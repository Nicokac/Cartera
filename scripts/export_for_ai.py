#!/usr/bin/env python3
"""
Export pipeline snapshots to CSV for external AI analysis.

Usage:
    python scripts/export_for_ai.py                  # latest snapshot
    python scripts/export_for_ai.py --date 2026-04-21

Generates two files in data/exports/:
    export_full_YYYY-MM-DD.csv     — todas las columnas de decision_table
                                     + última predicción por ticker
    export_curated_YYYY-MM-DD.csv  — ~30 columnas más informativas
                                     + contexto de portafolio en cada fila
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
RUNTIME_DIR = ROOT / "data" / "runtime"
EXPORTS_DIR = ROOT / "data" / "exports"

# Columnas curadas (~30): identidad, posición, decisión, técnico, rationale, predicción, contexto
CURATED_COLUMNS = [
    # Contexto de corrida (repetido en cada fila para facilitar lectura al agente)
    "run_date",
    "mep_real",
    "total_portfolio_ars",
    "liquidez_desplegable_total_ars",
    "market_regime_flags",
    # Identidad del instrumento
    "Ticker_IOL",
    "Tipo",
    "Bloque",
    "asset_family",
    "asset_subfamily",
    # Posición actual
    "Peso_%",
    "Valorizado_ARS",
    "Valor_USD",
    "Ganancia_%",
    # Decisión del motor
    "accion_sugerida_v2",
    "score_unificado",
    "accion_previa",
    "dias_consecutivos_refuerzo",
    "dias_consecutivos_reduccion",
    # Overlay técnico
    "Tech_Trend",
    "RSI_14",
    "Momentum_20d_%",
    "Momentum_60d_%",
    "ADX_14",
    "Relative_Volume",
    # Rationale legible
    "driver_1",
    "driver_2",
    "driver_3",
    # Predicción direccional (merged desde prediction_history)
    "pred_direction",
    "pred_confidence",
    "pred_conviction_label",
]


def find_latest_date() -> str:
    dates = sorted(
        {p.name[:10] for p in SNAPSHOTS_DIR.glob("????-??-??_real_decision_table.csv")},
        reverse=True,
    )
    if not dates:
        raise FileNotFoundError("No se encontraron snapshots en data/snapshots/")
    return dates[0]


def load_decision_table(date: str) -> pd.DataFrame:
    path = SNAPSHOTS_DIR / f"{date}_real_decision_table.csv"
    if not path.exists():
        raise FileNotFoundError(f"No existe decision_table para {date}: {path}")
    return pd.read_csv(path, low_memory=False)


def load_kpis(date: str) -> dict:
    path = SNAPSHOTS_DIR / f"{date}_real_kpis.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_liquidity_contract(date: str) -> dict:
    path = SNAPSHOTS_DIR / f"{date}_real_liquidity_contract.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_last_predictions() -> pd.DataFrame:
    path = RUNTIME_DIR / "prediction_history.csv"
    if not path.exists():
        return pd.DataFrame(columns=["ticker", "direction", "confidence", "conviction_label"])
    df = pd.read_csv(path, low_memory=False)
    if df.empty or "ticker" not in df.columns:
        return df
    # Última predicción por ticker (la más reciente por run_date)
    if "run_date" in df.columns:
        df["run_date"] = pd.to_datetime(df["run_date"], errors="coerce")
        df = df.sort_values("run_date", ascending=False)
    return df.drop_duplicates(subset=["ticker"], keep="first")[
        ["ticker", "direction", "confidence", "conviction_label"]
    ].rename(columns={
        "direction": "pred_direction",
        "confidence": "pred_confidence",
        "conviction_label": "pred_conviction_label",
    })


def enrich_with_context(df: pd.DataFrame, kpis: dict, liquidity: dict, date: str) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "run_date", date)
    df["mep_real"] = kpis.get("mep_real")
    df["total_portfolio_ars"] = kpis.get("total_ars")
    df["liquidez_desplegable_total_ars"] = liquidity.get("liquidez_desplegable_total_ars")

    # Consolidar flags de régimen en una sola columna legible
    flags: list[str] = []
    if df.get("market_regime_stress_soberano_local", pd.Series([False])).any():
        flags.append("stress_soberano")
    if df.get("market_regime_inflacion_local_alta", pd.Series([False])).any():
        flags.append("inflacion_alta")
    if df.get("market_regime_tasas_ust_altas", pd.Series([False])).any():
        flags.append("tasas_ust_altas")
    df["market_regime_flags"] = ", ".join(flags) if flags else "ninguno"

    return df


def enrich_with_predictions(df: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        df["pred_direction"] = None
        df["pred_confidence"] = None
        df["pred_conviction_label"] = None
        return df
    return df.merge(
        predictions,
        left_on="Ticker_IOL",
        right_on="ticker",
        how="left",
    ).drop(columns=["ticker"], errors="ignore")


def build_curated(df: pd.DataFrame) -> pd.DataFrame:
    available = [c for c in CURATED_COLUMNS if c in df.columns]
    missing = [c for c in CURATED_COLUMNS if c not in df.columns]
    if missing:
        print(f"  Columnas curadas no disponibles (se omiten): {missing}")
    return df[available].copy()


def export(date: str | None = None) -> None:
    date = date or find_latest_date()
    print(f"Exportando snapshot: {date}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    decision = load_decision_table(date)
    kpis = load_kpis(date)
    liquidity = load_liquidity_contract(date)
    predictions = load_last_predictions()

    print(f"  decision_table: {len(decision)} filas, {len(decision.columns)} columnas")
    print(f"  predicciones disponibles: {len(predictions)} tickers")

    decision = enrich_with_context(decision, kpis, liquidity, date)
    decision = enrich_with_predictions(decision, predictions)

    # --- Export completo ---
    full_path = EXPORTS_DIR / f"export_full_{date}.csv"
    decision.to_csv(full_path, index=False, encoding="utf-8-sig")
    print(f"  [full]    {full_path.name}  ({len(decision.columns)} cols, {len(decision)} filas)")

    # --- Export curado ---
    curated = build_curated(decision)
    curated_path = EXPORTS_DIR / f"export_curated_{date}.csv"
    curated.to_csv(curated_path, index=False, encoding="utf-8-sig")
    print(f"  [curated] {curated_path.name}  ({len(curated.columns)} cols, {len(curated)} filas)")

    print("Listo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exportar snapshot de cartera para análisis externo")
    parser.add_argument("--date", default=None, help="Fecha del snapshot (YYYY-MM-DD). Default: último disponible.")
    args = parser.parse_args()
    export(args.date)
