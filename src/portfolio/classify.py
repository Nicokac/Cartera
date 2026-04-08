from __future__ import annotations

from typing import Any


def classify_iol_portfolio(
    activos: list[dict[str, Any]],
    *,
    finviz_map: dict[str, str],
    block_map: dict[str, str],
    vn_factor_map: dict[str, float | int],
) -> dict[str, list[tuple]]:
    portafolio: list[tuple] = []
    acciones_locales: list[tuple] = []
    bonos: list[tuple] = []
    liquidez: list[tuple] = []

    for activo in activos:
        titulo = activo.get("titulo", {}) or {}
        simbolo = titulo.get("simbolo")
        descripcion = titulo.get("descripcion")
        tipo = str(titulo.get("tipo") or "").strip()
        tipo_norm = tipo.upper().replace(" ", "")
        moneda = str(titulo.get("moneda") or "")

        cantidad = float(activo.get("cantidad", 0) or 0)
        ppc = float(activo.get("ppc", 0) or 0)
        valorizado = float(activo.get("valorizado", 0) or 0)
        ganancia_dinero = float(activo.get("gananciaDinero", 0) or 0)

        if not simbolo:
            continue

        bloque = block_map.get(simbolo, "Sin clasificar")

        if tipo_norm == "CEDEARS":
            ticker_finviz = finviz_map.get(simbolo)
            portafolio.append((simbolo, ticker_finviz, bloque, cantidad, ppc))
            continue

        if tipo_norm in {"ACCIONES", "ACCION"}:
            acciones_locales.append((simbolo, simbolo, bloque, cantidad, ppc))
            continue

        if tipo_norm in {"TITULOSPUBLICOS", "TITULOPUBLICO"}:
            vn_factor = float(vn_factor_map.get(simbolo, 100) or 100)
            bonos.append((simbolo, bloque, cantidad, ppc, vn_factor))
            continue

        if "FONDOCOMUNDEINVERSION" in tipo_norm or "FCI" in tipo_norm:
            liquidez.append(
                (
                    simbolo,
                    descripcion,
                    "Liquidez",
                    "USD" if "DOLAR" in str(descripcion).upper() or "USD" in moneda.upper() else "ARS",
                    valorizado,
                    ganancia_dinero,
                )
            )
            continue

        if "CAUCION" in tipo_norm:
            liquidez.append(
                (
                    "CAUCION",
                    descripcion,
                    "Liquidez",
                    "ARS",
                    valorizado,
                    ganancia_dinero,
                )
            )

    return {
        "PORTAFOLIO": sorted(portafolio, key=lambda x: x[0]),
        "ACCIONES_LOCALES": sorted(acciones_locales, key=lambda x: x[0]),
        "BONOS": sorted(bonos, key=lambda x: x[0]),
        "LIQUIDEZ": sorted(liquidez, key=lambda x: x[0]),
    }
