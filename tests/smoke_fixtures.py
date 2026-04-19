from __future__ import annotations

import pandas as pd


def build_mock_inputs() -> tuple[list[dict], dict, dict[str, float], float]:
    mep_real = 1250.0

    activos = [
        {
            "cantidad": 85,
            "ppc": 9800,
            "valorizado": 1187450,
            "gananciaDinero": 354450,
            "titulo": {
                "simbolo": "T",
                "descripcion": "Cedear AT&T",
                "tipo": "CEDEARS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 25,
            "ppc": 30000,
            "valorizado": 1219000,
            "gananciaDinero": 469000,
            "titulo": {
                "simbolo": "VIST",
                "descripcion": "Cedear Vista",
                "tipo": "CEDEARS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 12,
            "ppc": 15000,
            "valorizado": 165000,
            "gananciaDinero": -15000,
            "titulo": {
                "simbolo": "NVDA",
                "descripcion": "Cedear NVIDIA",
                "tipo": "CEDEARS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 1000,
            "ppc": 82,
            "valorizado": 950,
            "gananciaDinero": 130,
            "titulo": {
                "simbolo": "GD30",
                "descripcion": "Bono GD30",
                "tipo": "TITULOS PUBLICOS",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 1,
            "ppc": 1,
            "valorizado": 300000,
            "gananciaDinero": 0,
            "titulo": {
                "simbolo": "ADBAICA",
                "descripcion": "FCI Cash Management",
                "tipo": "FCI",
                "moneda": "peso_Argentino",
            },
        },
        {
            "cantidad": 1,
            "ppc": 1,
            "valorizado": 500000,
            "gananciaDinero": 0,
            "titulo": {
                "simbolo": "CAU123",
                "descripcion": "Caucion colocada",
                "tipo": "CAUCION",
                "moneda": "peso_Argentino",
            },
        },
    ]

    estado_payload = {
        "totalEnPesos": 2800000,
        "cuentas": [
            {
                "moneda": "peso_Argentino",
                "disponible": 650000,
                "saldos": [
                    {"liquidacion": "inmediato", "disponible": 600000},
                    {"liquidacion": "48hs", "disponible": 50000},
                ],
            },
            {
                "moneda": "USD",
                "disponible": 160,
                "saldos": [
                    {"liquidacion": "inmediato", "disponible": 120},
                    {"liquidacion": "24hs", "disponible": 40},
                ],
            },
        ],
    }

    precios_iol = {
        "T": 13970.0,
        "VIST": 48760.0,
        "NVDA": 13750.0,
        "GD30": 95.0,
    }

    return activos, estado_payload, precios_iol, mep_real


def build_mock_operations() -> list[dict[str, object]]:
    return [
        {
            "numero": 170860152,
            "fechaOperada": "2026-04-16T12:54:19",
            "tipo": "Compra",
            "estado": "terminada",
            "mercado": "BCBA",
            "simbolo": "GOOGL",
            "cantidadOperada": 14,
            "precioOperado": 8440,
            "montoOperado": 118160,
            "plazo": "a24horas",
        },
        {
            "numero": 170859929,
            "fechaOperada": "2026-04-16T12:53:40",
            "tipo": "Compra",
            "estado": "terminada",
            "mercado": "BCBA",
            "simbolo": "PAMP",
            "cantidadOperada": 42,
            "precioOperado": 4800,
            "montoOperado": 201600,
            "plazo": "a24horas",
        },
        {
            "numero": 170443236,
            "fechaOperada": "2026-04-13T15:39:56",
            "tipo": "Pago de Dividendos",
            "estado": "terminada",
            "mercado": "BCBA",
            "simbolo": "DIA US$",
            "montoOperado": 0.06,
            "plazo": "inmediata",
        },
    ]


def build_mock_previous_portfolio() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Ticker_IOL": "GOOGL", "Tipo": "CEDEAR", "Bloque": "Growth", "Cantidad": 20, "Peso_%": 0.69, "Valorizado_ARS": 169200},
            {"Ticker_IOL": "T", "Tipo": "CEDEAR", "Bloque": "Dividendos", "Cantidad": 80, "Peso_%": 41.00, "Valorizado_ARS": 1117600},
        ]
    )


def enrich_mock_cedears(df_cedears: pd.DataFrame, *, mep_real: float) -> pd.DataFrame:
    if df_cedears.empty:
        return df_cedears

    overlays = {
        "T": {"Perf Week": 1.2, "Perf Month": 3.8, "Perf YTD": 8.4, "Beta": 0.72, "P/E": 18.0},
        "VIST": {"Perf Week": 2.4, "Perf Month": 8.1, "Perf YTD": 21.0, "Beta": 1.48, "P/E": 11.5},
        "NVDA": {"Perf Week": -4.8, "Perf Month": -6.0, "Perf YTD": -12.0, "Beta": 1.86, "P/E": 42.0},
    }

    out = df_cedears.copy()
    out["Perf Week"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Perf Week"))
    out["Perf Month"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Perf Month"))
    out["Perf YTD"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Perf YTD"))
    out["Beta"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("Beta"))
    out["P/E"] = out["Ticker_IOL"].map(lambda t: overlays.get(t, {}).get("P/E"))
    out["ROE"] = out["Ticker_IOL"].map(lambda t: {"T": 18.0, "VIST": 24.0, "NVDA": 31.0}.get(t))
    out["Profit Margin"] = out["Ticker_IOL"].map(lambda t: {"T": 15.0, "VIST": 19.0, "NVDA": 22.0}.get(t))
    out["MEP_Implicito"] = mep_real * pd.Series([0.995, 1.015, 1.055][: len(out)], index=out.index)
    return out


def build_mock_ratings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Ticker_Finviz": "T", "consenso": "buy", "consenso_n": 12, "total_ratings": 15},
            {"Ticker_Finviz": "VIST", "consenso": "buy", "consenso_n": 8, "total_ratings": 10},
            {"Ticker_Finviz": "NVDA", "consenso": "hold", "consenso_n": 4, "total_ratings": 11},
        ]
    ).set_index("Ticker_Finviz")


def build_mock_bonistas(df_bonds: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    if df_bonds.empty:
        return pd.DataFrame(), {}

    rows = []
    for ticker in df_bonds["Ticker_IOL"].tolist():
        if ticker == "GD30":
            rows.append(
                {
                    "bonistas_ticker": "GD30",
                    "bonistas_tir_pct": 12.4,
                    "bonistas_paridad_pct": 77.8,
                    "bonistas_md": 3.2,
                    "bonistas_volume_last": 1500000.0,
                    "bonistas_volume_avg_20d": 1200000.0,
                    "bonistas_volume_ratio": 1.25,
                    "bonistas_liquidity_bucket": "alta",
                    "bonistas_fecha_vencimiento": "09/07/2030",
                    "bonistas_fecha_emision": "04/09/2020",
                    "bonistas_valor_tecnico": 72.1,
                    "bonistas_tir_avg_365d_pct": 13.8,
                    "bonistas_put_flag": False,
                    "bonistas_subfamily": "bond_hard_dollar",
                }
            )
    macro = {
        "cer_diario": 1.2,
        "tamar": 31.5,
        "tamar_tea": 37.9,
        "badlar": 29.1,
        "badlar_tea": 33.2,
        "reservas_bcra_musd": 28350.0,
        "a3500_mayorista": 1387.72,
        "riesgo_pais_bps": 720.0,
        "rem_inflacion_mensual_pct": 2.7,
        "rem_inflacion_12m_pct": 24.6,
        "ust_5y_pct": 4.05,
        "ust_10y_pct": 4.25,
        "ust_spread_10y_5y_pct": 0.20,
        "ust_date": "2026-04-04",
    }
    return pd.DataFrame(rows), macro
