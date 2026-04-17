from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from common.numeric import positive_float_or_none


def normalize_account_currency(moneda: Any) -> str:
    m = str(moneda or "").strip().upper()
    if "DOLAR" in m or "USD" in m:
        return "USD"
    return "ARS"


def extract_estado_cuenta_components(estado_payload: dict[str, Any]) -> dict[str, float]:
    cash_immediate_ars = 0.0
    cash_immediate_usd = 0.0
    cash_pending_ars = 0.0
    cash_pending_usd = 0.0
    fallback_cash_ars = 0.0
    fallback_cash_usd = 0.0
    cash_saldo_ars = 0.0
    cash_saldo_usd = 0.0
    cash_comprometido_ars = 0.0
    cash_comprometido_usd = 0.0
    total_broker_en_pesos = float(estado_payload.get("totalEnPesos", 0) or 0)

    for cuenta in estado_payload.get("cuentas", []):
        moneda = normalize_account_currency(cuenta.get("moneda"))
        disponible = float(cuenta.get("disponible", 0) or 0)
        saldo = float(cuenta.get("saldo", 0) or 0)
        comprometido = float(cuenta.get("comprometido", 0) or 0)

        if moneda == "ARS":
            fallback_cash_ars += disponible
            cash_saldo_ars += saldo
            cash_comprometido_ars += comprometido
        else:
            fallback_cash_usd += disponible
            cash_saldo_usd += saldo
            cash_comprometido_usd += comprometido

        saldos = cuenta.get("saldos", []) or []
        if not saldos:
            continue

        immediate_found = False

        for saldo_row in saldos:
            liquidacion = str(saldo_row.get("liquidacion") or "").strip().lower()
            disponible_row = float(saldo_row.get("disponible", 0) or 0)

            if liquidacion == "inmediato":
                immediate_found = True
                if moneda == "ARS":
                    cash_immediate_ars += disponible_row
                else:
                    cash_immediate_usd += disponible_row
            else:
                if moneda == "ARS":
                    cash_pending_ars += disponible_row
                else:
                    cash_pending_usd += disponible_row

        if not immediate_found:
            if moneda == "ARS":
                cash_immediate_ars += disponible
            else:
                cash_immediate_usd += disponible

    if cash_immediate_ars == 0 and fallback_cash_ars > 0:
        cash_immediate_ars = fallback_cash_ars
    if cash_immediate_usd == 0 and fallback_cash_usd > 0:
        cash_immediate_usd = fallback_cash_usd

    return {
        "cash_immediate_ars": cash_immediate_ars,
        "cash_immediate_usd": cash_immediate_usd,
        "cash_pending_ars": cash_pending_ars,
        "cash_pending_usd": cash_pending_usd,
        "cash_disponible_ars": fallback_cash_ars,
        "cash_disponible_usd": fallback_cash_usd,
        "cash_saldo_ars": cash_saldo_ars,
        "cash_saldo_usd": cash_saldo_usd,
        "cash_comprometido_ars": cash_comprometido_ars,
        "cash_comprometido_usd": cash_comprometido_usd,
        "total_broker_en_pesos": total_broker_en_pesos,
    }


