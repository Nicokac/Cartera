# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y versionado [SemVer](https://semver.org/lang/es/).

## [Unreleased]

### Added

- endpoint `POST /cancel` en `server.py` para cancelar corridas en progreso
- boton `Cancelar corrida` en `static/index.html` (visible solo en estado `running`)
- cobertura de cancelacion en `tests/test_server.py` (endpoint y transicion a `interrupted`)
- recuperacion de corrida huerfana al startup en `server.py`:
  - persistencia de PID de corrida en `data/runtime/server_run.pid`
  - deteccion al iniciar servidor y marcado de estado `interrupted`
  - intento de terminar el proceso huerfano si sigue vivo
- backup diario automatico de runtime CSVs en corridas reales:
  - nuevo helper `backup_runtime_csvs_impl` en `scripts/generate_real_report_runtime.py`
  - integracion en `run_real_report` para copiar `data/runtime/*.csv` a `data/backups/YYYY-MM-DD/`
- scripts Bash Fase 1 para operacion local cross-platform (macOS/Linux):
  - `scripts/setup_local_app.sh`
  - `scripts/start_local_app.sh`
  - `scripts/status_local_app.sh`
  - `scripts/stop_local_app.sh`
  - `scripts/smoke_local_app.sh`
  - `scripts/run_local_app.sh`
- endpoint `GET /reports/list` en `server.py` para listar reportes HTML disponibles
- token de sesion simple para corridas:
  - `GET /session` devuelve token actual
  - `POST /run` exige header `X-Session-Token`
  - persistencia en `data/runtime/session.txt`
- validaciones de entrada en `POST /run`:
  - `aporte_externo_ars` debe ser `>= 0`
  - `username` y `password` limitados a 200 caracteres
- soporte de logging estructurado opcional en runner real:
  - variable de entorno `LOG_FORMAT=json`
  - salida JSON por linea con `ts`, `level`, `logger`, `message`
- `CONTRIBUTING.md` con guia de colaboracion:
  - setup local
  - convenciones de codigo
  - estrategia de testing por area
  - flujo sugerido de PR y mantenimiento de docs/changelog
- ADRs iniciales en `docs/decisions/`:
  - `ADR-0001` runner en subprocess
  - `ADR-0002` persistencia operativa en CSV (sin DB por ahora)
  - `ADR-0003` migracion gradual de `float` a `Decimal` para montos
- `docs/instrument-onboarding-checklist.md`: checklist formal para alta de
  instrumentos (taxonomia, mappings, validacion funcional, tests y cierre documental)
- `README.md`: referencia explicita a docs de API local de FastAPI:
  - `/docs`
  - `/openapi.json`
- `server.py`: nuevo endpoint `GET /runs/recent` con ultimas 5 corridas
- `static/index.html`: nueva seccion `Corridas recientes` consumiendo `/runs/recent`
- `static/index.html`: indicador de progreso estimado durante corrida
  (barra + etapa textual en estado `running`)
- documentacion explicita de umbrales de madurez historica (Dimension 19):
  - `README.md`: 10 corridas (`racha`), 20 observaciones (`serie_confiable`), 30 outcomes por familia (calibracion)
  - `docs/ayuda-usuario.txt`: mismos umbrales en FAQ operativa
- entorno de contenedor para desarrollo/testing:
  - `Dockerfile` base Python 3.12 slim con dependencias del proyecto
  - `.dockerignore` para excluir artefactos locales/runtime en build
  - instrucciones de uso en `README.md`
- validacion de riesgo historico contra benchmark externo (MEP):
  - `generate_real_report.py` construye serie diaria de benchmark desde ArgentinaDatos
  - `analytics/portfolio_risk.py` agrega `benchmark_validation` cuando la serie agregada es confiable
  - `report_sections.py` expone estado, observaciones, correlacion y tracking error en el bloque de riesgo
- revision de thresholds de scoring con evidencia historica:
  - `prediction_history.csv` ahora persiste `score_unificado`
  - `generate_real_report.py` agrega metrica `by_score_band` en accuracy de prediccion
  - `report_sections_prediction.py` muestra `Acierto por banda de score` en el HTML
- avance de calibracion por familia (Dimension 19 P3):
  - `generate_real_report.py` agrega `calibration_readiness` por `asset_family`
    con conteos `up/down/neutral` y umbral `30` por señal
  - `report_sections_prediction.py` muestra bloque `Preparación calibración por familia`
