from __future__ import annotations

import logging
import time
from pathlib import Path

from report_composer import (
    build_render_sections,
    compose_report_body_inputs,
    prepare_render_context,
)
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
    body_inputs = compose_report_body_inputs(
        context=context,
        sections=sections,
        title=title,
        headline=headline,
        lede=lede,
    )
    html_body = _time_section(
        "body",
        lambda: build_report_body(**body_inputs),
    )
    logger.info(
        "Report section timings: total=%.4fs %s",
        time.perf_counter() - render_started,
        " ".join(f"{name}={value:.4f}s" for name, value in section_timings.items()),
    )
    return html_body
