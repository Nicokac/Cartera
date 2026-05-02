# Checklist: Report UI Ready for Visual Redesign

Fecha: 2026-05-01

Version base: `0.5.3`

## Objetivo

Confirmar que el renderer de `real-report` quedo suficientemente desacoplado y estable para iniciar embellecimiento visual sin reabrir deuda estructural.

## Criterios de salida (deben estar en `OK`)

- `OK` pipeline de render modularizado:
  - `report_renderer` (orquestacion)
  - `report_composer` (contexto + secciones + adaptador de inputs)
  - `report_layout` (fachada publica)
  - `report_layout_sections` (builders de secciones)
  - `report_page` / `report_document` / `report_meta` / `report_assets`
- `OK` JS de interaccion separado en `static/report-ui.js` (sin bloque largo inline en layout)
- `OK` CSS centralizado en `static/styles.css` y cargado por `report_assets`
- `OK` contratos internos reforzados en composer (`TypedDict` para `RenderSections` y `ReportBodyInputs`)
- `OK` `prepare_render_context(...)` reducido mediante sub-builders privados
- `OK` `render_report(...)` desacoplado de claves internas por `compose_report_body_inputs(...)`
- `OK` suite de render estable en verde:
  - `tests.test_report_render_ui`
  - `tests.test_report_render_core`
  - `tests.test_report_primitives`
- `OK` documentacion alineada:
  - `docs/report-ux-architecture.md`
  - `docs/report-ui-embellecimiento-plan.md`
  - `docs/product-roadmap.md`
  - `CHANGELOG.md`

## Gate de inicio para embellecimiento

Si todos los criterios anteriores estan en `OK`, el siguiente stream habilitado es:

1. mejoras de jerarquia visual y densidad de informacion
2. rediseño de componentes (cards, chips, tablas, headers)
3. visualizaciones ligeras (sparklines / barras compactas)
4. ajuste final de accesibilidad visual y responsive

## Prueba minima previa a cada bloque visual (si aplica)

- `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- generar `reports/real-report.html`
- validar manualmente:
  - quick-nav activo
  - filtros/sort de decision
  - persistencia de `details`
  - sin overflow horizontal global

