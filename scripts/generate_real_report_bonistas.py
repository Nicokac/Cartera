from __future__ import annotations

import logging
from collections.abc import Callable

import pandas as pd


def build_real_bonistas_bundle_impl(
    df_bonos: pd.DataFrame,
    *,
    mep_real: float | None,
    get_bonds_for_portfolio_fn: Callable[[list[str]], pd.DataFrame],
    get_bond_volume_context_fn: Callable[[list[str]], pd.DataFrame],
    get_macro_variables_fn: Callable[[], dict[str, object]],
    get_riesgo_pais_latest_fn: Callable[..., dict[str, object] | None],
    riesgo_pais_url: str,
    get_rem_latest_fn: Callable[..., dict[str, object] | None],
    rem_url: str,
    rem_xls_url: str,
    get_bcra_monetary_context_fn: Callable[..., dict[str, object]],
    bcra_monetarias_api_url: str,
    bcra_reservas_id: int,
    bcra_a3500_id: int,
    bcra_badlar_tna_id: int,
    bcra_badlar_tea_id: int,
    get_ust_latest_fn: Callable[[], dict[str, object] | None],
    enrich_bond_analytics_fn: Callable[..., pd.DataFrame],
    build_bond_monitor_table_fn: Callable[[pd.DataFrame], pd.DataFrame],
    build_bond_subfamily_summary_fn: Callable[[pd.DataFrame], pd.DataFrame],
    build_bond_local_subfamily_summary_fn: Callable[[pd.DataFrame], pd.DataFrame],
    logger: logging.Logger,
    print_fn: Callable[[str], None],
) -> dict[str, object]:
    if df_bonos.empty:
        return {}

    tickers = sorted({str(ticker).strip().upper() for ticker in df_bonos["Ticker_IOL"].dropna().tolist() if str(ticker).strip()})
    if not tickers:
        return {}

    try:
        df_bonistas = get_bonds_for_portfolio_fn(tickers)
    except Exception as exc:
        print_fn(f"Bonistas instrumentos no disponible: {exc}")
        logger.warning("Bonistas instrumentos no disponible: %s", exc)
        df_bonistas = pd.DataFrame()
    if not df_bonistas.empty and "bonistas_ticker" in df_bonistas.columns and "Ticker_IOL" not in df_bonistas.columns:
        df_bonistas = df_bonistas.rename(columns={"bonistas_ticker": "Ticker_IOL"})

    try:
        df_bond_volume = get_bond_volume_context_fn(tickers)
    except Exception as exc:
        print_fn(f"PyOBD volumen no disponible: {exc}")
        logger.warning("PyOBD volumen no disponible: %s", exc)
        df_bond_volume = pd.DataFrame()
    if not df_bond_volume.empty:
        if df_bonistas.empty:
            df_bonistas = df_bond_volume.copy()
        else:
            df_bonistas = df_bonistas.merge(df_bond_volume, on="Ticker_IOL", how="left")

    try:
        macro_variables = get_macro_variables_fn()
    except Exception as exc:
        print_fn(f"Bonistas variables no disponible: {exc}")
        logger.warning("Bonistas variables no disponible: %s", exc)
        macro_variables = {}

    try:
        riesgo_pais = get_riesgo_pais_latest_fn(base_url=riesgo_pais_url)
    except Exception as exc:
        print_fn(f"ArgentinaDatos riesgo pais no disponible: {exc}")
        logger.warning("ArgentinaDatos riesgo pais no disponible: %s", exc)
        riesgo_pais = None
    if riesgo_pais:
        macro_variables = dict(macro_variables)
        macro_variables["riesgo_pais_bps"] = float(riesgo_pais["valor"])
        macro_variables["riesgo_pais_fecha"] = riesgo_pais.get("fecha")

    try:
        rem_latest = get_rem_latest_fn(
            base_url=rem_url,
            xlsx_url=rem_xls_url,
        )
    except Exception as exc:
        print_fn(f"BCRA REM no disponible: {exc}")
        logger.warning("BCRA REM no disponible: %s", exc)
        rem_latest = None
    if rem_latest:
        macro_variables = dict(macro_variables)
        macro_variables["rem_inflacion_mensual_pct"] = float(rem_latest["inflacion_mensual_pct"])
        if rem_latest.get("inflacion_12m_pct") is not None:
            macro_variables["rem_inflacion_12m_pct"] = float(rem_latest["inflacion_12m_pct"])
        macro_variables["rem_periodo"] = rem_latest.get("periodo")
        macro_variables["rem_fecha_publicacion"] = rem_latest.get("fecha_publicacion")

    try:
        bcra_monetary = get_bcra_monetary_context_fn(
            base_url=bcra_monetarias_api_url,
            reservas_id=bcra_reservas_id,
            a3500_id=bcra_a3500_id,
            badlar_tna_id=bcra_badlar_tna_id,
            badlar_tea_id=bcra_badlar_tea_id,
        )
    except Exception as exc:
        print_fn(f"BCRA monetarias no disponible: {exc}")
        logger.warning("BCRA monetarias no disponible: %s", exc)
        bcra_monetary = {}
    if bcra_monetary:
        macro_variables = dict(macro_variables)
        macro_variables.update(bcra_monetary)

    try:
        ust_latest = get_ust_latest_fn()
    except Exception as exc:
        print_fn(f"FRED UST no disponible: {exc}")
        logger.warning("FRED UST no disponible: %s", exc)
        ust_latest = None
        macro_variables = dict(macro_variables)
        macro_variables["ust_status"] = "error"
        macro_variables["ust_error"] = str(exc)
    if ust_latest:
        macro_variables = dict(macro_variables)
        macro_variables["ust_status"] = "ok"
        macro_variables.update(ust_latest)

    if df_bonistas.empty and not macro_variables:
        return {}

    bond_analytics = enrich_bond_analytics_fn(
        df_bonos,
        df_bonistas,
        macro_variables=macro_variables,
        mep_real=mep_real,
    )
    return {
        "bond_analytics": bond_analytics,
        "bond_monitor": build_bond_monitor_table_fn(bond_analytics),
        "bond_subfamily_summary": build_bond_subfamily_summary_fn(bond_analytics),
        "bond_local_subfamily_summary": build_bond_local_subfamily_summary_fn(bond_analytics),
        "macro_variables": macro_variables,
    }