- calibracion por `asset_family` en motor de calibracion:
  - `prediction.calibration` soporta modo opt-in `calibration.family_enabled`
  - genera `family_overrides` por familia/señal con gating por muestra y por señal
  - conserva calibracion global existente como comportamiento por defecto
- avance multi-horizonte en prediccion:
  - `generate_real_report.py` agrega `by_horizon` en métricas de accuracy
  - `report_sections_prediction.py` muestra bloque `Acierto por horizonte`
  - permite comparar precisión histórica por `horizon_days`
- clasificador B experimental sobre `signal_votes`:
  - `prediction.predictor` agrega salida alternativa (`classifier_b_direction`, `classifier_b_confidence`, `classifier_b_agrees`)
  - `pipeline` y `prediction_store` persisten métricas del clasificador B
  - `report_sections_prediction.py` expone KPI `Coincidencia clasificador B`
- CI DevOps:
  - `.github/workflows/ci.yml` vuelve a exigir unittest en `ubuntu-latest` y `macos-latest` como checks bloqueantes
- hotfix CI:
  - `pyproject.toml` reescrito en UTF-8 sin BOM para evitar error de parseo en `coverage` (`Invalid statement at line 1`)
- reporte HTML: nuevo bloque `Evolución de racha` en prioridades de decisión
  para destacar tickers con persistencia temporal (`racha >= 2`, excluye Liquidez)

### Changed

- `server.py`: cuando una corrida se cancela, el estado final queda en `interrupted`
  y se limpia la referencia del proceso al finalizar el watcher
- `README.md`, `docs/ayuda-usuario.txt` y `docs/product-roadmap.md` actualizados con el nuevo flujo de cancelacion
- `tests/test_server.py`: nuevas pruebas para recuperacion de huérfanos y limpieza de PID file de corrida
- `tests/test_server.py`: nueva cobertura de redaccion de secretos en `/status/detail`
- `src/clients/iol.py`: requests criticos ahora usan retry con backoff para timeouts,
  errores de conexion y HTTP transitorios (408/429/5xx)
- `src/clients/bcra.py`: `_fetch_text`, `_fetch_bytes` y `_fetch_json` ahora usan retry
  con backoff para timeouts, errores de conexion y HTTP transitorios (408/429/5xx)
- `tests/test_iol_client.py` y `tests/test_bcra_client.py`: cobertura de retry en
  escenarios de timeout transitorio
- cobertura ampliada en `tests/test_sizing.py` y `tests/test_bcra_client.py` para
  ramas de edge-cases, fallbacks y comentarios operativos
- `README.md`, `docs/baseline-actual.md`, `docs/improvement-roadmap.md` y `docs/product-roadmap.md`
  actualizados para reflejar operacion Bash cross-platform
- `static/index.html`: reemplazo de `window.confirm()` por modal custom HTML/CSS/JS
  para confirmar corrida con datos de usuario/fondeo antes de `POST /run`
- `static/index.html`: nueva seccion `Reportes anteriores` que consume `/reports/list`
  y permite abrir reportes historicos directamente desde la UI
- utilidades comunes centralizadas:
  - `src/common/text.py` agrega `normalize_text_basic` y `normalize_text_folded`
  - `src/common/numeric.py` agrega `safe_float`
  - `src/clients/bcra.py`, `src/clients/bonistas_client.py` y `src/prediction/predictor.py`
    pasan a reutilizar utilidades compartidas en lugar de implementaciones duplicadas
- `.github/workflows/ci.yml`: agrega `tests.test_text_utils` a la suite estable
- `static/index.html`: obtiene token via `GET /session` y lo envia en `POST /run`
- `tests/test_server.py`: cobertura de `GET /session` y rechazo `401` de `/run` con token invalido
- `server.py`: `/status/detail` ahora devuelve `log_tail` ampliado y campo `log_lines`
  para mejorar observabilidad operativa
- `server.py`: manejo explicito de error al iniciar subprocess en `/run`
  con respuesta HTTP 500 y mensaje claro
- `server.py`: `/status/detail` agrega `elapsed_seconds` (duracion total desde
  `started_at` hasta `finished_at` o `now`)
- `scripts/generate_real_report.py`: logging de duracion por fase principal
  (`Backup runtime`, `Credenciales`, `Datos de mercado`, `Analisis y decision`,
  `Render y persistencia`) con formato `Fase <nombre>: <seg>s`
- `scripts/generate_real_report.py`: `configure_logging()` ahora selecciona
  formato texto o JSON segun `LOG_FORMAT`
