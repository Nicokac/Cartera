# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y versionado [SemVer](https://semver.org/lang/es/).

## [Unreleased]

### Added

- `docs/report-ui-embellecimiento-plan.md`: plan post v0.5 para embellecimiento del reporte con:
  - auditoria estructural (layout/componentes/modulos)
  - arquitectura objetivo single-page modular
  - prioridades visuales y fases de implementacion
  - checklist de pruebas por tipo de cambio (solo si aplica)

### Changed

- `docs/product-roadmap.md`: agregado bloque de continuidad post-cierre para abrir la linea de trabajo UI/embellecimiento usando el nuevo plan.
- `docs/product-roadmap.md` y `docs/report-ui-embellecimiento-plan.md`: alineadas a baseline de version `0.5.3`.
- versionado normalizado a `0.5.3` en artefactos de release:
  - `pyproject.toml` (`project.version`)
  - `README.md` (version vigente, nombre de ZIP y ejemplos de `release.ps1`)
- inicio de refactorizacion de `real-report` (Fase UI-1):
  - nuevo `static/report-ui.js` con la logica de interaccion del reporte
  - `scripts/report_layout.py` deja de mantener JS embebido extenso y pasa a inyectar el contenido desde el archivo dedicado
  - comportamiento funcional preservado (quick-nav, filtros/sort, copy sizing, toggle columnas, persistencia de `details`)
- embellecimiento base de `real-report` (Fase UI-1):
  - mejora visual de `quick-nav`, cards primarias y encabezados de panel
  - mejoras de accesibilidad visual (`:focus-visible`) y microinteracciones en controles
  - headers de tabla sticky para lectura de tablas extensas
  - correccion de mojibake en icono de colapsables CSS (`\25B8`)
- refactor tecnico (sin cambios funcionales/visuales) del renderer de reporte:
  - nuevo `scripts/report_assets.py` para centralizar carga de assets (`styles.css`, `report-ui.js`)
  - `scripts/report_layout.py` ahora usa `load_report_css()` y `load_report_js()`
  - carga de assets cacheada con `lru_cache` para reducir I/O repetido en renders sucesivos
- refactor tecnico de composicion del documento HTML del reporte:
  - nuevo `scripts/report_document.py` como builder del shell HTML (`doctype/head/body/assets`)
  - `scripts/report_layout.py` conserva composicion de contenido y delega documento global al nuevo modulo
  - sin cambios de comportamiento en salida renderizada

## [0.5.3] - 2026-05-01

### Added

- `data/mappings/block_map.json`: entradas `TTWO` → "Growth" y `S31G6` → "CER" para que los nuevos activos reciban bloque correcto en scoring
- `data/mappings/finviz_map.json`: entrada `TTWO` → "TTWO" para cobertura Finviz del stock NASDAQ
- `data/mappings/instrument_profile_map.json`: entrada `TTWO` (Stock / stock_growth) para consistencia con el catalogo de instrumentos
- `data/mappings/vn_factor_map.json`: entrada `S31G6` → 100 (explicita; antes usaba el default silencioso)

### Fixed

- `src/decision/scoring.py`: acciones de mercado estadounidense (`Tipo == "Accion US"`) ya reciben `asset_family = "stock"` via nuevo flag `Es_Accion_US`; antes quedaban sin familia y el motor de scoring las trataba como instrumentos desconocidos
- `src/decision/scoring.py`: `Ticker_Finviz` de instrumentos no-CEDEAR (acciones US) ya se propaga al decision frame rellenando desde `df_total` tras el merge; `Cobertura_Modelo` pasa de "Parcial" a "Completa" para TTWO una vez que tenga datos Finviz
- `src/decision/scoring.py`: `Es_Accion_US` agregado a `bool_defaults` en `apply_base_scores` como fallback defensivo
- `src/analytics/technical.py`: `build_technical_overlay` acepta `df_extra` opcional para incluir acciones US (TTWO) en el overlay tecnico via Yahoo Finance; antes solo procesaba CEDEARs
- `scripts/generate_real_report.py`: pasa `df_us` como `df_extra` a `build_technical_overlay`; actualiza `_print_coverage_stats` para incluir US stocks con Finviz ticker en el denominador de cobertura tecnica
- `scripts/report_composer.py`: `tech_total` suma CEDEARs + acciones US con `Ticker_Finviz` para que el KPI "Cobertura tecnica" sea correcto

## [0.5.2] - 2026-05-01

### Fixed

