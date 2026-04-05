from __future__ import annotations

import json
import sys
from getpass import getpass
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

import config as project_config
from analytics.bond_analytics import build_bond_monitor_table, build_bond_subfamily_summary, enrich_bond_analytics
from analytics.technical import build_technical_overlay
from clients.argentinadatos import get_mep_real
from clients.bonistas_client import get_bonds_for_portfolio, get_macro_variables
from clients.finviz_client import fetch_finviz_bundle
from clients.iol import (
    iol_get_estado_cuenta,
    iol_get_portafolio,
    iol_get_quote_with_reauth,
    iol_login,
)
from generate_smoke_report import REPORTS_DIR, render_report
from pipeline import build_dashboard_bundle, build_decision_bundle, build_portfolio_bundle, build_sizing_bundle


HTML_PATH = REPORTS_DIR / "real-report.html"
SNAPSHOTS_DIR = ROOT / "tests" / "snapshots"


def prompt_yes_no(label: str, *, default: bool = False) -> bool:
    suffix = " [s/N]: " if not default else " [S/n]: "
    raw = input(label + suffix).strip().lower()
    if not raw:
        return default
    return raw in {"s", "si", "sí", "y", "yes"}


def prompt_money_ars(label: str) -> float:
    raw = input(label + " ").strip()
    if not raw:
        return 0.0
    normalized = raw.replace("$", "").replace(".", "").replace(",", ".").strip()
    return max(float(normalized), 0.0)