- `static/index.html`: mejoras de accesibilidad en UI local:
  - panel de estado con `aria-live="polite"`
  - icono de estado con `aria-label` descriptivo
  - mensajes de error de formulario/corrida en contenedor con `role="alert"`
- `static/index.html`: mejoras UX adicionales:
  - tooltip explicativo en `Aporte externo ARS`
  - link `Ver log completo` visible cuando estado es `error` (abre `/status/detail`)
- `server.py`: `POST /run` ahora rechaza `username/password` vacios con `422`
  antes de lanzar subprocess (defensa en profundidad)
- `server.py`: `POST /run` incorpora rate limiting basico
  (maximo 3 requests por minuto, respuesta `429` al exceder)
- `server.py`: nuevo endpoint `GET /api-health` para chequear conectividad
  resumida de APIs externas (IOL, ArgentinaDatos, BCRA, Bonistas, FRED, Finviz)
  - usa endpoints canonicos por proveedor
  - valida codigos esperados por API
  - reporta `latency_ms` por chequeo
- `.github/workflows/ci.yml`: se intento matriz de OS con `macos-latest`,
  pero se revierte temporalmente a `ubuntu-latest` y queda como deuda tecnica
  pendiente por inestabilidad en GitHub Actions
- `.github/workflows/ci.yml`: se desactiva temporalmente tambien `ubuntu-latest`
  para unittest en Actions; se agrega job de aviso no bloqueante mientras se
  resuelve la deuda tecnica de CI
- `server.py`: asegura creacion de `reports/` antes de `app.mount("/reports", ...)`
- `tests/test_report_render_ui.py`: assertion robusta para variante UTF-8/mojibake
  en marcador visual de `Refuerzo` (`⚠`/`âš `) sin alterar comportamiento funcional
- `scripts/generate_real_report_runtime.py`: hardening del flujo de operaciones IOL
  para tolerar payloads no homogéneos (lista con ruido, o wrapper dict con
  `operaciones`) y evitar `AttributeError` en extracción de tickers
- `tests/test_generate_real_report_split_runtime.py`: cobertura adicional para
  filas no-dict y normalización de wrapper `operaciones`
- fix de regresion en render de riesgo historico:
  - `scripts/report_sections.py` corrige firma de `fmt_score` en fila de benchmark
  - evita `TypeError: fmt_score() got an unexpected keyword argument 'digits'`
  para evitar fallo de import en CI cuando el directorio no existe
- retencion automatica de `prediction_history.csv`:
  - nueva funcion `apply_prediction_history_retention()` en `src/prediction/store.py`
  - retencion default de 90 dias (configurable)
  - aplicada en `scripts/generate_real_report.py` y `scripts/run_prediction_cycle.py`
- cache intradia de precios IOL (TTL 15 minutos):
  - `scripts/generate_real_report_runtime.py` agrega cache en archivo JSON
  - `scripts/generate_real_report.py` integra cache en `fetch_prices`
  - path de cache: `data/runtime/iol_price_cache.json`
- `docs/README.md`: nuevo diagrama de arquitectura en Mermaid
- `scripts/release.ps1`: automatiza release local
  - bump de version en `pyproject.toml`
  - creacion/actualizacion de `version.txt`
  - creacion de tag `vX.Y.Z`
  - ejecucion de `scripts/build_dist.ps1`
- webhook opcional al finalizar corrida en `server.py`:
  - variable `RUN_COMPLETION_WEBHOOK_URL`
  - emite `POST` con resumen de estado final (`done/error/interrupted`)
- validacion de integridad de CSV runtime al startup en `server.py`:
  - chequeo de schema/header para `decision_history.csv` y `prediction_history.csv`
  - cuarentena automatica de archivos invalidos en `data/runtime/corrupt/*.corrupt`
- scheduler opcional de corridas reales en `scripts/generate_real_report.py`:
  - nuevo flag `--schedule-every-minutes N` (requiere `--non-interactive`)
  - ejecuta corridas periodicas y espera `N` minutos entre ejecuciones
- `/api-health` incorpora circuit breaker simple por proveedor:
  - apertura tras fallas consecutivas
  - cooldown antes de reintentar
  - nuevos campos en respuesta: `circuit_open`, `failure_count`
- retencion configurable de `decision_history.csv`:
  - nueva funcion `apply_decision_history_retention()` en `src/decision/history.py`
  - default de 365 dias (`DECISION_HISTORY_RETENTION_DAYS`)
  - aplicada en `scripts/generate_real_report.py`
