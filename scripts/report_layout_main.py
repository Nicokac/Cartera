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
    return f"""  <main class="page">
    {build_report_hero(title=title, headline=headline, lede=lede)}

    {integrity_strip}
    {quick_nav}

    {build_report_sections_shell(
        primary_cards=primary_cards,
        secondary_cards=secondary_cards,
        panorama_section=panorama_section,
        changes_section=changes_section,
        operations_section=operations_section,
        prediction_section=prediction_section,
        regime_summary=regime_summary,
        summary_section=summary_section,
        sizing_section=sizing_section,
    )}

    {build_technical_panel(
        tech_enabled=tech_enabled,
        tech_covered=tech_covered,
        tech_total=tech_total,
        technical_view=technical_view,
        price_history=price_history,
    )}

    {bonistas_section}
    {decision_section}
    {portfolio_section}
    {integrity_section}
  </main>"""


def build_report_hero(*, title: str, headline: str, lede: str) -> str:
    return f"""<header class="hero">
      <div>
        <p class="eyebrow">{esc_text(title)}</p>
        <h1>{esc_text(headline)}</h1>
        <p class="lede">{lede}</p>
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
    return f"""<section class="panel" id="tecnico">
      <h2>Overlay t\u00e9cnico</h2>
      <div class="meta">
        <span>Activo: <strong>{tech_enabled}</strong></span>
        <span>Cobertura: <strong>{tech_covered}/{tech_total}</strong></span>
      </div>
      {build_technical_summary(technical_view)}
      {build_collapsible("Ver tabla t\u00e9cnica completa", build_technical_table(technical_view, price_history=price_history or {}), compact=True)}
    </section>"""


def build_report_sections_shell(
    *,
    primary_cards: str,
    secondary_cards: str,
    panorama_section: str,
    changes_section: str,
    operations_section: str,
    prediction_section: str,
    regime_summary: str,
    summary_section: str,
    sizing_section: str,
) -> str:
    return f"""{primary_cards}
    {secondary_cards}
    {panorama_section}
    {changes_section}
    {operations_section}
    {prediction_section}
    {regime_summary}

    {summary_section}

    {sizing_section}"""

