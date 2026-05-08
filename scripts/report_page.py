from __future__ import annotations

import pandas as pd

from report_document import build_report_document
from report_layout_main import build_report_main_content
from report_meta import build_report_meta


def build_report_page(
    *,
    title: str,
    generated_at_label: object,
    total_ars: float = 0.0,
    total_usd: float = 0.0,
    integrity_status: str = "ok",
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
    tab_title, meta_description = build_report_meta(title=title, generated_at_label=generated_at_label)
    main_content = build_report_main_content(
        title=title,
        generated_at_label=generated_at_label,
        total_ars=total_ars,
        total_usd=total_usd,
        integrity_status=integrity_status,
        headline=headline,
        lede=lede,
        integrity_strip=integrity_strip,
        quick_nav=quick_nav,
        primary_cards=primary_cards,
        secondary_cards=secondary_cards,
        panorama_section=panorama_section,
        changes_section=changes_section,
        operations_section=operations_section,
        prediction_section=prediction_section,
        regime_summary=regime_summary,
        summary_section=summary_section,
        sizing_section=sizing_section,
        tech_enabled=tech_enabled,
        tech_covered=tech_covered,
        tech_total=tech_total,
        technical_view=technical_view,
        price_history=price_history,
        bonistas_section=bonistas_section,
        decision_section=decision_section,
        portfolio_section=portfolio_section,
        integrity_section=integrity_section,
    )
    return build_report_document(
        tab_title=tab_title,
        meta_description=meta_description,
        main_content=main_content,
    )