- `src/portfolio/classify.py`: instrumentos de tipo `Letras` y `LetraNota` (ej. S31G6) ya son reconocidos y enrutados al bucket de bonos; antes caian silenciosamente fuera del clasificador y quedaban marcados como "pendiente de consolidacion" con cantidad incorrecta derivada del historial de operaciones
- `scripts/generate_real_report_runtime.py`: el portafolio de la cuenta `estados_Unidos` ya se incorpora a la cartera consolidada via `_fetch_merged_portfolio`; antes se ignoraba completamente el endpoint `/portafolio/estados_Unidos`, dejando posiciones como TTWO invisibles en reporte, scoring y riesgo
- `scripts/generate_real_report_runtime.py`: `extract_quote_tickers_impl` incluye `Letras` y `LetraNota` en el conjunto de tipos cotizables para snapshot de precios
- `src/portfolio/classify.py`: acciones de mercado estadounidense (tipo `ACCIONES`, pais `estados_Unidos`) clasificadas en bucket propio `ACCIONES_US` con precio, ppc, valorizado y ganancia en USD; ya no se confunden con CEDEARs ni acciones locales
- `src/portfolio/valuation.py`: nueva funcion `build_us_df` que convierte valores USD a ARS via MEP, expone `Valor_USD` directo desde el API y asigna `Tipo = "Accion US"`; elimina las 3 alertas de integridad que generaba TTWO al carecer de precio ARS
- `src/pipeline.py`: `build_portfolio_bundle` construye `df_us` y lo pasa a `build_portfolio_master`; este acepta `df_us` como parametro opcional backward-compatible

## [0.5.1] - 2026-05-01

### Changed

- documentacion de release alineada con la version publicada `0.5.1`:
  - `README.md`, `docs/README.md`, `docs/baseline-actual.md` y `docs/product-roadmap.md`
  - ejemplos de `scripts/release.ps1` actualizados para reflejar la release vigente
- hardening post-release del renderer HTML:
  - correccion de mojibake residual en titulos, labels, leyendas y simbolos del reporte
  - `Real Run` deja de publicar `Smoke Report` en el titulo de la pestana
  - `quality_label` se alinea con los umbrales visibles al usuario sin perder `Sin historia` en primera observacion
  - la advertencia de contradiccion en prediccion vuelve a renderizarse como icono de warning real en la tabla final
  - tests de render dejan de aceptar variantes mojibake como salida valida

### Fixed

- la corrida CLI vuelve a imprimir `Cobertura tecnica` sin mojibake
- validacion end-to-end confirmada sobre `reports/real-report.html` generado en corrida real

## [0.5.0] - 2026-05-01

### Added

- cobertura estructural para wrappers PowerShell:
  - nuevo `tests/test_powershell_scripts.py`
  - verificacion de helper comun, resolucion cross-platform de Python y uso de sesion en scripts protegidos
- cobertura estructural de responsive del reporte:
  - `tests/test_report_render_ui.py` valida `meta viewport`, breakpoints CSS, `table-wrap` con scroll horizontal local y hooks de navegacion/columnas adaptativas
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
- `docs/report-mobile-responsive-checklist.md`: checklist formal para validar
  legibilidad y usabilidad del reporte HTML en mobile/tablet
- configuracion basica de scoring desde UI local:
  - `GET /config/{config_name}` devuelve contenido actual (`scoring`, `action`, `sizing`)
  - `POST /config/{config_name}` valida JSON y persiste contenido formateado
  - nueva seccion `Configuracion de reglas (avanzado)` en `static/index.html`
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

- preparacion de release:
  - `pyproject.toml` y `version.txt` pasan a `0.5.1`
  - documentacion operativa de release actualiza ejemplos a la nueva version
  - `docs/product-roadmap.md` queda saneado como registro de cierre, con resumen ejecutivo de `v0.3`, `v0.4` y `v0.5`
  - `README.md` corrige referencia del ZIP distribuible a `cartera-v0.5.1-win64.zip`
  - `docs/product-roadmap.md` aclara como historicos los estados transicionales de CI ya resueltos
- wrappers PowerShell locales:
  - nuevo helper compartido `scripts/common_local_app.ps1`
  - `setup/start/status/smoke/run/stop` reutilizan rutas con `Join-Path`
  - `setup/start` resuelven `.venv/Scripts/python.exe` o `.venv/bin/python` segun plataforma
  - `status -Detailed` y `smoke` obtienen token via `GET /session` para consultar `/status` y `/status/detail`
  - `start/run` usan apertura de browser portable (`Start-Process` / `open` / `xdg-open`)
