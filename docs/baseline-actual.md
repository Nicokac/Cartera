# Baseline Actual

## Vigencia

Documento actualizado al `2026-04-18`. Define la baseline funcional vigente del proyecto, no una foto puntual de cartera.

## Capacidades activas

- consolidacion de cartera y liquidez desde IOL
- scoring operativo para CEDEARs, acciones locales, bonos y liquidez
- overlay tecnico con datos de mercado y manejo visible de errores por ticker
- contexto macro y capa local de bonos
- memoria temporal diaria entre corridas
- reporte HTML comun para smoke y real run
- lectura operativa de operaciones recientes y transiciones de posicion

## Estado tecnico vigente

- renderer dividido en:
  - `scripts/report_primitives.py`
  - `scripts/report_operations.py`
  - `scripts/report_renderer.py`
- flujo smoke dividido en:
  - `scripts/smoke_run.py`
  - `scripts/smoke_output.py`
  - `tests/smoke_fixtures.py`
- snapshots operativos canonicos en `data/snapshots/`
- fallback legacy a `tests/snapshots/` controlado por `ENABLE_LEGACY_SNAPSHOTS`
- logging agregado en capas criticas:
  - `valuation`
  - `classify`
  - `bond_analytics`
  - `technical`

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha_efectiva_de_mercado`
- reruns del mismo dia reemplazan la observacion
- corridas de fin de semana o preapertura reutilizan la ultima fecha efectiva de mercado
- el HTML expone:
  - `Accion previa`
  - `Delta Score`
  - `Racha`
- la liquidez no infla los KPIs agregados de persistencia
- `CASH_ARS` y `CAUCION` mantienen continuidad operativa compartida

## Operaciones y snapshots

- el real run puede enriquecer operaciones IOL y explicar:
  - altas nuevas
  - aumentos de posicion
  - reducciones
  - movimientos recientes no consolidados todavia en cartera
- los snapshots previos se validan antes de usarse
- si el sistema recurre a un snapshot legacy, emite un warning explicito

## Baseline de UX del reporte

- navegacion priorizada y sticky
- capa ejecutiva arriba del detalle tabular
- `Panorama`, `Cambios` y `Decision` como entradas principales
- `Sizing` y `Regimen` visibles sin bajar a tablas largas
- capas analiticas separadas:
  - tecnico
  - bonos locales
  - cartera
  - integridad
- detalle completo relegado a segunda capa o bloques colapsables

## Baseline de calidad

- CI basada en `unittest` con suites estables del core, renderer, smoke y clientes
- bootstrap automatico de configuracion de ejemplo antes de tests
- cobertura directa para:
  - `report_primitives`
  - `report_operations`
  - `smoke_run`
  - `smoke_output`

## Deuda real aun abierta

- seguir fragmentando `render_report()` para bajar complejidad del renderer principal
- mantener la documentacion de snapshots alineada cuando se retire el fallback legacy

## Frentes preparados pero no activos

- motor de prediccion direccional auditada:
  - Fase 1 completada: store y trazabilidad documental
  - Fase 2 completada: pesos y umbrales canonicos en `data/mappings/prediction_weights.json`
  - Fase 3 completada: predictor puro por consenso ponderado en `src/prediction/predictor.py`
  - todavia no forma parte de la baseline funcional del pipeline
  - se va a implementar como capa separada del scoring y sizing actuales
  - su arquitectura y trazabilidad viven en:
    - [prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
    - [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
