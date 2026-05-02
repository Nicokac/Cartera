from __future__ import annotations

import pandas as pd

from report_primitives import build_collapsible, build_technical_table, esc_text
from report_sections import build_technical_summary


def build_report_main_content(
    *,
    title: str,
    headline: str,
    lede: str,
    integrity_strip: str,
    quick_nav: str,
    primary_cards: str,
    secondary_cards: str,
    panorama_section: str,
    changes_section: str,
    operations_section: str,
    prediction_section: str,
    regime_summary: str,
    summary_section: str,
    sizing_section: str,
    tech_enabled: str,
    tech_covered: int,
    tech_total: int,
    technical_view: pd.DataFrame,
    price_history: dict | None,
    bonistas_section: str,
    decision_section: str,
    portfolio_section: str,
    integrity_section: str,
) -> str:
    return f"""  <main class=\"page\">
    {build_report_hero(title=title, headline=headline, lede=lede)}

    {integrity_strip}
    {quick_nav}

    {build_dashboard_module(
        primary_cards=primary_cards,
        secondary_cards=secondary_cards,
        panorama_section=panorama_section,
        changes_section=changes_section,
        regime_summary=regime_summary,
    )}

    <section class=\"module-block module-portfolio\" id=\"module-cartera\">
      <header class=\"module-head\">
        <p class=\"module-kicker\">Módulo</p>
        <h2>Cartera</h2>
      </header>
      <section class=\"portfolio-pulse\">
        <article class=\"portfolio-item\"><strong>Composición</strong><span>Tipos, pesos y mayor posición</span></article>
        <article class=\"portfolio-item\"><strong>Posiciones</strong><span>Vista completa por ticker</span></article>
        <article class=\"portfolio-item\"><strong>Pendientes</strong><span>Tenencias fuera de consolidación</span></article>
      </section>
      {portfolio_section}
    </section>

    <section class=\"module-block module-decision\" id=\"module-decision\">
      <header class=\"module-head\">
        <p class=\"module-kicker\">Módulo</p>
        <h2>Decisión y Rebalanceo</h2>
      </header>
      {decision_section}
      {sizing_section}
    </section>

    {build_prediction_module(prediction_section=prediction_section)}

    <section class=\"module-block module-technical\" id=\"module-tecnico\">
      <header class=\"module-head\">
        <p class=\"module-kicker\">Módulo</p>
        <h2>Técnico</h2>
      </header>
      {build_technical_panel(
        tech_enabled=tech_enabled,
        tech_covered=tech_covered,
        tech_total=tech_total,
        technical_view=technical_view,
        price_history=price_history,
      )}
    </section>

    <section class=\"module-block module-bonds\" id=\"module-bonos\">
      <header class=\"module-head\">
        <p class=\"module-kicker\">Módulo</p>
        <h2>Bonos y Macro</h2>
      </header>
      <section class=\"module-subblock\" id=\"bonos-resumen\">
        <div class=\"meta\">
          <span>Foco: <strong>Macro local + renta fija</strong></span>
          <span>Incluye: <strong>subfamilias, taxonomía y monitoreo completo</strong></span>
        </div>
      </section>
      <section class=\"module-subblock\" id=\"bonos-detalle\">
        {build_collapsible("Ver bonos y contexto macro", bonistas_section, compact=True)}
      </section>
    </section>

    {build_operations_module(operations_section=operations_section)}

    <section class=\"module-block module-risk\" id=\"module-riesgo\">
      <header class=\"module-head\">
        <p class=\"module-kicker\">Módulo</p>
        <h2>Riesgo e Integridad</h2>
      </header>
      <section class=\"risk-pulse\">
        <article class=\"risk-item\"><strong>Riesgo histórico</strong><span>Retorno, volatilidad y drawdown</span></article>
        <article class=\"risk-item\"><strong>Integridad</strong><span>Chequeos y alertas de consistencia</span></article>
      </section>
      <section class=\"module-subblock\" id=\"riesgo-resumen\">
        {build_collapsible("Ver resumen de cartera y riesgo", summary_section, compact=True)}
      </section>
      <section class=\"module-subblock\" id=\"riesgo-integridad\">
        {integrity_section}
      </section>
    </section>
  </main>"""