- accesibilidad de tablas del reporte:
  - encabezados `th` ahora incluyen `scope=\"col\"` en tablas renderizadas
  - aplicado en decision table, prediction signal table y primitivas de tablas
- refactor incremental en `src/decision/scoring.py`:
  - `apply_base_scores` extrae inicializacion de defaults/sub-scores a
    helper `_initialize_base_scores`
  - sin cambios funcionales en reglas de scoring
- refactor incremental adicional en `src/decision/scoring.py`:
  - `apply_base_scores` extrae en helpers privados la logica de:
    - blend absoluto por metricas (`_apply_absolute_metric_blends`)
    - concentracion y momentum (`_apply_concentration_and_momentum_scores`)
    - composicion de score de refuerzo (`_apply_refuerzo_score`)
    - composicion de score de reduccion (`_apply_reduccion_score`)
  - sin cambios funcionales en reglas de scoring
- `src/decision/sizing.py`: extraccion de comentarios operativos a modulo dedicado
  `src/decision/operational_comments.py`
  - mantiene compatibilidad con imports existentes mediante wrapper
    `_comentario_operativo` en `sizing.py`
  - mantiene helper `_join_with_y` en `sizing.py` como compatibilidad para tests/consumidores internos
- contratos tipados para clientes externos:
  - nuevo modulo `src/clients/protocols.py` con `HttpResponseProtocol`,
    `HttpGetProtocol` y `HttpRequestProtocol`
  - `src/clients/iol.py` y `src/clients/bcra.py` adoptan estos contratos
    en helpers de retry sin cambios funcionales
- refactor incremental adicional en `src/decision/scoring.py`:
  - `apply_base_scores` extrae ajustes efectivos de ETF/calidad a helper
    `_apply_etf_effective_scores`
  - sin cambios funcionales en reglas de scoring
- `server.py` migra la inicializacion de app a `lifespan` de FastAPI
  (reemplaza uso de `@app.on_event("startup")` deprecado)
  - se conserva `on_startup()` como helper interno para compatibilidad
    con pruebas unitarias
- `server.py`: mejora de mensaje de error operativo en corridas fallidas
  - cuando IOL responde `401 Unauthorized` en `/token`, `status/error`
    ahora devuelve mensaje amigable de credenciales invalidas
  - el traceback tecnico completo se conserva en `log_tail` de `/status/detail`
- `.github/workflows/ci.yml`: job `unittest` ahora fuerza Node 24 para
  acciones JavaScript (`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`) para evitar
  la deprecacion operativa de Node 20 en runners de GitHub Actions
- `static/index.html`: mejora UX/accesibilidad en panel de estado
  - agrega badge textual con color por estado (`Inactivo`, `En ejecucion`,
    `Completado`, `Interrumpido`, `Error`)
  - mantiene iconografia, `aria-label` y semantica existente de estados
- refactor incremental adicional en `src/decision/scoring.py`:
  - `apply_base_scores` extrae el calculo de `score_despliegue_liquidez`
    a helper `_apply_liquidity_deployment_score`
  - sin cambios funcionales en reglas de scoring
- refactor incremental adicional en `src/decision/scoring.py`:
  - `apply_base_scores` extrae el post-procesado final a helper
    `_apply_post_regime_adjustments` (regimen, clamp de reduccion y liquidez)
  - sin cambios funcionales en reglas de scoring
- refactor incremental adicional en `src/decision/scoring.py`:
  - `apply_base_scores` extrae parseo de configuracion/umbrales a helper
    `_parse_base_score_config`
  - sin cambios funcionales en reglas de scoring
- hardening de sesion en `server.py` y UI:
  - `POST /cancel` ahora exige header `X-Session-Token`
  - `static/index.html` envia token de sesion tambien al cancelar corrida
  - `tests/test_server.py` agrega cobertura de rechazo `401` en `/cancel`
- `src/decision/scoring.py`: mejora de tipado interno de configuracion base
  - nuevo `TypedDict` `BaseScoreConfig` para el retorno de `_parse_base_score_config`
  - reduce uso ambiguo de `dict[str, object]` en `apply_base_scores`
  - sin cambios funcionales en reglas de scoring
- documentacion de compatibilidad de navegadores:
  - nuevo `docs/browser-support.md` con matriz oficial desktop/mobile
  - `README.md` y `docs/README.md` referencian el documento de soporte
