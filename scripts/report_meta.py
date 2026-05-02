from __future__ import annotations


def build_report_meta(*, title: str, generated_at_label: object) -> tuple[str, str]:
    generated_at_text = str(generated_at_label or "").strip()
    generated_date = generated_at_text.split(" ", 1)[0] if generated_at_text else ""
    title_prefix = f"{title} - {generated_date}" if generated_date else title
    tab_title = f"{title_prefix} | Cartera de Activos"
    meta_description = (
        f"{title}. Reporte generado {generated_at_text or 'sin timestamp'} "
        "con panorama, cambios, decisiones, cartera e integridad."
    )
    return tab_title, meta_description