- `README.md`, `docs/baseline-actual.md` y `docs/product-roadmap.md` actualizados para reflejar cierre de la Fase 2 `pwsh` cross-platform
- `src/decision/sizing.py`: `build_operational_proposal` se descompone en helpers privados para:
  - aplicacion de acciones operativas
  - armado de comentarios
  - seleccion de rankings/top/descartados
  - calculo de resumen de fondeo
  - asignacion de fondeo sugerido a refuerzos
- `docs/product-roadmap.md` actualiza el cierre formal del pendiente `P2` de refactor de funciones largas
- `docs/accessibility-contrast-audit.md` amplía la evidencia de auditoria WCAG AA para `static/index.html` y `docs/product-roadmap.md` marca el item de contraste como completado
- `docs/report-mobile-responsive-checklist.md` registra cierre estructural automatizado del reporte y `docs/product-roadmap.md` marca el item mobile/responsive como completado
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
- `.github/workflows/ci.yml`: eleva el piso de cobertura de `82%` a `85%`
  en `coverage report --fail-under`
- `docs/product-roadmap.md`: se marca como completado el ítem de Dimensión 18
  sobre configuración básica en UI, reflejando el alcance real ya implementado
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
- `README.md` y `docs/README.md` ahora referencian tambien
  `docs/report-mobile-responsive-checklist.md` para ejecucion operativa de
  pruebas responsive del reporte
- `docs/product-roadmap.md`: normalizacion de estado de avance para reflejar
  items ya cerrados/avanzados (UI reportes, scheduler, cache intradia, tests de
  concurrencia, webhook, integridad runtime, docker dev/test, etc.)
- limpieza documental de estado CI:
  - `README.md` ya no marca unittest en GitHub Actions como deshabilitado
  - se alinea el texto con el workflow activo (`ubuntu-latest` + `macos-latest`)
- `src/decision/scoring.py`: ajuste de tipado en `apply_base_scores`
  - usa directamente `BaseScoreConfig` parseado (sin casts redundantes)
  - sin cambios funcionales en reglas de scoring
- hardening de observabilidad en `server.py` + UI:
  - `GET /status/detail` ahora requiere token de sesion
    (`X-Session-Token` o query `token`)
  - `static/index.html` actualiza el link `Ver log completo` con token de sesion
  - `tests/test_server.py` agrega cobertura de `401` sin token y `200` con query token
- hardening adicional de endpoints de historial/listado:
  - `GET /reports/list` y `GET /runs/recent` ahora requieren `X-Session-Token`
  - `static/index.html` envia token en fetch de ambas secciones
  - `tests/test_server.py` agrega cobertura de `401` sin token en ambos endpoints
- hardening adicional de endpoint de estado:
  - `GET /status` ahora requiere `X-Session-Token`
  - `static/index.html` envia token en polling y carga inicial de estado
  - `tests/test_server.py` agrega cobertura de `401` sin token en `/status`
- hardening adicional de endpoint de diagnostico de integraciones:
  - `GET /api-health` ahora requiere `X-Session-Token`
  - `tests/test_server.py` agrega cobertura de `401` sin token en `/api-health`
  - `README.md` aclara requerimiento de token para este endpoint
- `server.py`: refactor de mantenibilidad en autenticacion de sesion
  - nuevo helper `_require_session_token(...)` para validacion centralizada
  - reemplaza chequeos duplicados en todos los endpoints protegidos
  - sin cambios funcionales en contratos de API
- `src/decision/scoring.py`: refactor incremental de mantenibilidad
  - `_compute_base_scores_from_config` reduce ruido de variables intermedias
    y usa `BaseScoreConfig` directamente en el pipeline interno de scoring
  - sin cambios funcionales de resultado
  - `_apply_absolute_metric_blends` reduce repeticion de acceso a reglas
    por metrica con helper local `_metric_rules` (sin cambios funcionales)
  - `_apply_refuerzo_score` reduce repeticion en lectura de ajustes por
    subfamilia con helper local `_rule_value` (sin cambios funcionales)
  - `_apply_reduccion_score` reduce repeticion en lectura de ajustes por
    subfamilia con helper local `_rule_value` (sin cambios funcionales)
  - `_apply_etf_effective_scores` reduce repeticion de lectura de ajustes ETF
    con helper local `_adj` (sin cambios funcionales)
  - `_apply_concentration_and_momentum_scores` unifica formulas de
    concentracion con helper `_piecewise_linear_score` (sin cambios funcionales)
  - `_apply_concentration_and_momentum_scores` extrae helper
    `_weighted_momentum` para consolidar calculo ponderado de momentum
    (sin cambios funcionales)
  - `_apply_refuerzo_score` y `_apply_reduccion_score` consolidan lectura de
    pesos en helper local `_weight` para reducir repeticion
    (sin cambios funcionales)