- `docs/product-roadmap.md`: roadmap ampliado de 18 a 19 dimensiones con nueva
  dimension de validacion estadistica y madurez de senales (P1/P2/P3).
- `src/prediction/maturity.py`: umbrales minimos compartidos para madurez:
  - `MIN_RUNS_FOR_STREAK=10`
  - `MIN_RUNS_FOR_RELIABLE_SERIES=20`
  - `MIN_OUTCOMES_PER_FAMILY_FOR_CALIBRATION=30`
- fallback legacy de snapshots endurecido:
  - `scripts/generate_real_report.py` agrega `should_use_legacy_snapshots()`
  - si `data/snapshots/` alcanza >=20 snapshots de portfolio master, se
    desactiva automaticamente el fallback a `tests/snapshots/`
- `src/analytics/portfolio_risk.py` alinea `serie_agregada_confiable` con
  umbral minimo de 20 pasos estables para habilitar metricas agregadas
- calidad de historia en decision table:
  - `src/decision/history.py` agrega `quality_label` y `historial_observaciones`
    en enriquecimiento temporal por ticker/subfamilia
  - `scripts/report_decision.py` muestra columna `Calidad historia` con labels:
    `Robusta`, `Parcial`, `Corta`, `Sin historia`
- `tests/test_report_render_core.py`: asserts de texto robustecidos para tolerar
  variantes UTF-8/mojibake heredadas en algunos labels del HTML
- metricas historicas de acierto del predictor en reporte:
  - `src/prediction/store.py` persiste tambien `asset_family` y `asset_subfamily`
    en `prediction_history.csv`
  - `scripts/generate_real_report.py` calcula `accuracy` global y por familia
    desde outcomes verificados del historial
  - `scripts/report_sections_prediction.py` renderiza bloques:
    - `Acierto histórico (global)`
    - `Acierto por familia`

### Testing

- cobertura de modulos clave de P1 validada con suites dirigidas:
  - `src/clients/bcra.py`: 82%
  - `src/decision/sizing.py`: 86%
- tests de backup runtime agregados:
  - `tests/test_generate_real_report_split_runtime.py`
  - `tests/test_generate_real_report.py`
- nuevos tests de utilidades:
  - `tests/test_text_utils.py`
  - ampliacion de `tests/test_numeric_utils.py`
- `tests/test_server.py`: nuevos casos para validar:
  - rechazo `422` con `aporte_externo_ars` negativo
  - rechazo `422` con `username/password` de mas de 200 caracteres
  - respuesta `500` si falla `subprocess.Popen` al lanzar corrida
  - `elapsed_seconds` en `/status/detail` para corridas `running` y `done`
- `tests/test_generate_real_report.py`: nuevo test de `_log_phase_duration`
  para validar emision de log de duracion por fase
- `tests/test_generate_real_report.py`: nuevos tests de `configure_logging()`
  para modo texto default, modo JSON y escenario no-op con handlers existentes
- `tests/test_server.py`: nuevos tests para rechazo `422` cuando `username` o
  `password` llegan vacios/blancos en `POST /run`
- `tests/test_server.py`: cobertura de `GET /runs/recent`
- `tests/test_server.py`: nuevo test de rate limit en `/run` (`429`)
- `tests/test_server.py`: nuevos tests para `/api-health` (caso OK y fallo parcial)
- `tests/test_prediction_store.py`: cobertura de retencion por antiguedad y validacion de `retention_days`
- `tests/test_prediction_cycle.py`: cobertura de aplicacion de retencion dentro del ciclo
- `tests/test_generate_real_report_split_runtime.py`: nuevos tests de cache intradia
  (hit con cache fresca y refetch con cache vencida)
- `tests/test_server.py`: nuevo test concurrente de `/run`
  (`test_concurrent_run_requests_second_returns_409`) para validar que requests
  simultaneos no disparan dos corridas y el segundo recibe `409`
- `tests/test_server.py`: nuevos tests de webhook de finalizacion
  (`test_watch_process_sends_completion_webhook_when_configured` y
  `test_watch_process_ignores_webhook_errors`)
- `tests/test_server.py`: nuevos tests de validacion de CSV runtime
  (`TestRuntimeCsvValidation`)
- `tests/test_generate_real_report.py`: nuevos tests de scheduler
  (`schedule-every-minutes`, requerimiento de `--non-interactive`, loop/sleep)
- `tests/test_server.py`: nuevos tests de circuit breaker en `/api-health`
  (apertura por fallas consecutivas y retry despues de cooldown)
