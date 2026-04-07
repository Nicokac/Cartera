from __future__ import annotations

import pandas as pd


def _assign_action(
    decision: pd.DataFrame,
    *,
    action_column: str,
    score_refuerzo_column: str,
    score_reduccion_column: str,
    action_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    action_rules = action_rules or {}
    refuerzo_threshold = float(action_rules.get("refuerzo_threshold", 0.60))
    reduccion_threshold = float(action_rules.get("reduccion_threshold", 0.60))
    score_gap_min = float(action_rules.get("score_gap_min", 0.10))
    despliegue_liquidez_threshold = float(action_rules.get("despliegue_liquidez_threshold", 0.55))

    out = decision.copy()
    out[action_column] = "Mantener / Neutral"

    out.loc[
        (~out["Es_Liquidez"])
        & (~out["Es_Bono"])
        & (out[score_refuerzo_column] >= refuerzo_threshold)
        & ((out[score_refuerzo_column] - out[score_reduccion_column]) >= score_gap_min),
        action_column,
    ] = "Refuerzo"

    out.loc[
        (~out["Es_Liquidez"])
        & (~out["Es_Bono"])
        & (out[score_reduccion_column] >= reduccion_threshold)
        & ((out[score_reduccion_column] - out[score_refuerzo_column]) >= score_gap_min),
        action_column,
    ] = "Reducir"

    out.loc[
        (out["Es_Liquidez"]) & (out["score_despliegue_liquidez"] >= despliegue_liquidez_threshold),
        action_column,
    ] = "Desplegar liquidez"
    return out


def assign_base_action(decision: pd.DataFrame, *, action_rules: dict[str, object] | None = None) -> pd.DataFrame:
    return _assign_action(
        decision,
        action_column="accion_sugerida",
        score_refuerzo_column="score_refuerzo",
        score_reduccion_column="score_reduccion",
        action_rules=action_rules,
    )


def assign_action_v2(decision_tech: pd.DataFrame, *, action_rules: dict[str, object] | None = None) -> pd.DataFrame:
    return _assign_action(
        decision_tech,
        action_column="accion_sugerida_v2",
        score_refuerzo_column="score_refuerzo_v2",
        score_reduccion_column="score_reduccion_v2",
        action_rules=action_rules,
    )


def enrich_decision_explanations(
    df: pd.DataFrame,
    *,
    scoring_rules: dict[str, object] | None = None,
) -> pd.DataFrame:
    scoring_rules = scoring_rules or {}
    out = df.copy()
    absolute_rules = scoring_rules.get("absolute_scoring", {}) or {}
    absolute_metrics = absolute_rules.get("metrics", {}) or {}
    narrative_rules = scoring_rules.get("narrative_thresholds", {}) or {}

    beta_rules = absolute_metrics.get("beta", {}) or {}
    pe_rules = absolute_metrics.get("pe", {}) or {}
    roe_rules = absolute_metrics.get("roe", {}) or {}
    profit_margin_rules = absolute_metrics.get("profit_margin", {}) or {}
    mep_rules = absolute_metrics.get("mep_premium_pct", {}) or {}
    gain_rules = absolute_metrics.get("ganancia_pct_cap", {}) or {}

    positive_thresholds = narrative_rules.get("positive", {}) or {}
    negative_thresholds = narrative_rules.get("negative", {}) or {}

    low_weight_max = float(positive_thresholds.get("peso_max", 2.0))
    beta_ok_max = float(positive_thresholds.get("beta_max", beta_rules.get("good_max", 0.8)))
    pe_ok_max = float(positive_thresholds.get("pe_max", pe_rules.get("good_max", 18.0)))
    roe_good_min = float(positive_thresholds.get("roe_min", roe_rules.get("good_min", 20.0)))
    profit_margin_good_min = float(
        positive_thresholds.get("profit_margin_min", profit_margin_rules.get("good_min", 20.0))
    )
    consensus_good_min = float(positive_thresholds.get("consensus_min", 0.70))
    momentum_good_min = float(positive_thresholds.get("momentum_refuerzo_min", 0.65))
    mep_good_max = float(positive_thresholds.get("mep_premium_max", mep_rules.get("good_max", -90.0)))

    high_weight_min = float(negative_thresholds.get("peso_min", 4.0))
    beta_risk_min = float(negative_thresholds.get("beta_min", beta_rules.get("bad_min", 1.3)))
    pe_expensive_min = float(negative_thresholds.get("pe_min", pe_rules.get("bad_min", 30.0)))
    profit_margin_low_max = float(
        negative_thresholds.get("profit_margin_max", profit_margin_rules.get("bad_max", 10.0))
    )
    consensus_bad_max = float(negative_thresholds.get("consensus_max", 0.35))
    momentum_bad_min = float(negative_thresholds.get("momentum_reduccion_min", 0.60))
    gain_extended_min = float(negative_thresholds.get("ganancia_pct_cap_min", gain_rules.get("bad_min", 80.0)))

    def _is_country_region_etf(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "etf_country_region"

    def _is_sector_etf(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "etf_sector"

    def _is_core_etf(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "etf_core"

    def _is_growth_stock(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "stock_growth"

    def _is_defensive_dividend_stock(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "stock_defensive_dividend"

    def _is_commodity_stock(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "stock_commodity"

    def _is_argentina_stock(row: pd.Series) -> bool:
        return row.get("asset_subfamily") == "stock_argentina"

    def _metric_available(row: pd.Series, col: str) -> bool:
        return col in row.index and pd.notna(row.get(col))

    def _join_reasons(reasons: list[str], fallback: str) -> str:
        clean: list[str] = []
        for reason in reasons:
            if reason and reason not in clean:
                clean.append(reason)
        if not clean:
            return fallback
        if len(clean) == 1:
            return clean[0]
        return f"{clean[0]} y {clean[1]}"

    def _positive_signals(row: pd.Series) -> list[str]:
        signals: list[str] = []
        if _metric_available(row, "Peso_%") and float(row.get("Peso_%", 0)) <= low_weight_max:
            signals.append("peso bajo")
        if _metric_available(row, "Beta") and float(row.get("Beta", 0)) <= beta_ok_max:
            signals.append("beta controlada")
        if _metric_available(row, "P/E") and float(row.get("P/E", 0)) <= pe_ok_max:
            signals.append("valuacion razonable")
        if _metric_available(row, "ROE") and float(row.get("ROE", 0)) >= roe_good_min:
            signals.append("ROE alto")
        if _metric_available(row, "Profit Margin") and float(row.get("Profit Margin", 0)) >= profit_margin_good_min:
            signals.append("margen alto")
        if _metric_available(row, "Consensus_Final") and float(row.get("Consensus_Final", 0.5)) >= consensus_good_min:
            signals.append("consenso favorable")
        if _metric_available(row, "Momentum_Refuerzo") and float(row.get("Momentum_Refuerzo", 0.5)) >= momentum_good_min:
            signals.append("momentum fuerte")
        if row.get("Tech_Trend") == "Alcista":
            signals.append("tecnico alcista")
        if row.get("Tech_Trend") == "Alcista fuerte":
            signals.append("tecnico alcista fuerte")
        if _metric_available(row, "MEP_Premium_%") and float(row.get("MEP_Premium_%", 0)) <= mep_good_max:
            signals.append("MEP favorable")
        return signals

    def _negative_signals(row: pd.Series) -> list[str]:
        signals: list[str] = []
        if _metric_available(row, "Peso_%") and float(row.get("Peso_%", 0)) >= high_weight_min:
            signals.append("peso alto")
        if _metric_available(row, "Beta") and float(row.get("Beta", 0)) >= beta_risk_min:
            signals.append("beta alta")
        if _metric_available(row, "P/E") and float(row.get("P/E", 0)) >= pe_expensive_min:
            signals.append("valuacion exigente")
        if _metric_available(row, "Profit Margin") and float(row.get("Profit Margin", 100)) <= profit_margin_low_max:
            signals.append("margen bajo")
        if _metric_available(row, "Consensus_Final") and float(row.get("Consensus_Final", 0.5)) <= consensus_bad_max:
            signals.append("consenso debil")
        if _metric_available(row, "Momentum_Reduccion_Effective") and float(row.get("Momentum_Reduccion_Effective", 0.5)) >= momentum_bad_min:
            signals.append("momentum debil")
        if row.get("Tech_Trend") == "Bajista":
            signals.append("tecnico bajista")
        if _metric_available(row, "Ganancia_%_Cap") and float(row.get("Ganancia_%_Cap", 0)) >= gain_extended_min:
            signals.append("ganancia extendida")
        return signals

    def top_drivers(row: pd.Series) -> list[str]:
        candidates = [
            ("momentum", row.get("Momentum_Refuerzo", 0) - row.get("Momentum_Reduccion", 0)),
            ("consenso", row.get("s_consensus_good", 0) - row.get("s_consensus_bad", 0)),
            ("peso", row.get("s_low_weight", 0) - row.get("s_high_weight", 0)),
            ("beta", row.get("s_beta_ok", 0) - row.get("s_beta_risk", 0)),
            ("mep", row.get("s_mep_ok", 0) - row.get("s_mep_premium", 0)),
            ("valuacion", row.get("s_pe_ok", 0) - row.get("s_pe_expensive", 0)),
            ("liquidez", row.get("score_despliegue_liquidez", 0)),
        ]
        ordered = [name for name, _ in sorted(candidates, key=lambda item: abs(item[1]), reverse=True)]
        return ordered[:3]

    def motivo_score(row: pd.Series) -> str:
        if row.get("Es_Liquidez"):
            return "Score de liquidez calculado por peso y perdida relativa."
        if row.get("Es_Bono"):
            return "Score de bono calculado con sesgo prudencial y control de rebalanceo."
        if _is_core_etf(row):
            return "Score de ETF core balanceado entre regimen, concentracion, beta, MEP y rol de cartera."
        if _is_sector_etf(row):
            return "Score de ETF sectorial ponderado por beta, momentum, MEP y soporte tactico."
        if _is_country_region_etf(row):
            return "Score de ETF pais o region ponderado por momentum, beta, MEP y soporte tactico prudente."
        if _is_growth_stock(row):
            return "Score de CEDEAR growth ponderado por momentum, valuacion, beta, consenso y calidad."
        if _is_defensive_dividend_stock(row):
            return "Score de CEDEAR defensivo o dividendos ponderado por beta, calidad, valuacion y MEP."
        if _is_commodity_stock(row):
            return "Score de CEDEAR de commodities ponderado por momentum, valuacion, beta y soporte tactico."
        if _is_argentina_stock(row):
            return "Score de accion local ponderado por peso, momentum, beta y prudencia de cartera."
        return "Score de CEDEAR compuesto por momentum, peso, consenso, beta, MEP, valuacion y calidad."

    def motivo_accion(row: pd.Series) -> str:
        accion = row.get("accion_sugerida_v2", row.get("accion_sugerida", "Mantener / Neutral"))
        positive_signals = _positive_signals(row)
        negative_signals = _negative_signals(row)
        positive_summary = _join_reasons(positive_signals, "senales favorables")
        negative_summary = _join_reasons(negative_signals, "senales mixtas")

        if accion == "Refuerzo":
            if _is_sector_etf(row):
                return f"Refuerzo sectorial por {positive_summary}."
            if _is_core_etf(row):
                return f"Refuerzo tactico de ETF core por {positive_summary}."
            if _is_country_region_etf(row):
                return f"Refuerzo tactico de ETF pais o region por {positive_summary}."
            if _is_defensive_dividend_stock(row):
                return f"Refuerzo defensivo por {positive_summary}."
            if _is_growth_stock(row):
                return f"Refuerzo growth por {positive_summary}."
            if _is_commodity_stock(row):
                return f"Refuerzo ligado a commodities por {positive_summary}."
            return f"Refuerzo por {positive_summary}."

        if accion == "Reducir":
            if _is_core_etf(row):
                return f"Reduccion de ETF core por {negative_summary}."
            if _is_country_region_etf(row):
                return f"Reduccion de ETF pais o region por {negative_summary}."
            if _is_growth_stock(row):
                return f"Reduccion de growth por {negative_summary}."
            if _is_commodity_stock(row):
                return f"Reduccion ligada a commodities por {negative_summary}."
            return f"Reduccion por {negative_summary}."

        if accion == "Rebalancear / tomar ganancia":
            return "Bono con senal de salida parcial o toma de ganancia."

        if accion == "Desplegar liquidez":
            return "Liquidez identificada como fuente potencial de fondeo."

        if _is_core_etf(row):
            if negative_signals:
                return f"ETF core en monitoreo: pesan {negative_summary}, pero se preserva su rol de cartera."
            return "ETF core en monitoreo por rol estructural dentro de la cartera."

        if _is_country_region_etf(row):
            if positive_signals and not row.get("has_fundamental_support", False):
                return f"ETF pais o region con {positive_summary}, pero con soporte fundamental limitado."
            return "ETF pais o region en monitoreo por senales tacticas mixtas."

        if _is_sector_etf(row):
            if positive_signals and negative_signals:
                return f"ETF sectorial en monitoreo: conviven {positive_summary} con {negative_summary}."
            return "ETF sectorial en monitoreo por falta de senal dominante."

        if _is_growth_stock(row):
            if positive_signals and negative_signals:
                return f"Growth en monitoreo: conviven {positive_summary} con {negative_summary}."
            return "Growth en monitoreo por equilibrio inestable entre potencial y riesgo."

        if _is_defensive_dividend_stock(row):
            if positive_signals and negative_signals:
                return f"Defensivo o dividendos en monitoreo: destacan {positive_summary}, pero pesan {negative_summary}."
            return "Defensivo o dividendos en monitoreo por falta de senal dominante."

        if _is_commodity_stock(row):
            if positive_signals and negative_signals:
                return f"Commodities en monitoreo: destacan {positive_summary}, pero pesan {negative_summary}."
            return "Commodities en monitoreo por senales ciclicas mixtas."

        if _is_argentina_stock(row):
            if positive_signals and negative_signals:
                return f"Accion local en monitoreo: destacan {positive_summary}, pero pesan {negative_summary}."
            return "Accion local en monitoreo por senales locales aun mixtas."

        if positive_signals and negative_signals:
            return f"Mantener por senales mixtas: destacan {positive_summary}, pero pesan {negative_summary}."

        return "Sin senal dominante; mantener y monitorear."

    drivers = out.apply(top_drivers, axis=1)
    out["driver_1"] = drivers.apply(lambda x: x[0] if len(x) > 0 else None)
    out["driver_2"] = drivers.apply(lambda x: x[1] if len(x) > 1 else None)
    out["driver_3"] = drivers.apply(lambda x: x[2] if len(x) > 2 else None)
    out["motivo_score"] = out.apply(motivo_score, axis=1)
    out["motivo_accion"] = out.apply(motivo_accion, axis=1)
    return out
