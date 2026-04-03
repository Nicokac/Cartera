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
from clients.argentinadatos import get_mep_real
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


def enrich_real_cedears(df_cedears: pd.DataFrame, *, mep_real: float | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df_cedears.empty:
        return df_cedears, pd.DataFrame()

    out = df_cedears.copy()
    ratings_rows: list[dict[str, object]] = []

    defaults = {
        "Perf Week": np.nan,
        "Perf Month": np.nan,
        "Perf YTD": np.nan,
        "Beta": np.nan,
        "P/E": np.nan,
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
        except Exception:
            continue

        fundamentals = bundle.get("fundamentals", {}) or {}
        out.loc[idx, "Perf Week"] = fundamentals.get("Perf Week", out.loc[idx, "Perf Week"])
        out.loc[idx, "Perf Month"] = fundamentals.get("Perf Month", out.loc[idx, "Perf Month"])
        out.loc[idx, "Perf YTD"] = fundamentals.get("Perf YTD", out.loc[idx, "Perf YTD"])
        out.loc[idx, "Beta"] = fundamentals.get("Beta", out.loc[idx, "Beta"])
        out.loc[idx, "P/E"] = fundamentals.get("P/E", out.loc[idx, "P/E"])

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
    return out, df_ratings_res


def write_real_snapshots(
    *,
    portfolio_bundle: dict[str, object],
    dashboard_bundle: dict[str, object],
    decision_bundle: dict[str, object],
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
    ]

    df_total.sort_values("Valorizado_ARS", ascending=False).to_csv(paths[0], index=False, encoding="utf-8")
    final_decision.sort_values("score_unificado", ascending=False).to_csv(paths[1], index=False, encoding="utf-8")
    paths[2].write_text(json.dumps(liquidity_contract, ensure_ascii=False, indent=2), encoding="utf-8")
    paths[3].write_text(json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8")
    return paths


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
        vn_factor_map=project_config.VN_FACTOR_MAP,
        ratios=project_config.RATIOS,
        fci_cash_management=project_config.FCI_CASH_MANAGEMENT,
    )

    df_total = portfolio_bundle["df_total"]
    df_cedears, df_ratings_res = enrich_real_cedears(portfolio_bundle["df_cedears"], mep_real=mep_real)

    decision_bundle = build_decision_bundle(
        df_total=df_total,
        df_cedears=df_cedears,
        df_ratings_res=df_ratings_res,
        mep_real=mep_real,
    )
    sizing_bundle = build_sizing_bundle(
        final_decision=decision_bundle["final_decision"],
        mep_real=mep_real,
        defensive_tickers=project_config.DEFENSIVE_TICKERS,
        aggressive_tickers=project_config.AGGRESSIVE_TICKERS,
        bucket_weights=project_config.BUCKET_WEIGHTS,
    )
    dashboard_bundle = build_dashboard_bundle(df_total, mep_real=mep_real)

    report = {
        "mep_real": mep_real or 0.0,
        "portfolio_bundle": portfolio_bundle,
        "dashboard_bundle": dashboard_bundle,
        "decision_bundle": decision_bundle,
        "sizing_bundle": sizing_bundle,
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
    )
    print(f"Reporte generado en: {HTML_PATH}")
    print("Snapshots generados:")
    for path in snapshot_paths:
        print(f"  - {path}")


if __name__ == "__main__":
    main()