def rebuild_liquidity(
    activos: list[dict[str, Any]],
    estado_payload: dict[str, Any],
    *,
    mep_real: float | None,
    fci_cash_management: set[str],
) -> tuple[pd.DataFrame, dict[str, float], list[tuple]]:
    mep_value = positive_float_or_none(mep_real)
    liquidez_rows: list[tuple] = []

    caucion_ars = 0.0
    fci_cash_management_ars = 0.0

    for activo in activos:
        titulo = activo.get("titulo", {}) or {}
        simbolo = str(titulo.get("simbolo") or "").strip()
        descripcion = str(titulo.get("descripcion") or "").strip()
        tipo = str(titulo.get("tipo") or "").strip()
        tipo_norm = tipo.upper().replace(" ", "")
        moneda_raw = str(titulo.get("moneda") or "")
        moneda = normalize_account_currency(moneda_raw)

        valorizado = float(activo.get("valorizado", 0) or 0)
        ganancia_dinero = float(activo.get("gananciaDinero", 0) or 0)

        if "CAUCION" in tipo_norm or "CAUCION" in simbolo.upper():
            caucion_ars += valorizado
            liquidez_rows.append(
                ("CAUCION", descripcion or "Caución", "Liquidez", "ARS", valorizado, ganancia_dinero)
            )
            continue

        if simbolo.upper() in fci_cash_management or "FONDOCOMUNDEINVERSION" in tipo_norm or "FCI" in tipo_norm:
            valorizado_ars = valorizado * mep_value if moneda == "USD" and mep_value is not None else valorizado
            ganancia_ars = ganancia_dinero * mep_value if moneda == "USD" and mep_value is not None else ganancia_dinero

            if simbolo.upper() in fci_cash_management:
                fci_cash_management_ars += valorizado_ars

            liquidez_rows.append(
                (
                    simbolo,
                    descripcion,
                    "Liquidez",
                    moneda,
                    valorizado if moneda == "USD" else valorizado_ars,
                    ganancia_dinero if moneda == "USD" else ganancia_ars,
                )
            )

    cash_components = extract_estado_cuenta_components(estado_payload)

    cash_immediate_ars = cash_components["cash_immediate_ars"]
    cash_immediate_usd = cash_components["cash_immediate_usd"]
    cash_pending_ars = cash_components["cash_pending_ars"]
    cash_pending_usd = cash_components["cash_pending_usd"]
    total_broker_en_pesos = cash_components["total_broker_en_pesos"]

    # En corridas reales de IOL, la caucion puede ya reflejarse en saldos ARS de la cuenta.
    # Si el cash inmediato+pendiente replica casi exactamente la caucion informada como posicion,
    # evitamos el doble conteo priorizando la caucion como activo y descartando ese cash espejo.
    mirror_gap_ars = abs((cash_immediate_ars + cash_pending_ars) - caucion_ars)
    duplicate_caucion_in_cash = caucion_ars > 0 and mirror_gap_ars <= max(1.0, caucion_ars * 0.02)

    if duplicate_caucion_in_cash:
        cash_immediate_ars = 0.0
        cash_pending_ars = 0.0

    if cash_immediate_ars > 0:
        liquidez_rows.append(("CASH_ARS", "Cash disponible broker ARS", "Liquidez", "ARS", cash_immediate_ars, 0.0))
    if cash_immediate_usd > 0:
        liquidez_rows.append(("CASH_USD", "Cash disponible broker USD", "Liquidez", "USD", cash_immediate_usd, 0.0))

    registros_liquidez = []
    for ticker, descripcion, bloque, moneda, valorizado_raw, ganancia_raw in liquidez_rows:
        if moneda == "USD":
            valorizado_ars = valorizado_raw * mep_value if mep_value is not None else np.nan
            ganancia_ars = ganancia_raw * mep_value if mep_value is not None else np.nan
            valor_usd = valorizado_raw
        else:
            valorizado_ars = valorizado_raw
            ganancia_ars = ganancia_raw
            valor_usd = valorizado_ars / mep_value if mep_value is not None else np.nan

        registros_liquidez.append(
            {
                "Ticker_IOL": ticker,
                "Descripcion": descripcion,
                "Bloque": bloque,
                "Tipo": "Liquidez",
                "Moneda": moneda,
                "Valorizado_ARS": valorizado_ars,
                "Valor_USD": valor_usd,
                "Ganancia_ARS": ganancia_ars,
                "Cantidad": None,
                "Cantidad_Real": None,
                "PPC_ARS": None,
                "Precio_ARS": None,
            }
        )

    df_liquidez = pd.DataFrame(registros_liquidez)
    if not df_liquidez.empty:
        df_liquidez = (
            df_liquidez.groupby(
                ["Ticker_IOL", "Descripcion", "Bloque", "Tipo", "Moneda"], as_index=False
            ).agg(
                {
                    "Valorizado_ARS": lambda values: values.sum(min_count=1),
                    "Valor_USD": lambda values: values.sum(min_count=1),
                    "Ganancia_ARS": lambda values: values.sum(min_count=1),
                    "Cantidad": "first",
                    "Cantidad_Real": "first",
                    "PPC_ARS": "first",
                    "Precio_ARS": "first",
                }
            )
        )

    cash_disponible_broker_ars = (
        cash_immediate_ars + cash_immediate_usd * mep_value if mep_value is not None else cash_immediate_ars
    )
    caucion_colocada_ars = caucion_ars
    liquidez_estrategica_ars = fci_cash_management_ars
    liquidez_desplegable_total_ars = cash_disponible_broker_ars + caucion_colocada_ars + liquidez_estrategica_ars

    liquidity_contract = {
        "cash_operativo_ars": round(cash_disponible_broker_ars, 2),
        "cash_comprometido_ars": round(cash_components["cash_comprometido_ars"], 2),
        "caucion_tactica_ars": round(caucion_colocada_ars, 2),
        "fci_estrategico_ars": round(liquidez_estrategica_ars, 2),
        "liquidez_desplegable_total_ars": round(liquidez_desplegable_total_ars, 2),
        "cash_operativo_usd": round(cash_disponible_broker_ars / mep_value, 2) if mep_value is not None else np.nan,
        "cash_comprometido_usd": round(cash_components["cash_comprometido_usd"], 2),
        "caucion_tactica_usd": round(caucion_colocada_ars / mep_value, 2) if mep_value is not None else np.nan,
        "fci_estrategico_usd": round(liquidez_estrategica_ars / mep_value, 2) if mep_value is not None else np.nan,
        "liquidez_desplegable_total_usd": (
            round(liquidez_desplegable_total_ars / mep_value, 2) if mep_value is not None else np.nan
        ),
        "total_broker_en_pesos": total_broker_en_pesos,
        "duplicate_caucion_in_cash": duplicate_caucion_in_cash,
    }

    return df_liquidez, liquidity_contract, liquidez_rows