def build_report_hero(*, title: str, headline: str, lede: str) -> str:
    return f"""<header class=\"hero\">
      <div>
        <p class=\"eyebrow\">{esc_text(title)}</p>
        <h1>{esc_text(headline)}</h1>
        <p class=\"lede\">{lede}</p>
      </div>
    </header>"""


def build_technical_panel(
    *,
    tech_enabled: str,
    tech_covered: int,
    tech_total: int,
    technical_view: pd.DataFrame,
    price_history: dict | None,
) -> str:
    return f"""<section class=\"panel\" id=\"tecnico\">
      <h2>Lectura técnica</h2>
      <section class=\"module-subblock\" id=\"tecnico-resumen\">
        <div class=\"meta\">
          <span>Activo: <strong>{tech_enabled}</strong></span>
          <span>Cobertura: <strong>{tech_covered}/{tech_total}</strong></span>
        </div>
        {build_technical_summary(technical_view)}
      </section>
      <section class=\"module-subblock\" id=\"tecnico-detalle\">
        {build_collapsible("Ver tabla técnica completa", build_technical_table(technical_view, price_history=price_history or {}), compact=True)}
      </section>
    </section>"""


def build_dashboard_module(
    *,
    primary_cards: str,
    secondary_cards: str,
    panorama_section: str,
    changes_section: str,
    regime_summary: str,
) -> str:
    return f"""<section class=\"module-block module-dashboard\" id=\"module-dashboard\">
    <header class=\"module-head\">
      <p class=\"module-kicker\">Módulo</p>
      <h2>Dashboard Ejecutivo</h2>
    </header>
    <section class=\"dashboard-pulse module-subblock\" id=\"dashboard-foco\">
      <a class=\"pulse-item\" href=\"#module-decision\"><strong>Ir a Decisión</strong><span>Rebalanceo y acción sugerida</span></a>
      <a class=\"pulse-item\" href=\"#module-cartera\"><strong>Ir a Cartera</strong><span>Composición y exposición</span></a>
      <a class=\"pulse-item\" href=\"#module-riesgo\"><strong>Ir a Riesgo</strong><span>Integridad y diagnóstico</span></a>
    </section>
    <section class=\"module-subblock\" id=\"dashboard-detalle\">
      {primary_cards}
      {secondary_cards}
      {panorama_section}
      {build_collapsible("Ver cambios y cobertura", changes_section, compact=True)}
      {regime_summary}
    </section>
    </section>"""


def build_operations_module(*, operations_section: str) -> str:
    operations_block = build_collapsible("Ver operaciones recientes", operations_section, compact=True) if operations_section.strip() else ""
    return f"""<section class=\"module-block module-analysis\" id=\"module-analisis\">
    <header class=\"module-head\">
      <p class=\"module-kicker\">Módulo</p>
      <h2>Operaciones</h2>
    </header>
    <section class=\"analysis-pulse module-subblock\" id=\"operaciones-resumen\">
      <article class=\"analysis-item\"><strong>Actividad reciente</strong><span>Compras, ventas y eventos recientes</span></article>
      <article class=\"analysis-item\"><strong>Impacto operativo</strong><span>Cambios observados contra snapshot previo</span></article>
      <article class=\"analysis-item\"><strong>Auditoría</strong><span>Detalle completo por símbolo y operación</span></article>
    </section>
    <section class=\"module-subblock\" id=\"operaciones-detalle\">
      {operations_block}
    </section>
    </section>"""


def build_prediction_module(*, prediction_section: str) -> str:
    prediction_block = build_collapsible("Ver señales y predicción", prediction_section, compact=True) if prediction_section.strip() else ""
    return f"""<section class=\"module-block module-prediction\" id=\"module-prediccion\">
    <header class=\"module-head\">
      <p class=\"module-kicker\">Módulo</p>
      <h2>Predicción</h2>
    </header>
    <section class=\"prediction-pulse module-subblock\" id=\"prediccion-resumen\">
      <article class=\"prediction-item\"><strong>Dirección esperada</strong><span>Distribución suba, baja y neutral</span></article>
      <article class=\"prediction-item\"><strong>Confianza</strong><span>Lectura de convicción y validación histórica</span></article>
      <article class=\"prediction-item\"><strong>Detalle de señales</strong><span>Drivers por ticker y horizonte objetivo</span></article>
    </section>
    <section class=\"module-subblock\" id=\"prediccion-detalle\">
      {prediction_block}
    </section>
    </section>"""