def parse_finviz_number(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return np.nan
    suffixes = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    suffix = text[-1].upper()
    if suffix in suffixes:
        try:
            return float(text[:-1]) * suffixes[suffix]
        except Exception:
            return np.nan
    try:
        return float(text)
    except Exception:
        return np.nan


def parse_finviz_pct(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return np.nan
    text = text.replace("%", "")
    try:
        return float(text)
    except Exception:
        return np.nan


def extract_quote_tickers(activos: list[dict]) -> list[str]:
    tickers: set[str] = set()
    allowed_types = {"CEDEARS", "ACCIONES", "ACCION", "TITULOSPUBLICOS", "TITULOPUBLICO"}

    for activo in activos:
        titulo = activo.get("titulo", {}) or {}
        simbolo = str(titulo.get("simbolo") or "").strip()
        tipo = str(titulo.get("tipo") or "").strip()
        tipo_norm = tipo.upper().replace(" ", "")

        if not simbolo or tipo_norm not in allowed_types:
            continue
        tickers.add(simbolo)

    return sorted(tickers)


def fetch_prices(
    tickers: list[str],
    *,
    token: str,
    username: str,
    password: str,
) -> tuple[dict[str, float], str]:
    prices: dict[str, float] = {}
    current_token = token

    for ticker in tickers:
        try:
            data, current_token = iol_get_quote_with_reauth(
                ticker,
                current_token,
                username=username,
                password=password,
                base_url=project_config.IOL_BASE_URL,
                market=project_config.MARKET,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 404:
                print(f"  [skip] Sin cotizacion IOL para {ticker} (404)")
                continue
            raise

        price = data.get("ultimoPrecio")
        if price is not None:
            prices[ticker] = float(price)
        else:
            print(f"  [skip] ultimoPrecio ausente para {ticker}")

    return prices, current_token


def enrich_real_cedears(
    df_cedears: pd.DataFrame,
    *,
    mep_real: float | None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    if df_cedears.empty:
        return df_cedears, pd.DataFrame(), {
            "cedears_total": 0,
            "fundamentals_covered": 0,
            "ratings_covered": 0,
            "coverage_by_field": {},
            "errors": [],
        }

    out = df_cedears.copy()
    ratings_rows: list[dict[str, object]] = []
    errors: list[str] = []

    defaults = {
        "Perf Week": np.nan,
        "Perf Month": np.nan,
        "Perf YTD": np.nan,
        "Beta": np.nan,
        "P/E": np.nan,
        "ROE": np.nan,
        "Profit Margin": np.nan,
        "MEP_Implicito": np.nan,
    }
    for col, default in defaults.items():
        if col not in out.columns:
            out[col] = default

    for idx, row in out.iterrows():
        ticker_finviz = row.get("Ticker_Finviz")
        if not ticker_finviz:
            continue

        try:
            bundle = fetch_finviz_bundle(str(ticker_finviz))
        except Exception as exc:
            errors.append(f"{ticker_finviz}: {exc}")
            continue

        fundamentals = bundle.get("fundamentals", {}) or {}
        out.loc[idx, "Perf Week"] = parse_finviz_pct(fundamentals.get("Perf Week", out.loc[idx, "Perf Week"]))
        out.loc[idx, "Perf Month"] = parse_finviz_pct(fundamentals.get("Perf Month", out.loc[idx, "Perf Month"]))
        out.loc[idx, "Perf YTD"] = parse_finviz_pct(fundamentals.get("Perf YTD", out.loc[idx, "Perf YTD"]))
        out.loc[idx, "Beta"] = parse_finviz_number(fundamentals.get("Beta", out.loc[idx, "Beta"]))
        out.loc[idx, "P/E"] = parse_finviz_number(fundamentals.get("P/E", out.loc[idx, "P/E"]))
        out.loc[idx, "ROE"] = parse_finviz_pct(fundamentals.get("ROE", out.loc[idx, "ROE"]))
        out.loc[idx, "Profit Margin"] = parse_finviz_pct(fundamentals.get("Profit Margin", out.loc[idx, "Profit Margin"]))

        if mep_real and pd.notna(row.get("Precio_ARS")):
            try:
                out.loc[idx, "MEP_Implicito"] = float(row["Precio_ARS"]) / max(float(mep_real), 1.0)
            except Exception:
                pass

        ratings = bundle.get("ratings")
        if isinstance(ratings, pd.DataFrame) and not ratings.empty:
            ratings = ratings.copy()
            action_col = next((c for c in ratings.columns if c.lower() in {"rating", "action", "status"}), None)
            if action_col:
                consenso = str(ratings[action_col].mode().iloc[0]) if not ratings[action_col].mode().empty else None
                consenso_n = int((ratings[action_col] == consenso).sum()) if consenso else 0
                ratings_rows.append(
                    {
                        "Ticker_Finviz": ticker_finviz,
                        "consenso": consenso,
                        "consenso_n": consenso_n,
                        "total_ratings": int(len(ratings)),
                    }
                )

    df_ratings_res = pd.DataFrame(ratings_rows)
    if not df_ratings_res.empty:
        df_ratings_res = df_ratings_res.drop_duplicates(subset=["Ticker_Finviz"]).set_index("Ticker_Finviz")
    coverage_fields = ["Perf Week", "Perf Month", "Perf YTD", "Beta", "P/E", "ROE", "Profit Margin"]
    coverage_by_field = {col: int(out[col].notna().sum()) for col in coverage_fields if col in out.columns}
    fundamentals_covered = int(out[coverage_fields].notna().any(axis=1).sum()) if coverage_fields else 0
    stats = {
        "cedears_total": int(len(out)),
        "fundamentals_covered": fundamentals_covered,
        "ratings_covered": int(len(df_ratings_res)),
        "coverage_by_field": coverage_by_field,
        "errors": errors[:10],
    }
    return out, df_ratings_res, stats


def write_real_snapshots(
    *,
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
    technical_overlay: pd.DataFrame | None,
) -> list[Path]:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp.now().strftime("%Y-%m-%d")

    df_total = portfolio_bundle["df_total"].copy()
    final_decision = decision_bundle["final_decision"].copy()
    liquidity_contract = dict(portfolio_bundle["liquidity_contract"])
    kpis = dict(dashboard_bundle["kpis"])

    paths = [
        SNAPSHOTS_DIR / f"{stamp}_real_portfolio_master.csv",
        SNAPSHOTS_DIR / f"{stamp}_real_decision_table.csv",
        SNAPSHOTS_DIR / f"{stamp}_real_liquidity_contract.json",
        SNAPSHOTS_DIR / f"{stamp}_real_kpis.json",
        SNAPSHOTS_DIR / f"{stamp}_real_technical_overlay.csv",
    ]

    df_total.sort_values("Valorizado_ARS", ascending=False).to_csv(paths[0], index=False, encoding="utf-8")
    final_decision.sort_values("score_unificado", ascending=False).to_csv(paths[1], index=False, encoding="utf-8")
    paths[2].write_text(json.dumps(liquidity_contract, ensure_ascii=False, indent=2), encoding="utf-8")
    paths[3].write_text(json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8")
    technical_df = technical_overlay.copy() if isinstance(technical_overlay, pd.DataFrame) else pd.DataFrame()
    technical_df.to_csv(paths[4], index=False, encoding="utf-8")
    return paths


def build_real_bonistas_bundle(df_bonos: pd.DataFrame) -> dict[str, object]:
    if df_bonos.empty:
        return {}

    tickers = sorted({str(ticker).strip().upper() for ticker in df_bonos["Ticker_IOL"].dropna().tolist() if str(ticker).strip()})
    if not tickers:
        return {}

    try:
        df_bonistas = get_bonds_for_portfolio(tickers)
    except Exception as exc:
        print(f"Bonistas instrumentos no disponible: {exc}")
        df_bonistas = pd.DataFrame()

    try:
        macro_variables = get_macro_variables()
    except Exception as exc:
        print(f"Bonistas variables no disponible: {exc}")
        macro_variables = {}

    if df_bonistas.empty and not macro_variables:
        return {}

    bond_analytics = enrich_bond_analytics(
        df_bonos,
        df_bonistas,
        macro_variables=macro_variables,
    )
    return {
        "bond_monitor": build_bond_monitor_table(bond_analytics),
        "bond_subfamily_summary": build_bond_subfamily_summary(bond_analytics),
        "macro_variables": macro_variables,
    }


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    username = input("Usuario IOL: ").strip()
    password = getpass("Password IOL: ").strip()
    if not username or not password:
        raise ValueError("Usuario y password son obligatorios.")

    print("Login IOL...")
    token = iol_login(username, password, base_url=project_config.IOL_BASE_URL)

    print("Descargando portafolio y estado de cuenta...")
    portfolio_payload = iol_get_portafolio(token, base_url=project_config.IOL_BASE_URL, pais="argentina")
    estado_payload = iol_get_estado_cuenta(token, base_url=project_config.IOL_BASE_URL)
    activos = portfolio_payload.get("activos", []) or []

    print("Definiendo politica de fondeo...")
    usar_liquidez_iol = prompt_yes_no("Usar liquidez actual de IOL para fondear la estrategia?", default=False)
    aporte_externo_ars = prompt_money_ars("Cuanto dinero nuevo vas a ingresar en ARS? (enter para 0)")

    mep_data = get_mep_real(casa=project_config.MEP_CASA, base_url=project_config.ARGENTINADATOS_URL)
    mep_real = float(mep_data["promedio"]) if mep_data else None

    tickers = extract_quote_tickers(activos)
    print(f"Descargando precios IOL para {len(tickers)} tickers...")
    precios_iol, token = fetch_prices(tickers, token=token, username=username, password=password)

    portfolio_bundle = build_portfolio_bundle(
        activos=activos,
        estado_payload=estado_payload,
        precios_iol=precios_iol,
        mep_real=mep_real,
        finviz_map=project_config.FINVIZ_MAP,
        block_map=project_config.BLOCK_MAP,
        instrument_profile_map=project_config.INSTRUMENT_PROFILE_MAP,
        vn_factor_map=project_config.VN_FACTOR_MAP,
        ratios=project_config.RATIOS,
        fci_cash_management=project_config.FCI_CASH_MANAGEMENT,
    )

    df_total = portfolio_bundle["df_total"]
    df_cedears, df_ratings_res, finviz_stats = enrich_real_cedears(portfolio_bundle["df_cedears"], mep_real=mep_real)
    technical_overlay = build_technical_overlay(df_cedears, scoring_rules=project_config.SCORING_RULES)
    tech_metric_cols = [
        "Dist_SMA20_%",
        "Dist_SMA50_%",
        "Dist_EMA20_%",
        "Dist_EMA50_%",
        "RSI_14",
        "Momentum_20d_%",
        "Momentum_60d_%",
        "Vol_20d_Anual_%",
        "Drawdown_desde_Max3m_%",
    ]
    tech_available_cols = [col for col in tech_metric_cols if col in technical_overlay.columns]
    tech_covered = int(technical_overlay[tech_available_cols].notna().any(axis=1).sum()) if tech_available_cols else 0
    tech_total = int(len(df_cedears))
    print(f"Cobertura técnica: {tech_covered}/{tech_total}")
    print(
        "Cobertura Finviz: "
        f"{finviz_stats.get('fundamentals_covered', 0)}/{finviz_stats.get('cedears_total', 0)}"
        f" | Ratings: {finviz_stats.get('ratings_covered', 0)}/{finviz_stats.get('cedears_total', 0)}"
    )
    if finviz_stats.get("errors"):
        print("Errores Finviz (muestra):")
        for item in finviz_stats["errors"]:
            print(f"  - {item}")

    decision_bundle = build_decision_bundle(
        df_total=df_total,
        df_cedears=df_cedears,
        df_ratings_res=df_ratings_res,
        decision_tech=technical_overlay,
        mep_real=mep_real,
        scoring_rules=project_config.SCORING_RULES,
        action_rules=project_config.ACTION_RULES,
    )
    sizing_bundle = build_sizing_bundle(
        final_decision=decision_bundle["final_decision"],
        mep_real=mep_real,
        bucket_weights=project_config.BUCKET_WEIGHTS,
        usar_liquidez_iol=usar_liquidez_iol,
        aporte_externo_ars=aporte_externo_ars,
        action_rules=project_config.ACTION_RULES,
        sizing_rules=project_config.SIZING_RULES,
    )
    dashboard_bundle = build_dashboard_bundle(df_total, mep_real=mep_real)
    bonistas_bundle = build_real_bonistas_bundle(portfolio_bundle["df_bonos"])

    report = {
        "mep_real": mep_real or 0.0,
        "portfolio_bundle": portfolio_bundle,
        "dashboard_bundle": dashboard_bundle,
        "decision_bundle": decision_bundle,
        "sizing_bundle": sizing_bundle,
        "technical_overlay": technical_overlay,
        "finviz_stats": finviz_stats,
        "bonistas_bundle": bonistas_bundle,
    }
    html_body = render_report(
        report,
        title="Real Run",
        headline="Prueba visual con datos reales de IOL",
        lede="Reporte generado con login por terminal. Las credenciales no se guardan en disco.",
    )
    HTML_PATH.write_text(html_body, encoding="utf-8")
    snapshot_paths = write_real_snapshots(
        portfolio_bundle=portfolio_bundle,
        dashboard_bundle=dashboard_bundle,
        decision_bundle=decision_bundle,
        technical_overlay=technical_overlay,
    )
    print(f"Reporte generado en: {HTML_PATH}")
    print("Snapshots generados:")
    for path in snapshot_paths:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
