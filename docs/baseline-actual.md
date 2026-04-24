# Baseline Actual

## Vigencia

Documento actualizado al `2026-04-24`. Define la baseline funcional vigente del proyecto, no una foto puntual de cartera.

## Capacidades activas

- consolidacion de cartera y liquidez desde IOL
- scoring operativo para CEDEARs, acciones locales, bonos y liquidez
- overlay tecnico con datos de mercado y manejo visible de errores por ticker
- contexto macro y capa local de bonos
- memoria temporal diaria entre corridas
- reporte HTML comun para smoke y real run
- lectura operativa de operaciones recientes y transiciones de posicion
- clasificacion de FCIs reales (IOLPORA, ADBAICA, PRPEDOB) como posiciones visibles en cartera, separadas de la liquidez tactica
- diferenciacion entre alta genuina y reclasificacion de posicion en el bloque operacional del reporte
- capa experimental de prediccion direccional con historial, verificacion, recalibracion y conviction_label
- metricas historicas de riesgo por posicion y portfolio agregado (`analytics/portfolio_risk.py`): drawdown, volatilidad y retorno acumulado con metodologia de universo comparable y circuit breaker `serie_confiable`

## Estado tecnico vigente

- renderer dividido en:
  - `scripts/report_decision.py`
  - `scripts/report_sections.py`
  - `scripts/report_layout.py`
  - `scripts/report_composer.py`
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
  - altas nuevas (`change_kind = "alta_nueva"`)
  - reclasificaciones (`change_kind = "reclasificacion"`): ticker que ya existia en el snapshot previo bajo otra taxonomia (ej: FCI antes clasificado como Liquidez)
  - aumentos de posicion
  - reducciones
  - movimientos recientes no consolidados todavia en cartera
- `build_position_transition_bundle` distingue entre ticker genuinamente nuevo (ausente del snapshot previo) y ticker reclasificado (presente pero con Tipo diferente) — la distincion se hace contra el portfolio previo sin filtrar, antes de que `prepare_portfolio_for_compare` descarte liquidez
- los snapshots previos se validan antes de usarse
- la validacion previa ahora exige:
  - columna `Ticker_IOL`
  - al menos una fila utilizable con ticker no vacio
  - coercion numerica defensiva en columnas opcionales relevantes para comparacion
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

- CI basada en `unittest` con 37 suites estables del core, renderer, smoke, clientes y analytics
- bootstrap automatico de configuracion de ejemplo antes de tests
- cobertura directa para:
  - `report_primitives`, `report_operations`, `report_sections`
  - `smoke_run`, `smoke_output`
  - `decision/actions`, `decision/scoring`
  - `analytics/portfolio_risk`
- suite local: 358/358 OK

## Clasificacion de FCIs

- `FCI_REPORTED_AS_FUND = {"IOLPORA", "ADBAICA", "PRPEDOB"}` en `src/portfolio/liquidity.py`
- estos tres FCIs se muestran como posiciones reales (Tipo=FCI, Bloque=FCI, Es_Liquidez=False), no como liquidez tactica
- `FCI_CASH_MANAGEMENT` quedo vacio: ningun FCI actual se trata como caja gestionada
- los tres tienen perfil en `data/mappings/instrument_profile_map.json`:
  - ADBAICA y PRPEDOB: `asset_family=fci`, `asset_subfamily=fci_renta_fija_usd` (soberana ley extranjera)
  - IOLPORA: `asset_family=fci`, `asset_subfamily=fci_renta_fija_ars`
- el `block_map.json` los registra como `"FCI"` (ya no `"Liquidez"`)

## Deuda real aun abierta

- mantener la documentacion de snapshots alineada cuando se retire el fallback legacy
- seguir observando la capa experimental de prediccion con historico real antes de convertirla en senal mas fuerte
- calibracion por `asset_family` en el motor de prediccion: bloqueada por datos (requiere >= 30 outcomes verificados por familia x senal)
- `decision/scoring.py` (885 ln): cobertura unitaria directa ampliada para `build_decision_base` y `apply_base_scores`; seguir cubriendo ramas de calibracion avanzada y overlays tecnicos
- `test_report_render.py` (~1109 ln): candidato a split por dominio cuando supere 1200 ln (O-006)

## Capa experimental integrada

- motor de prediccion direccional auditada:
  - Fase 1 completada: store y trazabilidad documental
  - Fase 2 completada: pesos y umbrales canonicos en `data/mappings/prediction_weights.json`
  - Fase 3 completada: predictor puro por consenso ponderado en `src/prediction/predictor.py`
  - Fase 4 completada: verificador de outcomes en `src/prediction/verifier.py`
  - Fase 5 completada: calibracion de pesos en `src/prediction/calibration.py`
  - Fase 6 completada: integracion experimental al pipeline, renderer y runner de mantenimiento
  - Fase 6.1 completada: correccion de escala del voto `score_unificado`
  - Fase 6.2 completada: zona muerta en votos continuos, RSI continuo, `IC <= 0` apaga senal
  - Fase 6.3 completada: calibracion rolling con fallback al historico completo
  - Fase 7 completada: ADX continuo y relative_volume continua incorporados
  - Hardening de senales: `sma_trend` con votos graduados, `relative_volume` con escala continua
  - `conviction_label` integrado: calculado en `predict()` desde `conviction_thresholds` JSON, persistido en CSV, renderizado en HTML
  - ya forma parte del smoke y del real run como capa observacional
  - sigue separada del scoring y sizing operativos
  - ciclo operativo vigente:
    - `generate_real_report.py` construye el bundle, persiste observaciones nuevas y expone la seccion HTML
    - `run_prediction_cycle.py` consume el historial existente para verificar outcomes y recalibrar pesos
    - el runner de mantenimiento no genera observaciones nuevas por si solo
  - su arquitectura y trazabilidad viven en:
    - [prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
    - [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
