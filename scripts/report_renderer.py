from __future__ import annotations

import logging
import time
from pathlib import Path

from report_composer import build_render_sections, prepare_render_context
from report_layout import build_report_body


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
logger = logging.getLogger(__name__)


def render_report(
    result: dict[str, object],
    *,
    title: str = "Smoke Run",
    headline: str = "Prueba visual del pipeline",
    lede: str = "Reporte generado desde <code>scripts/generate_smoke_report.py</code> sin depender del notebook.",
) -> str:
    render_started = time.perf_counter()
    section_timings: dict[str, float] = {}

    def _time_section(name: str, fn):
        started = time.perf_counter()
        value = fn()
        section_timings[name] = round(time.perf_counter() - started, 4)
        return value

    context = prepare_render_context(result)
    sections = build_render_sections(context, time_section=_time_section)
    html_body = _time_section(
        "body",
        lambda: build_report_body(
            title=title,
            headline=headline,
            lede=lede,
            integrity_strip=sections.get("integrity_strip", ""),
            quick_nav=sections["quick_nav"],
            primary_cards=sections["primary_cards"],
            secondary_cards=sections["secondary_cards"],
            action_summary=sections["action_summary"],
            panorama_section=sections["panorama_section"],
            changes_section=sections["changes_section"],
            operations_section=sections["operations_section"],
            prediction_section=sections["prediction_section"],
            regime_summary=sections["regime_summary"],
            summary_section=sections["summary_section"],
            sizing_section=sections["sizing_section"],
            tech_enabled=str(context["tech_enabled"]),
            tech_covered=int(context["tech_covered"]),
            tech_total=int(context["tech_total"]),
            technical_view=context["technical_view"],
            bonistas_section=sections["bonistas_section"],
            decision_section=sections["decision_section"],
            portfolio_section=sections["portfolio_section"],
            integrity_section=sections["integrity_section"],
        ),
    )
    logger.info(
        "Report section timings: total=%.4fs %s",
        time.perf_counter() - render_started,
        " ".join(f"{name}={value:.4f}s" for name, value in section_timings.items()),
    )
    return html_body
