# Arquitectura UX/UI del Reporte

## Objetivo

Documentar la arquitectura vigente del reporte HTML despues del refactor estructural del renderer.

## Estado actual

La arquitectura base del reporte ya esta implementada y estable:

- portada ejecutiva con `Panorama`
- bloque visible de `Cambios`
- `Decision` priorizada antes de la tabla completa
- `Sizing` y `Regimen` en primera capa
- capas analiticas separadas para tecnico y bonos
- detalle completo relegado a bloques secundarios

La arquitectura tecnica actual del renderer quedo separada en:

- `report_renderer`: orquestacion y timing
- `report_composer`: armado de contexto, secciones y adaptador de inputs del body
- `report_layout`: fachada publica compatible (`build_report_body` + reexports de builders)
- `report_layout_sections`: builders de shell/secciones (panorama, cambios, decision, cartera, integridad, etc.)
- `report_layout_main`: composicion del `main` de la pagina
- `report_page`: orquestacion final (`meta + main + document`)
- `report_meta`: metadatos de documento (tab title / description)
- `report_document`: shell HTML final (`doctype/head/body`)
- `report_assets`: carga de CSS/JS del reporte
- `report_sections`: bloques reutilizables (incluye seccion de riesgo historico)
- `report_decision`: presentacion de tablas y narrativa de decision
- `report_primitives`: helpers HTML reutilizables (focus blocks, tablas, barras)
- `report_operations`: bloque de operaciones recientes y transiciones

El modulo analitico de soporte es:

- `analytics/portfolio_risk.py`: calcula el bundle de riesgo historico que consume `report_sections`

## Flujo de render vigente

1. `report_renderer.render_report(...)`
2. `report_composer.prepare_render_context(...)`
3. `report_composer.build_render_sections(...)`
4. `report_composer.compose_report_body_inputs(...)`
5. `report_layout.build_report_body(...)` (fachada)
6. `report_page.build_report_page(...)`
7. `report_document.build_report_document(...)`

## Capas vigentes

### 1. Lectura ejecutiva

Debe responder rapido:

- que cambio
- que pide accion
- si hay sizing activo
- si existe alguna alerta operacional

Bloques:

- hero de corrida
- KPIs principales
- `Panorama`
- `Cambios`
- highlights de decision

### 2. Decision operativa

Debe exponer:

- refuerzos activos
- reducciones activas
- monitoreo relevante
- tabla completa como segunda capa

### 3. Diagnostico analitico

Debe explicar el contexto:

- regimen de mercado
- overlay tecnico resumido
- bonos locales resumidos
- coberturas y notas del pipeline
- riesgo historico por posicion: drawdown, volatilidad, retorno acumulado con indicador de calidad de historia y circuit breaker `serie_confiable`

### 4. Detalle completo

Reservado para auditoria y revision profunda:

- cartera completa
- tabla tecnica completa
- monitoreo completo de bonos
- chequeos de integridad

## Principios vigentes

- primero decision, despues detalle
- primero cambios, despues stock estable
- primero resumen ejecutivo, despues explicacion analitica
- mantener HTML estatico portable
- no cambiar contratos del pipeline solo por UX

## Deuda abierta

La deuda principal ya no es de estructura del renderer. Hoy la deuda relevante es de calibracion de contenido:

- evitar duplicacion visual entre resumen ejecutivo y tablas
- seguir afinando la narrativa con corridas reales
- mantener la capa de prediccion como observacional mientras no tenga historico suficiente

## Proxima iteracion razonable

La siguiente mejora razonable no es volver a partir el renderer. Es mejorar la lectura con evidencia real:

1. narrativa ejecutiva
2. metricas historicas utiles
3. consistencia entre paneles y tablas

## Restricciones tecnicas

- seguir generando HTML estatico
- mantener compatibilidad entre smoke y real run
- no introducir dependencia frontend pesada
- no duplicar logica de negocio dentro de helpers visuales

## Criterio de exito

La arquitectura se considera sana si:

- el usuario entiende el estado de la corrida sin leer tablas largas
- los cambios materiales dominan la lectura
- el sizing no queda enterrado
- el detalle sigue disponible sin contaminar la portada
- la modularizacion se mantiene estable sin volver a concentrar logica de negocio en `report_renderer.py`