- `tests/test_decision_history.py`: nuevos tests de retencion de decision history
- `tests/test_generate_real_report.py`: nuevo test de aplicacion de retencion en flujo real
- `tests/test_report_primitives.py` y `tests/test_report_sections_prediction.py`:
  cobertura de headers con `scope=\"col\"`
- validacion de no-regresion del refactor de scoring:
  - `python -m unittest tests.test_decision_scoring -v`
  - `python -m unittest tests.strategy_rules_technical_scoring -v`
- validacion del refactor de comentarios operativos:
  - `python -m unittest tests.test_sizing -v`
  - `python -m unittest tests.test_pipeline -v`
- validacion de contratos tipados en clientes:
  - `python -m unittest tests.test_iol_client -v`
  - `python -m unittest tests.test_bcra_client -v`
- validacion de umbrales de madurez y fallback legacy:
  - `python -m unittest tests.test_portfolio_risk -v`
  - `python -m unittest tests.test_generate_real_report -v`
- validacion de quality label en decision table:
  - `python -m unittest tests.test_decision_history -v`
  - `python -m unittest tests.test_report_render_core -v`
- validacion de metricas de acierto en prediccion:
  - `python -m unittest tests.test_prediction_store -v`
  - `python -m unittest tests.test_generate_real_report -v`
  - `python -m unittest tests.test_report_sections_prediction -v`

### Security

- `server.py`: `/status/detail` ahora sanitiza `log_tail` y `error` para ocultar
  secretos si aparecen en logs (`IOL_USERNAME`, `IOL_PASSWORD`, `username`, `password`)

### Fixed

- `static/index.html`: iconos de estado en UI normalizados con secuencias Unicode escapadas
  para evitar mojibake por problemas de encoding (ejemplo: `Corrida cancelada`)

## [0.2.2] - 2026-04-27

### Added

- `docs/ayuda-usuario.txt`: guia de uso para usuarios finales con descripcion
  de cada seccion del reporte, preguntas frecuentes y contacto de soporte
- `AYUDA.txt` incluido en el zip generado por `build_dist.ps1`

## [0.2.1] - 2026-04-27

### Added

- seccion "¿Que hace esta app?" colapsable en `static/index.html`: explica el proposito,
  como usar el formulario y que credenciales se necesitan — visible para usuarios finales
  al abrir la app por primera vez

## [0.2.0] - 2026-04-26

### Added

- `scripts/build_dist.ps1`: genera `dist/cartera-vX.Y.Z-win64.zip` con Python 3.12
  embeddable, dependencias pre-instaladas y bat files de inicio/detencion
  - `Iniciar Cartera.bat`: doble clic, crea directorios, carga `.env`, abre browser
  - `Detener Cartera.bat`: detiene el proceso por PID
  - `LEEME.txt`: instrucciones para usuarios finales sin conocimiento tecnico
  - estrategia de updates: `data/runtime/`, `reports/` y `data/strategy/` no se incluyen
    en el zip y sobreviven al extraer con "reemplazar todo"
- `GET /version`: expone la version activa (lee `version.txt`; fallback a `pyproject.toml`
  con sufijo `-dev` en entorno de desarrollo)
- footer de version en `static/index.html` con mensaje de contacto para updates
- `scripts/setup_local_app.ps1`: bootstrap rapido de entorno local para developers/testers
- `docs/tester-guide.md`: guia de uso para testers con credenciales IOL

### Fixed

- `styles.css` movido de `reports/` a `static/` (lugar correcto para assets de la app)
- HTML del reporte generado ahora es autocontenido: CSS inlineado en `<style>` en lugar
  de `<link href="styles.css">` — funciona offline, por mail y sin dependencias externas

## [0.1.0] - 2026-04-26

### Added

- app local FastAPI (`server.py`) con frontend en `static/index.html`
- endpoints `/health`, `/status`, `/status/detail` y servido de reportes por `/reports/*`
- scripts operativos locales (`run_local_app.ps1`, `start_local_app.ps1`, `status_local_app.ps1`, `stop_local_app.ps1`, `smoke_local_app.ps1`)
- test suite de servidor (`tests/test_server.py`)

### Changed

- modularizacion del runner real y del renderer en scripts especializados
- split de `tests/test_strategy_rules.py` por dominio, manteniendo `tests.test_strategy_rules` como entrypoint de suite

### Security

- credenciales IOL en app local:
  - no se guardan en `_state`
  - no se pasan por argv al subprocess
  - se inyectan por variables de entorno del proceso hijo