- accesibilidad UI (contraste):
  - `static/index.html` mejora contraste en textos secundarios y estados disabled
    (`#status-time`, `footer`, `button:disabled`, `#btn-cancel:disabled`)
  - nuevo reporte `docs/accessibility-contrast-audit.md` con alcance y verificacion recomendada
- refactor incremental de mantenibilidad en `src/decision/scoring.py`:
  - `apply_base_scores` delega su secuencia principal en
    `_compute_base_scores_from_config`
  - sin cambios funcionales en scoring; mejora legibilidad y desacople interno
- `static/index.html`: refactor de mantenibilidad en llamadas autenticadas
  - nuevo helper `fetchWithSession(...)` para inyectar `X-Session-Token`
  - elimina duplicacion de headers en `run/cancel/status/reports/runs`
  - sin cambios funcionales en flujo de UI
- testing cross-platform (scripts Bash):
  - nuevo `tests/test_bash_scripts.py` con smoke estructural de scripts `*.sh`
    (existencia, shebang bash, `set -euo pipefail`)
  - control de permisos POSIX marcado como `skip` en Windows por portabilidad
  - `.github/workflows/ci.yml` incluye `tests.test_bash_scripts` en suite estable
- `tests/test_decision_scoring.py`: nueva cobertura de contrato de configuracion
  - tests para `_parse_base_score_config` (defaults y overrides)
  - reduce riesgo de regresiones silenciosas en parseo de `scoring_rules`
- `tests/test_server.py`: nueva cobertura unitaria para auth helper
  `_require_session_token(...)`
  - casos: token valido, token invalido y sesion no inicializada
  - refuerza contrato de seguridad del refactor de endpoints protegidos
- `tests/test_server.py`: nueva cobertura de `GET/POST /config/scoring`
  - `401` sin token
  - validacion de JSON invalido (`422`)
  - persistencia correcta de JSON formateado
  - `404` para config name no soportado
  - persistencia en archivo objetivo (`action_rules.json`)
- `docs/product-roadmap.md`: normalizacion de estado de roadmap
  - marcado explicito de items ya implementados como `(completado)`
  - limpieza de hallazgos desactualizados en Seguridad y Compatibilidad
  - deja visible la deuda real pendiente para cierre del roadmap
- contratos tipados para clientes externos:
  - `src/clients/protocols.py` agrega `FredSeriesClientProtocol` y `PyOBDClientProtocol`
  - `src/clients/fred_client.py` y `src/clients/pyobd_client.py` aceptan clientes inyectados y tipados
  - `tests/test_fred_client.py` y `tests/test_pyobd_client.py` cubren la nueva inyeccion directa
- auditoria de credenciales:
  - `tests/test_generate_real_report_split_cli.py` verifica que la resolucion CLI de credenciales no imprima valores sensibles
  - se consolida cierre de roadmap para auditoria de secretos y filtrado de `log_tail`
- `docs/product-roadmap.md`: cierre formal del refactor incremental de `apply_base_scores`
  y de la adopcion de `typing.Protocol` en clientes externos
- precision monetaria en valuacion:
  - `src/portfolio/valuation.py` migra calculos criticos de `Valorizado_ARS`,
    `Ganancia_ARS` y `Valor_USD` a aritmetica interna con `Decimal`
  - se mantiene salida `float` en DataFrames para compatibilidad con el pipeline actual
  - `tests/test_valuation_and_checks.py` agrega cobertura especifica para precision monetaria
- tipado temporal compartido:
  - nuevo alias `DateLike` en `src/common/types.py`
  - reemplaza `object` generico en firmas de `pipeline`, `prediction.store`,
    `prediction.verifier` y `decision.history`
  - tests temporales/pipeline validan que el cambio no altera comportamiento
- tipado de contratos de dominio:
  - `src/portfolio/operations.py` agrega `TypedDict` para bundles de
    transiciones, highlights y operaciones
  - `src/decision/sizing.py` agrega `SizingBundle` para el contrato de salida
  - tests de `operations`, `sizing` y `pipeline` validan compatibilidad
- tipado de reglas y contexto:
  - `src/decision/actions.py`, `src/decision/market_regime_scoring.py`,
    `src/decision/sizing.py` y `src/analytics/bond_analytics.py` reemplazan
    varios `dict[str, object]` por `Mapping[str, Any]` y `TypedDict`
  - tests de decision/scoring/sizing/bond analytics validan que no cambia el comportamiento
