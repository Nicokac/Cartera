from __future__ import annotations

import pandas as pd


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def render_smoke_output(result: dict[str, object]) -> None:
    mep_real = float(result["mep_real"])
    portfolio_bundle = result["portfolio_bundle"]
    dashboard_bundle = result["dashboard_bundle"]
    decision_bundle = result["decision_bundle"]
    sizing_bundle = result["sizing_bundle"]
    operations_bundle = result["operations_bundle"]

    df_total = portfolio_bundle["df_total"]
    final_decision = decision_bundle["final_decision"]

    print_section("Smoke Run")
    print(f"MEP usado: ${mep_real:,.2f}")
    print(f"Instrumentos totales: {len(df_total)}")
    print(f"Total ARS: ${df_total['Valorizado_ARS'].sum():,.0f}")
    print(f"Total USD: USD {df_total['Valor_USD'].sum():,.2f}")
    print(f"Peso total: {df_total['Peso_%'].sum():.2f}%")

    print_section("Integridad")
    print(portfolio_bundle["integrity_report"].to_string(index=False))

    print_section("Dashboard")
    print(pd.Series(dashboard_bundle["kpis"]).to_string())

    print_section("Decision")
    decision_cols = ["Ticker_IOL", "Tipo", "score_unificado", "accion_sugerida_v2", "motivo_accion"]
    print(final_decision[decision_cols].sort_values("score_unificado", ascending=False).to_string(index=False))

    print_section("Sizing")
    print(f"Fuente de fondeo: {sizing_bundle['fuente_fondeo']}")
    print(f"Pct fondeo: {sizing_bundle['pct_fondeo']:.0%}")
    print(f"Monto fondeo ARS: ${sizing_bundle['monto_fondeo_ars']:,.0f}")
    asignacion = sizing_bundle["asignacion_final"]
    if asignacion.empty:
        print("Sin asignacion final generada.")
    else:
        sizing_cols = ["Ticker_IOL", "Bucket_Prudencia", "Peso_Fondeo_%", "Monto_ARS", "Monto_USD"]
        print(asignacion[sizing_cols].to_string(index=False))

    print_section("Operaciones")
    print(f"Snapshot previo: {operations_bundle.get('previous_snapshot_date')}")
    print(pd.Series(operations_bundle["stats"]).to_string())
    if not operations_bundle["recent_operations"].empty:
        operation_cols = ["simbolo", "tipo", "estado", "fecha_evento", "monto_final"]
        print(operations_bundle["recent_operations"][operation_cols].to_string(index=False))
