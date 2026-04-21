from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))
if str(ROOT / "src") not in sys.path:
    sys.path.append(str(ROOT / "src"))

from report_renderer import REPORTS_DIR, render_report
from smoke_run import run_smoke_pipeline


HTML_PATH = REPORTS_DIR / "smoke-report.html"


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    result = run_smoke_pipeline()
    run_ts = pd.Timestamp.now(tz=ZoneInfo("America/Argentina/Buenos_Aires"))
    result["generated_at_label"] = run_ts.strftime("%Y-%m-%d %H:%M:%S")
    html_body = render_report(result)
    HTML_PATH.write_text(html_body, encoding="utf-8")
    print(f"Reporte generado en: {HTML_PATH}")


if __name__ == "__main__":
    main()
