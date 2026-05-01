# Plan de Embellecimiento UI del Reporte (post v0.5.3)

Fecha: 2026-05-01

Version de referencia: 0.5.3

## Objetivo

Mejorar la calidad visual y la claridad del reporte HTML sin romper el flujo actual de una sola página.

## 1) Auditoría estructural actual

### Layout shell (estructura global)

- Archivo principal: `scripts/report_layout.py` (`build_report_body`)
- Responsabilidades actuales:
  - `<head>` + CSS inline (`static/styles.css`)
  - orden de secciones y composición de página
  - JS de interacción (filtros, sort, quick-nav, overflow, persistencia de `details`)

### Componentes reutilizables

- `report_primitives.py`: `build_table`, `build_collapsible`, `build_focus_list`, formateadores
- `report_layout.py`: `build_header_cards`, `build_quick_nav`, `build_decision_section`, etc.
- `report_sections.py` / `report_sections_prediction.py`: bloques por dominio reutilizables

### Contenido de módulos (dominio)

- Composición por dominio en:
  - `scripts/report_sections.py`
  - `scripts/report_sections_prediction.py`
  - `scripts/report_operations.py`
  - `scripts/report_decision.py`
  - `scripts/report_sections_risk.py`

### Hallazgos clave

- La arquitectura Python ya está semi-modular (compositor + secciones), pero:
  - el JS de UI está centralizado en un único bloque largo dentro de `build_report_body`
  - el shell visual y la lógica de interacción están acoplados
  - la jerarquía visual depende más del orden lineal que de “capas de lectura”

## 2) Arquitectura objetivo (misma página, más modular)

### Principio

Mantener single-page, pero separar responsabilidades en 3 capas:

1. Shell visual
- Layout general, hero, quick-nav, slots de secciones

2. UI components
- cards, badges/chips, tablas, paneles colapsables, bloques de highlights

3. Module content
- cada sección de negocio solo produce contenido (sin lógica de navegación/filtro global)

### Refactor técnico incremental

- Paso A: extraer JS inline a `static/report-ui.js` (sin cambiar comportamiento)
- Paso B: introducir helpers de render para “primitivas visuales” faltantes:
  - `build_badge`, `build_kpi_tile`, `build_section_header`
- Paso C: normalizar clases CSS por sistema:
  - layout (`l-*`), componentes (`c-*`), utilidades (`u-*`), estados (`is-*`)

## 3) Prioridades visuales (qué va arriba y qué se colapsa)

### Siempre visible (arriba)

- KPIs core
- Panorama ejecutivo
- Alertas/acciones relevantes (refuerzo/reducción)

### Colapsable por defecto

- tablas extensas (decisión completa, cartera completa, operaciones completas)
- diagnósticos largos (riesgo detallado, técnico extendido)

### Candidatos a visual fuerte (sin romper simplicidad)

- sparkline mini para momentum/rendimiento
- chips semánticos para estado/convicción/calidad de historia
- barras compactas para distribución de tipos y acciones

## 4) Plan de implementación visual

### Fase UI-1 (base visual segura)

- tokenizar estilos (colores, espacios, radios, tipografía)
- mejorar jerarquía de encabezados y densidad de cards
- unificar estados (success/warn/error/info)

### Fase UI-2 (legibilidad de datos)

- tablas con header sticky y zebra sutil
- controles de tabla más claros (filtro/sort visibles)
- mejoras de contraste y foco teclado

### Fase UI-3 (realce analítico)

- sparklines en filas clave
- micro-gráficos de distribución en resumen/decisión
- badges de “calidad de historia” y “confianza”

## 5) Qué probar en cada cambio (solo si aplica)

### Si se toca render/layout/CSS/JS del reporte

- `python -m unittest tests.test_report_render_core tests.test_report_render_ui tests.test_report_primitives -v`
- generar `reports/real-report.html` y validar manualmente:
  - quick-nav sticky + link activo por scroll
  - filtros/sort de decisión
  - persistencia de `details` abierta/cerrada
  - sin overflow horizontal global

### Si se toca lógica de secciones (resumen, predicción, riesgo, bonos)

- correr tests específicos del módulo afectado (ejemplos):
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

- Documento creado como guía de ejecución para la etapa de embellecimiento.
- No reemplaza `docs/product-roadmap.md`; lo complementa como stream UI post-cierre v0.5.
