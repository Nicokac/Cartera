from __future__ import annotations

from report_assets import load_report_css, load_report_js
from report_primitives import esc_text


def build_report_document(*, tab_title: str, meta_description: str, main_content: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc_text(tab_title)}</title>
  <meta name="description" content="{esc_text(meta_description)}">
  <style>{load_report_css()}</style>
</head>
<body>
{main_content}
  <script>{load_report_js()}</script>
</body>
</html>
"""