- tipado en analytics:
  - `src/analytics/portfolio_risk.py` agrega `TypedDict` para puntos comparables,
    filas de riesgo y bundle de salida
  - `src/analytics/technical.py` agrega `TechnicalOverlayRow` y tipa configuracion/salida
  - tests de `portfolio_risk`, `technical` y `pipeline` validan compatibilidad
- cierre de tipado generico:
  - `src/decision/scoring.py` reemplaza contratos `dict[str, object]` por `Mapping[str, Any]`
  - `src/clients/bcra.py`, `src/clients/pyobd_client.py` y `src/portfolio/operations.py`
    eliminan remanentes puntuales de contratos genericos
  - se completa el item del roadmap sobre type hints genericos remanentes
- observabilidad de integraciones:
  - `GET /api-health` agrega campo `checked_at` por proveedor
  - facilita trazabilidad temporal de disponibilidad/latencia por chequeo
- configuracion avanzada por API:
  - nuevo `GET /config` para listar configuraciones editables permitidas
  - permite discovery seguro de la allowlist (`scoring`, `action`, `sizing`)
  - `static/index.html` ahora consume `GET /config` para poblar dinamicamente
    el selector de archivos editables (evita opciones hardcodeadas desactualizadas)
  - `GET /config` ahora incluye metadata por archivo (`filename`, `exists`,
    `modified_at`) para mejorar diagnostico operativo
  - la UI de configuracion avanzada muestra la metadata del archivo seleccionado
    (`filename`, `exists`, `modified_at`) en pantalla
  - el editor avanzado incorpora `dirty state` y validacion JSON en vivo:
    `Guardar` se habilita solo cuando hay cambios pendientes y el JSON es valido
  - nuevo boton `Formatear JSON` en el editor avanzado para pretty-print local
    antes de guardar
  - nuevo atajo de teclado en editor avanzado: `Ctrl+S` / `Cmd+S` para guardar
    rapidamente cuando el contenido es valido
  - nuevo boton `Revertir cambios` en editor avanzado para descartar edicion
    local y volver al ultimo contenido cargado
  - `POST /config/{config_name}` ahora crea backup automatico del archivo
    previo en `data/backups/config/YYYY-MM-DD/` antes de persistir cambios
  - la UI ahora muestra la ruta del backup (`backup_path`) luego de guardar
    configuracion exitosamente
  - la UI ahora advierte al cerrar/recargar pestaña si hay cambios sin guardar
    en el editor avanzado (`beforeunload`)
  - tras guardar, la UI refresca `GET /config` para actualizar metadata
    (`modified_at`) en pantalla inmediatamente
  - nuevo endpoint `GET /config/{config_name}/backups` para listar backups
    disponibles del archivo de reglas seleccionado
  - la UI de configuracion avanzada muestra los ultimos backups (top 5)
    del archivo seleccionado con fecha/nombre/tamaño
  - nuevo endpoint `POST /config/{config_name}/restore` para restaurar
    configuracion desde backup_path validado (ruta segura + prefijo esperado)
  - naming de backups endurecido con microsegundos para evitar colisiones
    en guardados consecutivos dentro del mismo segundo
  - la UI avanzada permite restore desde backups recientes (`Usar` + `Restaurar backup`)
    con confirmacion explicita previo al rollback
  - hardening en `GET /config/{config_name}/backups`: parametro `limit`
    validado en rango `1..100` para controlar carga de respuesta
  - la UI avanzada agrega selector de cantidad visible de backups recientes
    (1..20) aprovechando `limit` en el endpoint
  - feedback de restore mejorado en UI: muestra backup origen restaurado y
    backup de seguridad generado antes del rollback
- contratos tipados (`Protocol`) extendidos a clientes HTTP adicionales:
  - `src/clients/argentinadatos.py` ahora acepta `get_fn: HttpGetProtocol`
  - `src/clients/bonistas_client.py` ahora acepta `get_fn: HttpGetProtocol` en fetch/listing/macro/portfolio
  - mantiene comportamiento existente y mejora testabilidad/inyeccion de cliente

### Testing

- `tests/test_argentinadatos_client.py`: nuevo caso de inyeccion de `get_fn` en `get_dollar_series`
- `tests/test_bonistas_client.py`: nuevo caso de inyeccion de `get_fn` en `_fetch_html`
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
- `scripts/report_sections.py`: resumen compacto de `Bonos Locales` ahora evita
  renderizar `nan` literal en `TIR/Paridad/MD` y muestra `-` cuando no hay dato.
  Se agrega test de regresion en `tests/test_report_render_ui.py`.

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
