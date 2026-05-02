from __future__ import annotations

from functools import lru_cache
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_STATIC_DIR = _ROOT / "static"
_CSS_PATH = _STATIC_DIR / "styles.css"
_JS_PATH = _STATIC_DIR / "report-ui.js"


@lru_cache(maxsize=1)
def load_report_css() -> str:
    return _CSS_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_report_js() -> str:
    return _JS_PATH.read_text(encoding="utf-8")

