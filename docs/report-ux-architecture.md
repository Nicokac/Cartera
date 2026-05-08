# Arquitectura UX/UI del Reporte

## Objetivo

Documentar la arquitectura vigente del reporte HTML despues del refactor estructural del renderer.

## Estado actual

La arquitectura base del reporte esta implementada y estable:

- navegacion por vistas (un modulo visible por vez) con opcion `Vista completa`
- portada ejecutiva en `Dashboard`
- modulos separados para `Cartera`, `Decision y Rebalanceo`, `Prediccion`, `Tecnico`, `Bonos y Macro`, `Operaciones`, `Riesgo e Integridad`
- detalle completo relegado a bloques colapsables

La arquitectura tecnica del renderer queda separada en:

- `report_renderer`: orquestacion y timing
- `report_composer`: armado de contexto, secciones y adaptador de inputs
- `report_layout`: fachada publica compatible (`build_report_body` + reexports)
- `report_layout_sections`: builders de shell/secciones
- `report_layout_main`: composicion del `main` por modulos
- `report_page`: orquestacion final (`meta + main + document`)
- `report_meta`: metadatos de documento
- `report_document`: shell HTML final
- `report_assets`: carga de CSS/JS
- `report_sections`: bloques reutilizables
- `report_decision`: tablas y narrativa de decision
- `report_primitives`: helpers HTML reutilizables
- `report_operations`: bloque de operaciones recientes y transiciones

## Flujo de render vigente

1. `report_renderer.render_report(...)`
2. `report_composer.prepare_render_context(...)`
3. `report_composer.build_render_sections(...)`
4. `report_composer.compose_report_body_inputs(...)`
5. `report_layout.build_report_body(...)`
6. `report_page.build_report_page(...)`
7. `report_document.build_report_document(...)`

## Capas de lectura vigentes

### 1. Lectura ejecutiva

Debe responder rapido:

- que cambio
- que pide accion
- si hay sizing activo
- si existe alerta operacional

Bloques:

- hero de corrida
- KPIs principales
- panorama
- cambios
- highlights de decision

### 2. Decision operativa

Debe exponer:

- refuerzos
- reducciones
- monitoreo relevante
- tabla completa como segunda capa

### 3. Diagnostico analitico

Debe explicar contexto:

- regimen de mercado
- overlay tecnico resumido
- bonos locales resumidos
- coberturas y notas del pipeline
- riesgo historico por posicion

### 4. Detalle completo

Reservado para auditoria:

- cartera completa
- tabla tecnica completa
- monitoreo completo de bonos
- chequeos de integridad

## Principios vigentes

- primero decision, despues detalle
- primero cambios, despues stock estable
- primero resumen ejecutivo, despues explicacion analitica
- mantener HTML estatico portable
- no duplicar logica de negocio en helpers visuales

## Deuda abierta

La deuda principal ya no es estructural; es visual:

- consistencia de jerarquia tipografica
- reduccion de densidad por modulo
- sistema visual de componentes (cards/chips/tablas)

## Criterio de exito

La arquitectura se considera sana si:

- el usuario entiende la corrida sin leer tablas largas
- los cambios materiales dominan la lectura
- el sizing no queda enterrado
- el detalle sigue disponible sin contaminar portada
- la modularizacion se mantiene estable
