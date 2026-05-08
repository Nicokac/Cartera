# Plan de Embellecimiento UI del Reporte (post v0.5.4)

Fecha: 2026-05-08

Version de referencia: 0.5.4

## Objetivo

Mejorar la calidad visual y la claridad del reporte HTML sin romper el flujo actual de una sola pagina.

## 1) Auditoria estructural actual

### Layout shell (estructura global)

- Archivos principales:
  - `scripts/report_layout.py` (`build_report_body`)
  - `scripts/report_layout_main.py` (composicion del `main`)
  - `scripts/report_layout_sections.py` (secciones shell)
- Responsabilidades actuales:
  - orden de secciones y composicion de pagina
  - navegacion por vistas (`report-view` + `data-target-view`)
  - JS de interaccion en `static/report-ui.js`

### Componentes reutilizables

- `report_primitives.py`: `build_table`, `build_collapsible`, `build_focus_list`, formateadores
- `report_layout_sections.py`: `build_header_cards`, `build_quick_nav`, `build_decision_section`, etc.
- `report_sections.py` / `report_sections_prediction.py`: bloques por dominio reutilizables

### Contenido de modulos (dominio)

- Composicion por dominio en:
  - `scripts/report_sections.py`
  - `scripts/report_sections_prediction.py`
  - `scripts/report_operations.py`
  - `scripts/report_decision.py`
  - `scripts/report_sections_risk.py`

### Hallazgos clave

- La arquitectura Python ya esta modularizada para evolucion visual incremental.
- La navegacion por vistas ya reemplaza la lectura lineal densa del reporte.
- La deuda principal pasa a ser visual (jerarquia, densidad, consistencia de componentes), no estructural.

## 2) Arquitectura objetivo (misma pagina, mas modular)

### Principio

Mantener single-page, separando responsabilidades en 3 capas:

1. Shell visual
- Layout general, hero, quick-nav, slots de secciones.

2. UI components
- cards, badges/chips, tablas, paneles colapsables, bloques de highlights.

3. Module content
- cada seccion de negocio produce contenido, sin logica global de navegacion.

## 3) Prioridades visuales (que va arriba y que se colapsa)

### Siempre visible (arriba)

- KPIs core
- Panorama ejecutivo
- Alertas/acciones relevantes (refuerzo/reduccion)

### Colapsable por defecto

- tablas extensas (decision completa, cartera completa, operaciones completas)
- diagnosticos largos (riesgo detallado, tecnico extendido)

### Candidatos a visual fuerte (sin romper simplicidad)

- sparklines mini para momentum/rendimiento
- chips semanticos para estado/conviccion/calidad de historia
- barras compactas para distribucion de tipos y acciones

## 4) Plan de implementacion visual

### Fase UI-1 (base visual segura)

- tokenizar estilos (colores, espacios, radios, tipografia)
- mejorar jerarquia de encabezados y densidad de cards
- unificar estados (success/warn/error/info)

### Fase UI-2 (legibilidad de datos)

- tablas con header sticky y zebra sutil
- controles de tabla mas claros (filtro/sort visibles)
- mejoras de contraste y foco teclado

### Fase UI-3 (realce analitico)

- sparklines en filas clave
- micro-graficos de distribucion en resumen/decision
- badges de calidad de historia y confianza

## 5) Que probar en cada cambio (solo si aplica)

### Si se toca render/layout/CSS/JS del reporte

- `python -m unittest tests.test_report_render_core tests.test_report_render_ui tests.test_report_primitives -v`
- generar `reports/real-report.html` y validar manualmente:
  - quick-nav por vistas
  - filtros/sort de decision
  - persistencia de `details`
  - copy de sizing
  - descarga CSV sin entidades escapadas
  - sin overflow horizontal global

### Si se toca logica de secciones (resumen, prediccion, riesgo, bonos)

- correr tests especificos del modulo afectado (ejemplos):
  - `tests.test_report_sections`
  - `tests.test_report_sections_prediction`
  - `tests.test_report_operations`

### Si se toca server/UI local (token/endpoints/reportes)

- `python -m unittest tests.test_server -v`
- smoke manual:
  - abrir app local
  - generar corrida
  - abrir reporte actual y anterior

## Estado

- Documento actualizado como guia de ejecucion para la etapa de embellecimiento.
- No reemplaza `docs/product-roadmap.md`; lo complementa como stream UI post-cierre v0.5.

## Contrato IA

- Referencia de arquitectura de informacion: `docs/report-ia-architecture.md`.
- Este contrato define modulos, jerarquia de lectura y backlog P1/P2/P3 previo al embellecimiento visual fino.
