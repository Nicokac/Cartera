# Product Roadmap v0.3

Fecha de validacion: 2026-04-28

## Resultado del analisis

El roadmap propuesto coincide en lineas generales con el estado actual del proyecto y es aplicable como plan de ejecucion.

## Cierre final

Estado final al 2026-05-01:

- roadmap completado
- pendientes reales abiertos: `0`
- fases `v0.3`, `v0.4` y `v0.5` cerradas
- documento pasa de plan de ejecucion a registro de cierre de implementacion
- release materializada para distribucion: `0.5.3`

## Continuidad post-cierre (UI)

Con el roadmap de producto cerrado, la siguiente linea de trabajo activa pasa a UX/UI del reporte:

- documento de ejecucion: `docs/report-ui-embellecimiento-plan.md`
- alcance: embellecimiento visual y mejora de jerarquia, manteniendo arquitectura single-page
- estrategia: auditoria estructural -> modularizacion de shell/componentes -> prioridades visuales -> implementacion incremental
- baseline de version para esta etapa: `0.5.3`

Avance UI post-cierre:

- 2026-05-01: iniciado Fase UI-1 del reporte (`real-report`) con refactor de JS de interaccion a `static/report-ui.js`, conservando salida y comportamiento mediante inyeccion inline desde `scripts/report_layout.py`.
- 2026-05-01: continuacion Fase UI-1 con embellecimiento base en `static/styles.css`:
  - mejor jerarquia visual de `quick-nav`, cards y paneles
  - mejoras de foco visible y microinteracciones
  - headers de tabla sticky para lectura de tablas largas
  - fix de mojibake en indicador de colapsables (`\25B8`)
- 2026-05-01: refactor tecnico adicional (sin cambios visuales) para desacoplar assets del renderer:
  - nuevo modulo `scripts/report_assets.py` (carga/cache de CSS y JS)
  - `scripts/report_layout.py` consume `load_report_css()` y `load_report_js()`
  - base preparada para seguir modularizando `real-report` sin tocar UX
- 2026-05-01: refactor tecnico de composicion HTML:
  - nuevo modulo `scripts/report_document.py` para encapsular el documento HTML (head/body/assets)
  - `scripts/report_layout.py` queda enfocado en el contenido (`main`) y delega shell global al nuevo builder
  - sin cambios funcionales ni visuales en el reporte generado
- 2026-05-01: refactor de organizacion interna en `report_layout`:
  - nuevo helper `build_report_main_content(...)` para aislar el template principal del reporte
  - `build_report_body(...)` queda reducido a metadatos + orquestacion de documento
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor por bloques en `report_layout`:
  - extraidos helpers `build_report_hero(...)` y `build_technical_panel(...)`
  - menor acoplamiento del template principal y mejor separacion por secciones
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de shell de secciones en `report_layout`:
  - nuevo helper `build_report_sections_shell(...)` para agrupar el bloque central de cards/secciones
  - `build_report_main_content(...)` reduce complejidad y mejora legibilidad
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de metadatos de documento en `report_layout`:
  - nuevo helper `build_report_meta(...)` para encapsular `tab_title` y `meta_description`
  - `build_report_body(...)` reduce lógica incidental de composición
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de modularizacion del `main` del reporte:
  - nuevo modulo `scripts/report_layout_main.py` con:
    - `build_report_main_content(...)`
    - `build_report_hero(...)`
    - `build_technical_panel(...)`
    - `build_report_sections_shell(...)`
  - `scripts/report_layout.py` delega el armado del `main` para bajar acoplamiento
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de metadatos a modulo dedicado:
  - nuevo `scripts/report_meta.py` con `build_report_meta(...)`
  - `scripts/report_layout.py` elimina logica de metadatos inline y delega
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de orquestacion final del render:
  - nuevo `scripts/report_page.py` para centralizar `meta + main + document`
  - `scripts/report_layout.py` conserva API publica (`build_report_body`) como wrapper
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de shell de secciones a modulo dedicado:
  - nuevo `scripts/report_layout_sections.py` con builders de integridad, header cards, quick-nav, panorama, cambios, regimen y preview de sizing
  - `scripts/report_layout.py` reduce responsabilidad y conserva builders de decision/cartera/integridad + wrapper publico
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor adicional de modularizacion de secciones:
  - `scripts/report_layout_sections.py` incorpora tambien builders de `decision`, `cartera` e `integridad`
  - `scripts/report_layout.py` queda como fachada de compatibilidad (re-export de builders + `build_report_body`)
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de acoplamiento entre composer y renderer:
  - nuevo adaptador `compose_report_body_inputs(...)` en `scripts/report_composer.py` para centralizar el mapping `context/sections -> build_report_body(...)`
  - `scripts/report_renderer.py` deja de acoplarse a claves internas del composer y delega el armado de kwargs al adaptador
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de tipado interno en composer de reporte:
  - nuevos `TypedDict` en `scripts/report_composer.py`: `RenderSections` y `ReportBodyInputs`
  - `build_render_sections(...)` y `compose_report_body_inputs(...)` ahora devuelven contratos tipados explícitos
  - sin cambios funcionales ni visuales
- 2026-05-01: refactor de complejidad en `prepare_render_context(...)`:
  - extraidos sub-builders privados en `scripts/report_composer.py`:
    - `_extract_bonistas_context(...)`
    - `_extract_coverage_context(...)`
    - `_extract_decision_context(...)`
  - `prepare_render_context(...)` queda como orquestador de contexto con menor acoplamiento interno
  - sin cambios funcionales ni visuales
- 2026-05-01: saneamiento adicional de contexto de render:
  - nuevo helper privado `_build_pending_portfolio_rows(...)` en `scripts/report_composer.py`
  - `prepare_render_context(...)` delega armado de pendientes de consolidacion y reduce logica inline
  - sin cambios funcionales ni visuales
- 2026-05-01: snapshot documental de arquitectura de renderer post-refactor:
  - actualizado `docs/report-ux-architecture.md` con modulos vigentes (`report_layout_sections`, `report_page`, `report_document`, `report_assets`, etc.)
  - agregado flujo de render actual extremo a extremo para facilitar onboarding y proxima fase de embellecimiento
- 2026-05-01: gate formal de cierre de refactor UI:
  - nuevo `docs/report-ui-ready-checklist.md` con criterios `ready for visual redesign`
  - enlaces agregados en `docs/README.md` y `README.md` para entrada rapida a la fase de embellecimiento
- 2026-05-01: contrato IA para fase visual:
  - nuevo `docs/report-ia-architecture.md` con division en 8 modulos de producto, niveles de lectura (rapida/analisis/auditoria), mapeo bloque->modulo y backlog P1/P2/P3
  - `docs/report-ui-embellecimiento-plan.md` enlaza explicitamente este contrato como base de ejecucion
  - `docs/README.md` y `README.md` incorporan link directo al contrato
- validacion aplicada:
  - `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
  - 32 tests OK

Ajustes puntuales detectados al validar contra el repo actual al inicio del trabajo:

- Cobertura total actual: 84% (no 87%).
- Suite actual: 47 archivos `test_*.py` (alineado con el plan).
- Piso de cobertura en CI: 82% (alineado con el plan de subir a 85%).
- `POST /cancel` y boton de cancelacion en UI ya implementados (estado final `interrupted`).
- `status/detail` sigue con `log_tail` de 1200 chars. (resuelto durante la ejecucion)

## Avance de ejecucion

- 2026-04-28: completado primer item P1 de v0.3 (`POST /cancel` + boton UI).
- 2026-04-28: completado segundo item P1 de v0.3 (deteccion de corrida huerfana al startup y marcado `interrupted`).
- 2026-04-28: completado tercer item P1 de v0.3 (sanitizacion de secretos en `/status/detail`).
- 2026-04-28: completado cuarto item P1 de v0.3 (retry con backoff en clientes IOL y BCRA).
- 2026-04-28: completado quinto item P1 de v0.3 (cobertura >=82% en `sizing.py` y `bcra.py`).
- 2026-04-28: completado sexto item P1 de v0.3 (backup diario automatico de `data/runtime/*.csv`).
- 2026-04-28: completado septimo item P1 de v0.3 (scripts Bash Fase 1 cross-platform).
- 2026-04-28: completado primer item P2 de v0.4 (modal custom de confirmacion; reemplaza `window.confirm()`).
- 2026-04-28: completado segundo item P2 de v0.4 (panel de reportes anteriores en UI).
- 2026-04-28: completado tercer item P2 de v0.4 (centralizacion de utilidades de texto/numericas en `src/common/`).
- 2026-04-28: completado cuarto item P2 de v0.4 (token de sesion simple para `POST /run`).
- 2026-04-28: completada mejora de observabilidad en `/status/detail` (`log_tail` ampliado + `log_lines`).
- 2026-04-28: completados items P2 de validacion de input en `/run` (aporte externo no negativo, `username/password` con maximo 200 chars) y manejo explicito de error de `Popen` (HTTP 500 claro).
- 2026-04-28: completado item P2 de performance/observabilidad: `/status/detail` ahora expone `elapsed_seconds`.
- 2026-04-28: completado item P2 de observabilidad: log de tiempos por fase en `generate_real_report.py` (formato `Fase <nombre>: <seg>s`).
- 2026-04-28: completado item P2 de observabilidad: `LOG_FORMAT=json` opcional para structured logging en `generate_real_report.py`.
- 2026-04-28: completado item P2 de mantenibilidad/documentacion: nuevo `CONTRIBUTING.md` con setup, convenciones, tests y flujo de PR.
- 2026-04-28: completado item P2 de documentacion: `docs/decisions/` con ADRs iniciales (subprocess, CSV sin DB, float->Decimal gradual).
- 2026-04-29: completado item P2 de accesibilidad en UI (`aria-live` en estado, `aria-label` de icono y mensajes de error con `role=\"alert\"`).
- 2026-04-29: hardening adicional en `/run`: rechazo backend de `username/password` vacios (HTTP 422) para evitar corridas invalidas ante fallos de validacion en frontend/autocompletado.
- 2026-04-29: completados pendientes UX: tooltip explicativo en `Aporte externo ARS` y link `Ver log completo` cuando el estado es `error`.
- 2026-04-29: item P2 de DevOps (`macos-latest` en CI) queda temporalmente como deuda tecnica por inestabilidad inicial en GitHub Actions (luego resuelto).
- 2026-04-29: fix de estabilidad CI: `server.py` asegura creacion de `reports/` antes del mount de archivos estaticos.
- 2026-04-29: `ubuntu-latest` en CI tambien queda temporalmente desactivado para no bloquear entregas durante el ajuste inicial (luego resuelto).
- 2026-04-29: completado item P2 de escalabilidad/documentacion: checklist formal de alta de instrumento (`docs/instrument-onboarding-checklist.md`).
- 2026-04-29: completado item P1 de documentacion API: README referencia `/docs` y `/openapi.json` de FastAPI.
- 2026-04-29: completado item P2 de UX: panel de corridas recientes (ultimas 5) con endpoint `GET /runs/recent`.
- 2026-04-29: completado item P3 de UX/UI: indicador de progreso estimado durante corrida (barra + etapa textual por tiempo transcurrido).
- 2026-04-29: completado item P3 de seguridad: rate limiting basico en `POST /run` (maximo 3 requests/minuto).
- 2026-04-29: completado item P3 de integraciones: nuevo endpoint `GET /api-health` para chequeo resumido de conectividad externa.
- 2026-04-29: completado item P2 de datos/escalabilidad: purga automatica de `prediction_history.csv` con retencion configurable (default 90 dias).
- 2026-04-29: completado item P3 de performance: cache intradia de precios IOL con TTL de 15 minutos para reducir re-fetch en corridas sucesivas.
- 2026-04-29: completado item P3 de documentacion: diagrama de arquitectura (Mermaid) en `docs/README.md`.
- 2026-04-29: completado item P3 de testing: prueba de concurrencia en `/run` (2 requests simultaneos, segundo responde `409`).
- 2026-04-29: completado item P1 de DevOps: script de release automatizado (`scripts/release.ps1`) para bump de version, tag y build de distribucion.
- 2026-04-29: completado item P3 de observabilidad: webhook opcional por fin de corrida (`RUN_COMPLETION_WEBHOOK_URL`).
- 2026-04-29: completado item P3 de datos: validacion basica de integridad/schema de CSV runtime al startup con cuarentena automatica de archivos invalidos.
- 2026-04-29: completado item P3 de usabilidad operativa: scheduler opcional por intervalo (`--schedule-every-minutes N`) en `generate_real_report.py`.
- 2026-04-29: completado item P2 de integraciones: circuit breaker simple en `/api-health` (apertura tras fallas consecutivas y reintento post-cooldown).
- 2026-04-29: completado item P2 de escalabilidad/datos: retencion configurable tambien para `decision_history.csv` (default 365 dias).
- 2026-04-29: completado item P3 de accesibilidad en reporte: headers de tablas con `scope=\"col\"` en tablas generadas por renderer.
- 2026-04-29: avance P2 de arquitectura/mantenibilidad: refactor incremental de `apply_base_scores` extrayendo inicializacion de sub-scores a helper dedicado (`_initialize_base_scores`).
- 2026-04-29: avance P2 de arquitectura/mantenibilidad: refactor incremental adicional de `apply_base_scores` separando blend absoluto, concentracion/momentum y composicion de scores en helpers privados (`_apply_absolute_metric_blends`, `_apply_concentration_and_momentum_scores`, `_apply_refuerzo_score`, `_apply_reduccion_score`) sin cambios funcionales.
- 2026-04-29: completado item P2 de arquitectura/mantenibilidad en `sizing`: extraccion de `_comentario_operativo` a modulo dedicado `src/decision/operational_comments.py` con wrapper de compatibilidad en `sizing.py`.
- 2026-04-29: avance P3 de arquitectura/escalabilidad: contratos tipados con `typing.Protocol` para clientes HTTP externos (`src/clients/protocols.py`) e integracion no disruptiva en clientes IOL/BCRA.
- 2026-04-29: avance P1 de Dimension 19: umbrales minimos formalizados en codigo (`MIN_RUNS_FOR_STREAK=10`, `MIN_RUNS_FOR_RELIABLE_SERIES=20`, `MIN_OUTCOMES_PER_FAMILY_FOR_CALIBRATION=30`) y apagado automatico del fallback legacy de snapshots cuando la carpeta canonica ya alcanza ventana suficiente.
- 2026-04-30: completado P1 documental de Dimension 19: umbrales minimos (10/20/30) explicitados en `README.md` y `docs/ayuda-usuario.txt`.
- 2026-04-29: completado item P2 de Dimension 19: `quality label` en decision table del HTML (`Robusta/Parcial/Corta/Sin historia`) derivado del historial temporal por ticker/subfamilia.
- 2026-04-29: completado item P2 de Dimension 19: seccion de metricas de acierto del predictor en HTML (`%` global y `%` por `asset_family`) basada en outcomes verificados del `prediction_history`.
- 2026-04-29: completado item P2 de Dimension 19: tablero `Evolucion de racha` en prioridades de decision para destacar persistencia temporal por ticker (racha >=2, excluye Liquidez).
- 2026-04-30: hardening de robustez en runtime real: normalizacion defensiva de payload de operaciones IOL (lista directa o wrapper `operaciones`) para evitar fallas por respuestas no homogéneas.
- 2026-04-30: completado item P3 de DevOps: `Dockerfile` y `.dockerignore` para entorno de desarrollo/testing en contenedor.
- 2026-04-30: completado item P2 de Dimension 19: validacion de riesgo historico contra benchmark externo (MEP) cuando `serie_agregada_confiable` esta activa.
- 2026-04-30: hotfix de render para Dimension 19: correccion de llamada a `fmt_score` en bloque benchmark de riesgo (evita `TypeError` en `generate_real_report.py`).
- 2026-04-30: completado item P2 de Dimension 19: revision de thresholds de scoring contra outcomes reales acumulados via bloque `Acierto por banda de score` en Prediccion.
- 2026-04-30: avance P3 de Dimension 19: tablero de preparacion para calibracion por `asset_family` (conteos `up/down/neutral` y estado `Lista/Pendiente` con umbral 30 por senal).
- 2026-04-30: avance P3 de Dimension 19: calibracion por `asset_family` implementada en modo opt-in (`calibration.family_enabled`) con `family_overrides` por señal y gating por umbral de muestra.
- 2026-04-30: avance P3 de Dimension 19: soporte multi-horizonte en metricas historicas de Prediccion (`Acierto por horizonte` usando `horizon_days`).
- 2026-04-30: avance P3 de Dimension 19: opcion B de clasificador sobre `signal_votes` integrada en modo experimental (sin reemplazar direccion principal).
- 2026-04-30: completado item P2 de DevOps CI: matriz `ubuntu-latest` + `macos-latest` vuelve a modo bloqueante (sin `continue-on-error` por SO).
- 2026-04-30: hotfix CI: `pyproject.toml` normalizado a UTF-8 sin BOM para compatibilidad con parser de `coverage` en GitHub Actions.
- 2026-04-30: avance P2 de DevOps/CI: se reactiva ejecucion de tests en `ubuntu-latest` y se reincorpora `macos-latest` de forma transicional para recuperar visibilidad previa al cierre bloqueante final.
- 2026-04-30: avance P2 de arquitectura/mantenibilidad: refactor incremental en `apply_base_scores` extrayendo ajustes efectivos de ETF/calidad a helper dedicado (`_apply_etf_effective_scores`) sin cambios funcionales.
- 2026-04-30: mejora de compatibilidad FastAPI: migracion de startup a `lifespan` en `server.py` (se elimina uso de `@app.on_event("startup")` deprecado, manteniendo `on_startup()` como helper de compatibilidad para tests).
- 2026-04-30: hardening UX/operabilidad en errores de corrida: `server.py` resume fallas de autenticacion IOL (`401 /token`) con mensaje amigable en `status/error` y deja traceback completo en `log_tail` para diagnostico.
- 2026-04-30: hardening de CI en GitHub Actions: workflow `unittest` fuerza runtime Node 24 para acciones JavaScript (`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`) y evita dependencia en Node 20 deprecado.
- 2026-04-30: mejora UX/accesibilidad en estado UI: badge visual por estado (Inactivo/En ejecucion/Completado/Interrumpido/Error) con colores y texto explicito, manteniendo `aria-label` y mensajes funcionales existentes.
- 2026-04-30: avance P2 de arquitectura/mantenibilidad: refactor incremental adicional en `apply_base_scores` extrayendo el calculo de `score_despliegue_liquidez` a helper dedicado (`_apply_liquidity_deployment_score`) sin cambios funcionales.
- 2026-04-30: avance P2 de arquitectura/mantenibilidad: refactor incremental adicional en `apply_base_scores` extrayendo post-procesado final (ajustes de regimen + clamp de `score_reduccion` + despliegue de liquidez) a helper `_apply_post_regime_adjustments`, sin cambios funcionales.
- 2026-04-30: avance P2 de arquitectura/mantenibilidad: refactor incremental adicional en `apply_base_scores` extrayendo parseo de configuracion/umbrales a helper `_parse_base_score_config`, manteniendo defaults y comportamiento.
- 2026-04-30: hardening de seguridad operativa: `POST /cancel` ahora requiere `X-Session-Token` (alineado con `/run`), con ajuste en UI para enviar token de sesion y test de rechazo `401` sin token.
- 2026-04-30: avance P3 de calidad/tipado: `scoring.py` incorpora `TypedDict` (`BaseScoreConfig`) para tipar el resultado de `_parse_base_score_config` y reducir ambiguedad de `dict[str, object]` en `apply_base_scores`.
- 2026-04-30: completado item P2 de compatibilidad documental: matriz oficial de navegadores soportados en `docs/browser-support.md` + referencias en `README.md` y `docs/README.md`.
- 2026-04-30: avance P3 de calidad/tipado: simplificacion de `apply_base_scores` para usar `BaseScoreConfig` tipado sin casts redundantes, manteniendo comportamiento.
- 2026-04-30: hardening de seguridad en observabilidad: `GET /status/detail` ahora requiere token de sesion (header `X-Session-Token` o query `token`), y UI actualiza `Ver log completo` con token para mantener trazabilidad sin exponer logs anonimamente.
- 2026-04-30: hardening adicional de endpoints operativos: `GET /reports/list` y `GET /runs/recent` ahora requieren `X-Session-Token`; UI actualiza fetch autenticado para ambas secciones.
- 2026-04-30: hardening adicional de endpoint de estado: `GET /status` ahora requiere `X-Session-Token`; UI actualiza polling y carga inicial de estado con token de sesion.
- 2026-04-30: hardening adicional de endpoint de diagnostico externo: `GET /api-health` ahora requiere `X-Session-Token`; tests adaptados para validar `401` sin token.
- 2026-04-30: avance P2 de mantenibilidad/seguridad en servidor: centralizacion de validacion de sesion en helper unico `_require_session_token(...)`, aplicado a todos los endpoints protegidos para evitar duplicacion y desalineaciones.
- 2026-04-30: completado item P3 de accesibilidad (avance UI local): mini-auditoria de contraste WCAG en `static/index.html` con ajustes de colores secundarios/disabled y reporte en `docs/accessibility-contrast-audit.md`.
- 2026-04-30: avance P2 de arquitectura/mantenibilidad: `apply_base_scores` reduce complejidad estructural al extraer su orquestacion principal a helper `_compute_base_scores_from_config`, manteniendo reglas y resultados.
- 2026-04-30: avance P2 de mantenibilidad frontend: centralizacion de llamadas autenticadas en UI con helper `fetchWithSession(...)` para evitar duplicacion de headers/token en `/run`, `/cancel`, `/status`, `/reports/list` y `/runs/recent`.
- 2026-04-30: avance P2 de testing cross-platform: nuevo smoke estructural para scripts Bash (`tests/test_bash_scripts.py`) e incorporacion en CI (`.github/workflows/ci.yml`).
- 2026-04-30: avance P2 de testing/mantenibilidad de scoring: nuevos tests unitarios para `_parse_base_score_config` (defaults + overrides) en `tests/test_decision_scoring.py` para bloquear contrato de configuracion.
- 2026-04-30: avance P2 de testing/seguridad en servidor: nueva cobertura unitaria directa para `_require_session_token(...)` (token valido, invalido y sesion no inicializada) en `tests/test_server.py`.
- 2026-04-30: avance P3 de compatibilidad: checklist formal de validacion mobile/responsive del reporte en `docs/report-mobile-responsive-checklist.md` (viewports objetivo, navegadores y criterios de aceptacion).
- 2026-04-30: completado cierre de deuda documental remanente: se normaliza estado de CI activo (`ubuntu-latest` + `macos-latest`) en `README.md` para alinear documentacion con el workflow vigente.
- 2026-04-30: avance P3 de usabilidad operativa: configuracion basica de scoring desde UI local (`GET/POST /config/scoring` + seccion "Configuracion de scoring (avanzado)" en `static/index.html`).
- 2026-04-30: avance P3 de arquitectura/escalabilidad: adopcion de `HttpGetProtocol` tambien en clientes `argentinadatos` y `bonistas_client` (inyeccion de requester tipado sin cambios funcionales).
- 2026-04-30: hardening de UX de reporte en Bonos Locales: el resumen compacto ya no muestra literales `nan` y usa fallback `-` para TIR/Paridad/MD cuando faltan datos.
- 2026-04-30: avance P3 de usabilidad operativa: editor UI de configuracion ampliado de solo `scoring_rules.json` a `scoring/action/sizing` via endpoint generico protegido (`GET/POST /config/{config_name}` con allowlist).
- 2026-04-30: avance de observabilidad en integraciones: `/api-health` ahora incluye `checked_at` por proveedor para trazabilidad temporal de cada chequeo.
- 2026-04-30: avance de usabilidad operativa/API: nuevo `GET /config` para descubrir configuraciones editables soportadas (`scoring`, `action`, `sizing`).
- 2026-04-30: avance UX operativo: selector de reglas en UI ahora se puebla dinamicamente desde `GET /config` (evita desalineacion entre frontend y allowlist backend).
- 2026-04-30: avance P2 de arquitectura/mantenibilidad: refactor incremental adicional en `_compute_base_scores_from_config` para reducir variables intermedias y mantener flujo declarativo basado en `BaseScoreConfig` (sin cambios funcionales).
- 2026-04-30: avance de usabilidad operativa/API: `GET /config` ahora devuelve metadata por archivo (`filename`, `exists`, `modified_at`) para diagnóstico y UX de configuración avanzada.
- 2026-05-01: avance UX operativo en configuracion avanzada: la UI ahora muestra metadata del archivo seleccionado (`filename`, `exists`, `modified_at`) usando `GET /config`.
- 2026-05-01: avance UX operativo adicional en configuracion avanzada: editor con estado de cambios pendientes (`dirty state`) y habilitacion de `Guardar` solo para JSON valido.
- 2026-05-01: avance UX operativo adicional en configuracion avanzada: boton `Formatear JSON` para pretty-print local previo a guardado.
- 2026-05-01: avance UX operativo adicional en configuracion avanzada: atajo `Ctrl+S/Cmd+S` dentro del editor para guardar rapido cuando hay cambios validos.
- 2026-05-01: avance UX operativo adicional en configuracion avanzada: boton `Revertir cambios` para volver al ultimo contenido cargado localmente.
- 2026-05-01: hardening operativo de configuracion avanzada: `POST /config/{config_name}` ahora genera backup automatico del archivo previo en `data/backups/config/YYYY-MM-DD/`.
- 2026-05-01: avance UX operativo adicional: la UI muestra `backup_path` al guardar configuracion para facilitar rollback manual.
- 2026-05-01: hardening UX de editor avanzado: aviso `beforeunload` cuando hay cambios sin guardar para evitar perdida accidental de edicion.
- 2026-05-01: mejora UX de configuracion avanzada: post-guardado refresca metadata (`modified_at`) desde `GET /config` para mostrar estado actualizado en el panel.
- 2026-05-01: avance de usabilidad operativa/API: nuevo `GET /config/{config_name}/backups` para listar historico de backups por archivo de reglas.
- 2026-05-01: avance UX operativo: la UI de configuracion avanzada muestra “Backups recientes” (top 5) del archivo seleccionado usando `GET /config/{config_name}/backups`.
- 2026-05-01: avance de usabilidad operativa/API: nuevo `POST /config/{config_name}/restore` para rollback controlado desde backup_path con validacion de ruta segura.
- 2026-05-01: avance UX operativo: restore de configuracion desde backup integrado en UI avanzada (seleccion desde lista + confirmacion).
- 2026-05-01: hardening API de backups: `GET /config/{config_name}/backups` ahora valida `limit` en rango `1..100`.
- 2026-05-01: cierre funcional de configuración operativa en UI: editor avanzado completo para `scoring/action/sizing` con discovery, validación JSON, dirty-state, format/revert, backup/restore y trazabilidad de cambios.
- 2026-05-01: completado item de testing CI: piso de cobertura sube de 82% a 85% en `.github/workflows/ci.yml` (cobertura local suite estable: 89%).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_absolute_metric_blends` reduce repeticion de acceso a reglas por metrica mediante helper local `_metric_rules` (sin cambios funcionales).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_refuerzo_score` reduce repeticion al leer ajustes por subfamilia mediante helper local `_rule_value` (sin cambios funcionales).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_reduccion_score` reduce repeticion al leer ajustes por subfamilia mediante helper local `_rule_value` (sin cambios funcionales).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_etf_effective_scores` reduce repeticion de lectura de ajustes ETF mediante helper local `_adj` (sin cambios funcionales).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_concentration_and_momentum_scores` elimina duplicacion de formulas de concentracion con helper `_piecewise_linear_score` (sin cambios funcionales).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_concentration_and_momentum_scores` extrae helper `_weighted_momentum` para evitar duplicacion en calculo de `Momentum_Refuerzo` y `Momentum_Reduccion` (sin cambios funcionales).
- 2026-05-01: avance P2 de mantenibilidad en scoring: `_apply_refuerzo_score` y `_apply_reduccion_score` consolidan lectura de pesos en helper local `_weight` para reducir ruido y repeticion (sin cambios funcionales).
- 2026-05-01: avance UX operativo: selector en UI para cantidad de backups recientes visibles (1..20), usando query `limit` del endpoint.
- 2026-05-01: mejora UX de restore: la UI ahora muestra trazabilidad completa post-restore (`restored_from` + backup de seguridad previo).
- 2026-05-01: completado item P3 de arquitectura/escalabilidad: contratos `typing.Protocol` extendidos tambien a clientes FRED y PyOBD, con inyeccion tipada testeable en clientes externos restantes.
- 2026-05-01: completado item P1 de seguridad: auditoria operativa de credenciales reforzada con tests para asegurar que la resolucion CLI de usuario/password no imprime secretos.
- 2026-05-01: completado item P1 de seguridad: filtrado de secretos en `/status/detail` queda cubierto tanto en `error` como en `log_tail`, respaldado por pruebas unitarias.
- 2026-05-01: completado item P2 de arquitectura/mantenibilidad: `apply_base_scores` queda reducido a orquestacion minima sobre `_parse_base_score_config(...)` y `_compute_base_scores_from_config(...)`; el refactor incremental se considera cerrado.
- 2026-05-01: completado item P2 de datos/persistencia: montos criticos de valuacion (`Valorizado_ARS`, `Ganancia_ARS`, `Valor_USD`) pasan a calcularse con `Decimal` en `src/portfolio/valuation.py`, manteniendo salida compatible en `float` para el resto del pipeline.
- 2026-05-01: avance P3 de calidad/tipado: se introduce alias compartido `DateLike` (`src/common/types.py`) y se reemplaza `object` generico en flujo temporal de `pipeline`, `prediction.store`, `prediction.verifier` y `decision.history`.
- 2026-05-01: avance P3 de calidad/tipado: `portfolio.operations` y `decision.sizing` reemplazan bundles de salida `dict[str, object]` por `TypedDict` especificos (`OperationsBundle`, `PositionTransitionBundle`, `SizingBundle`), manteniendo contratos runtime intactos.
- 2026-05-01: avance P3 de calidad/tipado: `decision.actions`, `decision.market_regime_scoring`, `decision.sizing` y `analytics.bond_analytics` reemplazan configuraciones/contextos `dict[str, object]` por `Mapping[str, Any]` o `TypedDict` donde el contrato ya era estable.
- 2026-05-01: avance P3 de calidad/tipado: `analytics.portfolio_risk` y `analytics.technical` incorporan `TypedDict` para filas/bundles y reemplazan configuraciones `dict[str, object]` por tipos mas especificos sin cambiar comportamiento.
- 2026-05-01: completado item P3 de calidad/tipado: barrido final de `dict[str, object]`/contratos genericos en `decision.scoring`, `clients.bcra`, `clients.pyobd_client` y `portfolio.operations`; el codigo fuente (`src/`) queda sin remanentes de esos contratos genericos en puntos relevados del roadmap.
- 2026-05-01: completado item P2 de compatibilidad: wrappers PowerShell (`setup/start/status/smoke/run`) ya operan en `pwsh` cross-platform con resolucion de `.venv` por SO, apertura de browser portable y uso de token de sesion para endpoints protegidos.
- 2026-05-01: completado item P2 de mantenibilidad: `build_operational_proposal` en `src/decision/sizing.py` se parte en helpers internos para acciones operativas, comentarios, rankings, fondeo y asignacion de refuerzos; el pendiente de refactor de funciones largas queda cerrado.
- 2026-05-01: post-cierre de roadmap: hardening del renderer HTML y memoria temporal para corregir mojibake residual en el reporte (`Predicción`, `Régimen`, `Acción`, símbolos de señal y título de pestaña), mejorar copy (`Metodología`, singular/plural de instrumentos) y alinear `quality_label` con los umbrales visibles del producto.

Prueba de cierre (si aplica):
- correr `python -m unittest tests.test_prediction_store tests.test_prediction_cycle -v`
- ejecutar una corrida real/no interactiva y verificar que `data/runtime/prediction_history.csv` no conserve filas con `run_date` fuera de ventana de retencion
- correr `python -m unittest tests.test_generate_real_report_split_runtime tests.test_generate_real_report -v`
- ejecutar dos corridas seguidas en menos de 15 minutos y verificar que se crea/actualiza `data/runtime/iol_price_cache.json`
- abrir `docs/README.md` en GitHub/visor Markdown y validar que el bloque Mermaid renderiza correctamente
- correr `python -m unittest tests.test_server.TestPostRun.test_concurrent_run_requests_second_returns_409 -v`
- ejecutar `.\scripts\release.ps1 -Version X.Y.Z -DryRun` y validar que:
  - detecta version actual/nueva
  - no modifica archivos en modo dry run
  - informa correctamente tag y pasos de build
- exportar `RUN_COMPLETION_WEBHOOK_URL` y correr una corrida:
  - confirmar que al finalizar se emite `POST` con `status`, `started_at`, `finished_at`, `username`, `usar_liquidez_iol`, `aporte_externo_ars`, `error`
- crear un `data/runtime/decision_history.csv` invalido (header incorrecto), reiniciar servidor y verificar que:
  - el archivo se mueva a `data/runtime/corrupt/*.corrupt`
  - el server arranque normal
- correr `python -m unittest tests.test_generate_real_report -v` y validar casos de scheduler
- ejecutar una corrida programada con `--schedule-every-minutes` en modo `--non-interactive`
- correr `python -m unittest tests.test_server.TestGetHealth -v`
- disparar varias consultas a `/api-health` con una API simulada caída y verificar `circuit_open=true`
- correr `python -m unittest tests.test_decision_history tests.test_generate_real_report -v`
- setear `DECISION_HISTORY_RETENTION_DAYS` y verificar poda de filas antiguas en `data/runtime/decision_history.csv`
- correr `python -m unittest tests.test_report_primitives tests.test_report_sections_prediction -v`
- abrir `reports/real-report.html` y validar que los `th` incluyan `scope=\"col\"`
- correr `python -m unittest tests.test_decision_scoring tests.strategy_rules_technical_scoring -v`
- validar sobre una corrida real existente que ranking/acciones sugeridas no cambian respecto a baseline previo para mismo input (control de no regresion funcional del refactor)
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- correr `python -m unittest tests.test_report_sections_prediction tests.test_report_render_core tests.test_report_render_ui tests.test_decision_history -v`
- generar `reports/real-report.html` y validar:
  - sin textos mojibake (`Predicción`, `Régimen`, `Acción`, `Señales`)
  - pestaña del browser con `Real Run - YYYY-MM-DD | Cartera de Activos`
  - columna `Confianza` con separación correcta entre label y porcentaje (`baja 19.37%`)
  - `Calidad historia` consistente con los umbrales visibles (ej. corrida 20 -> `Robusta`)
- validar que el refactor de concentracion/momentum mantiene exactamente el mismo comportamiento de `apply_base_scores` (sin cambios en scores ni recomendaciones para un mismo input)
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar que `Momentum_Refuerzo` y `Momentum_Reduccion` no cambian tras la extraccion de `_weighted_momentum` (refactor sin cambio funcional)
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- validar que el refactor a `report_layout_sections.py` no cambia salida funcional del reporte (navegacion, paneles y tablas renderizados)
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- validar que `report_layout.py` sigue exponiendo la misma API publica para `report_composer` tras quedar como fachada
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- validar que `render_report(...)` mantiene salida equivalente tras delegar kwargs a `compose_report_body_inputs(...)`
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- validar que el tipado (`TypedDict`) no altera el contrato runtime de `render_report(...)`
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- validar que `prepare_render_context(...)` conserva mismas claves consumidas por `build_render_sections(...)` tras la extraccion de sub-builders
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core tests.test_report_primitives -v`
- validar que `pending_portfolio_rows` sigue mostrandose en `Cartera` cuando hay operaciones sin consolidar
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar que `score_refuerzo` y `score_reduccion` se mantienen estables para el mismo input tras la centralizacion de pesos con `_weight`
- correr `python -m unittest tests.test_fred_client tests.test_pyobd_client -v`
- validar que FRED y PyOBD aceptan clientes inyectados tipados sin depender de patching interno del modulo
- correr `python -m unittest tests.test_generate_real_report_split_cli tests.test_server -v`
- validar que la resolucion CLI de credenciales y `/status/detail` no exponen usuario/password reales en mensajes, `error` ni `log_tail`
- correr `python -m unittest tests.test_valuation_and_checks tests.test_pipeline tests.test_sizing -v`
- validar que `Valorizado_ARS`, `Ganancia_ARS` y `Valor_USD` conservan comportamiento esperado tras la migracion interna a `Decimal` en valuacion
- correr `python -m unittest tests.test_prediction_store tests.test_prediction_verifier tests.test_decision_history tests.test_pipeline -v`
- validar que el alias `DateLike` no altera comportamiento de `run_date/outcome_date/today` en pipeline, persistencia y verificacion historica
- correr `python -m unittest tests.test_operations tests.test_sizing tests.test_pipeline -v`
- validar que los bundles tipados (`OperationsBundle`, `PositionTransitionBundle`, `SizingBundle`) no alteran payloads ni DataFrames expuestos por operaciones/sizing
- correr `python -m unittest tests.test_bond_analytics tests.test_sizing tests.test_pipeline tests.test_decision_scoring -v`
- validar que el reemplazo de `dict[str, object]` por `Mapping[str, Any]`/`TypedDict` no altera reglas de acciones, regimen de mercado, sizing ni analitica de bonos
- correr `python -m unittest tests.test_portfolio_risk tests.test_technical tests.test_pipeline -v`
- validar que `portfolio_risk` y `technical` mantienen exactamente las mismas series, metricas y tablas tras tipar filas/bundles de salida
- correr `python -m unittest tests.test_bcra_client tests.test_pyobd_client tests.test_operations tests.test_decision_scoring -v`
- validar que el barrido final de tipado en `scoring`, `bcra`, `pyobd_client` y `operations` no altera contratos ni resultados funcionales
- correr `python -m unittest tests.test_powershell_scripts -v`
- revisar `pwsh ./scripts/setup_local_app.ps1`, `pwsh ./scripts/status_local_app.ps1 -Detailed` y `pwsh ./scripts/smoke_local_app.ps1` para confirmar resolucion cross-platform de `.venv`, apertura portable y acceso autenticado a `/status` y `/status/detail`
- correr `python -m unittest tests.test_sizing tests.test_pipeline tests.test_operations -v`
- validar que `build_operational_proposal` mantiene exactamente los mismos candidatos top/descartados, comentarios operativos y calculo de fondeo tras la extraccion de helpers internos
- correr `python -m unittest tests.test_sizing tests.test_pipeline -v`
- ejecutar una corrida completa y verificar que la columna/comentario `comentario_operativo` mantiene el mismo comportamiento textual esperado en bonos, liquidez y CEDEARs
- correr `python -m unittest tests.test_iol_client tests.test_bcra_client -v`
- validar smoke de corrida normal para confirmar que login IOL y fetch BCRA mantienen comportamiento operativo esperado
- correr `python -m unittest tests.test_portfolio_risk tests.test_generate_real_report -v`
- validar que con >=20 snapshots en `data/snapshots/` ya no se tome `tests/snapshots/` como fallback legacy aunque `ENABLE_LEGACY_SNAPSHOTS=1`
- correr `python -m unittest tests.test_decision_history tests.test_report_render_core -v`
- abrir `reports/real-report.html` y validar que la tabla de decision muestra la columna `Calidad historia` con labels esperados
- correr `python -m unittest tests.test_prediction_store tests.test_generate_real_report tests.test_report_sections_prediction -v`
- abrir `reports/real-report.html` y validar en `Predicción`:
  - bloque `Acierto histórico (global)` con `%` y cantidad de outcomes
  - bloque `Acierto por familia` con `%` por `asset_family`
- correr `python -m unittest tests.test_report_render_ui tests.test_report_render_core -v`
- abrir `reports/real-report.html` y validar en `Decisión`:
  - bloque `Evolución de racha` visible
  - solo aparecen tickers con racha >=2
  - no aparece `Liquidez` en ese bloque
- correr `python -m unittest tests.test_generate_real_report_split_runtime -v`
- ejecutar `python scripts/generate_real_report.py` y validar que no falla en `extract_operation_quote_tickers` aunque IOL devuelva operaciones con formato no estándar
- correr `python -m unittest tests.test_portfolio_risk tests.test_generate_real_report tests.test_report_render_core -v`
- ejecutar una corrida real y validar en `Resumen -> Riesgo histórico`:
  - nueva fila de benchmark con `MEP`, estado de validacion, observaciones, correlacion y tracking error diario
  - si `serie_agregada_confiable=false`, el estado debe reflejar que la validacion se omite por baja confiabilidad
- correr `python -m unittest tests.test_generate_real_report tests.test_report_sections_prediction tests.test_prediction_store -v`
- ejecutar una corrida real y validar en `Predicción`:
  - bloque `Acierto por banda de score`
  - bandas visibles: `Bajo (<= -0.15)`, `Neutro (-0.15 a 0.15)`, `Alto (>= 0.15)` cuando exista muestra
- validar en `Predicción` el bloque `Preparación calibración por familia`:
  - muestra conteos por familia para `up/down/neutral`
  - estado `Lista` solo cuando `min(up,down,neutral) >= 30`
- correr `python -m unittest tests.test_prediction_calibration tests.test_prediction_cycle -v`
- (si aplica) habilitar en `prediction_weights.json`:
  - `calibration.family_enabled=true`
  - `calibration.family_min_per_direction=30`
  y verificar que `calibrate_prediction_weights` produce `family_overrides` en salida
- validar en `Predicción` el bloque `Acierto por horizonte`:
  - muestra precisión por `horizon_days` (ej. `5 ruedas`, `10 ruedas`)
  - conserva consistencia con el horizonte configurado de corrida
- validar en `Predicción`:
  - KPI `Coincidencia clasificador B`
  - valores persistidos de `classifier_b_direction`, `classifier_b_confidence`, `classifier_b_agrees` en historial de predicción
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- ejecutar una corrida y validar que el ranking/acciones sugeridas de `score_refuerzo` y `score_reduccion` se mantiene estable para el mismo input (control de no regresión del refactor)
- correr `python -m unittest tests.test_server -v`
- levantar `python server.py` y confirmar que ya no aparece `DeprecationWarning` por `on_event` en startup
- correr una corrida con password IOL invalida y validar en `/status/detail`:
  - `error = "Credenciales IOL invalidas. Verifica usuario/password e intenta nuevamente."`
  - `log_tail` conserva el traceback tecnico completo para soporte
- disparar un run de CI en GitHub Actions y validar:
  - job `unittest` ejecuta normalmente en `ubuntu-latest` y `macos-latest`
  - ya no aparece el warning de deprecacion por acciones en Node 20
- abrir la app local y validar el panel `Estado` en los 5 escenarios (`idle`, `running`, `done`, `interrupted`, `error`):
  - el badge textual cambia correctamente
  - el color del badge cambia segun estado
  - en `error`, se mantiene el mensaje funcional y el link `Ver log completo ->`
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar en una corrida baseline que la priorizacion de liquidez y `score_despliegue_liquidez` no cambia respecto al comportamiento previo
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar en corrida baseline que `score_reduccion` y el ranking final se mantienen iguales frente al baseline previo (control no regresion del post-procesado)
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar en corrida baseline que thresholds y pesos (`momentum`, `concentration`, `gain_clip`) se comportan igual que antes del refactor
- correr `python -m unittest tests.test_server -v`
- en UI, iniciar una corrida y cancelar:
  - cancelar desde app funciona normalmente
  - llamada manual `POST /cancel` sin `X-Session-Token` devuelve `401`
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar que no hay cambios funcionales en scoring tras el endurecimiento de tipado de config
- abrir `docs/browser-support.md` y validar que la matriz cubre:
  - desktop: Chrome/Edge/Firefox/Safari
  - mobile: iOS Safari/Chrome Android
- abrir app local y un `reports/*.html` en al menos 2 navegadores soportados y confirmar render correcto basico
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar en baseline que no cambia el resultado de `apply_base_scores` tras simplificacion de tipado
- correr `python -m unittest tests.test_server -v`
- validar manualmente:
  - `GET /status/detail` sin token responde `401`
  - `GET /status/detail?token=<token_sesion>` responde `200`
  - link `Ver log completo ->` desde UI abre correctamente el detalle autenticado
- correr `python -m unittest tests.test_server -v`
- validar manualmente:
  - `GET /reports/list` y `GET /runs/recent` sin token responden `401`
  - app local sigue mostrando `Reportes anteriores` y `Corridas recientes` normalmente (UI envia token)
- correr `python -m unittest tests.test_server -v`
- validar manualmente:
  - `GET /status` sin token responde `401`
  - la app local sigue mostrando estado y progreso en tiempo real (polling autenticado)
- correr `python -m unittest tests.test_server -v`
- validar manualmente:
  - `GET /api-health` sin token responde `401`
  - `GET /api-health` con `X-Session-Token` responde `200` y mantiene payload esperado
- correr `python -m unittest tests.test_server -v`
- validar smoke de endpoints protegidos (`/run`, `/cancel`, `/status`, `/status/detail`, `/reports/list`, `/runs/recent`, `/api-health`) para confirmar mismo comportamiento funcional post-refactor
- abrir `docs/accessibility-contrast-audit.md` y revisar cambios de color aplicados
- validar visualmente en UI local:
  - `#status-time` y `footer` con mayor contraste
  - botones deshabilitados legibles (`btn-run`, `btn-cancel`)
  - (opcional) verificar combinaciones con una herramienta WCAG AA de contraste
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar baseline de scoring para confirmar que ranking/acciones no cambian tras el refactor de orquestacion
- correr `python -m unittest tests.test_server -v`
- validar en UI local que:
  - iniciar corrida funciona
  - cancelar corrida funciona
  - estado/polling y listados (`Reportes anteriores`, `Corridas recientes`) cargan normalmente
- correr `python -m unittest tests.test_bash_scripts -v`
- validar en CI que la suite `tests.test_bash_scripts` corre en `ubuntu-latest`/`macos-latest`
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar que cambios en `scoring_rules` impactan en `gain_clip`, `momentum` y `concentration` como se espera (covered por tests de parse config)
- correr `python -m unittest tests.test_server -v`
- validar que helper `_require_session_token(...)`:
  - acepta token valido
  - rechaza token invalido
  - rechaza cuando no hay sesion inicializada
- ejecutar `docs/report-mobile-responsive-checklist.md` sobre `reports/real-report.html` en al menos:
  - `375x667` (mobile estandar) y `390x844` (mobile moderno)
  - iOS Safari o Chrome Android (si disponible) y Chrome desktop emulado
- validar que no haya overflow horizontal global y que tablas criticas (`Ticker`, `Accion`, `Score`) queden legibles con scroll local
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente en UI local:
  - seccion `Configuracion de scoring (avanzado)` carga JSON actual
  - `Guardar` persiste cambios validos y rechaza JSON invalido
- correr `python -m unittest tests.test_argentinadatos_client tests.test_bonistas_client -v`
- validar que `get_dollar_series(..., get_fn=...)` y `_fetch_html(..., get_fn=...)` acepten inyeccion de cliente HTTP (sin usar red real en test)
- correr `python -m unittest tests.test_report_render_ui -v`
- generar `reports/real-report.html` y validar en `Bonos Locales` que en tarjetas de `Subfamilias`/`Taxonomía local` no aparezca `nan` (debe verse `-` cuando no hay dato)
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente en UI local:
  - en `Configuracion de reglas (avanzado)` cambiar selector entre `scoring/action/sizing`
  - `Recargar` trae el JSON correspondiente
  - `Guardar` persiste cambios validos y rechaza JSON invalido
- correr `python -m unittest tests.test_server.TestGetHealth -v`
- validar manualmente `GET /api-health` con token:
  - cada API incluye `checked_at`
  - el timestamp cambia entre chequeos consecutivos
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente `GET /config` con token y confirmar allowlist:
  - `scoring`
  - `action`
  - `sizing`
- validar manualmente en UI local:
  - el selector de `Configuracion de reglas` se carga desde backend al iniciar
  - si se agrega/quita item en allowlist de `server.py`, la UI refleja el cambio sin tocar HTML
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar baseline de scoring para confirmar que ranking/acciones no cambian tras el refactor interno de `_compute_base_scores_from_config`
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente `GET /config` con token y confirmar metadata por item:
  - `filename`
  - `exists`
  - `modified_at`
- validar manualmente en la app local:
  - al cambiar entre `scoring/action/sizing`, el panel muestra metadatos del archivo seleccionado
  - si el archivo no existe, `Existe: no` y `Modificado: -`
- validar manualmente en la app local (editor avanzado):
  - sin cambios: muestra `Sin cambios pendientes.` y `Guardar` deshabilitado
  - con cambios y JSON valido: muestra `Cambios pendientes de guardar.` y `Guardar` habilitado
  - con JSON invalido: muestra `Cambios pendientes (JSON invalido).` y `Guardar` deshabilitado
- validar manualmente `Formatear JSON`:
  - con JSON valido: reindenta el contenido y mantiene estado de cambios
  - con JSON invalido: muestra alerta `No se pudo formatear: JSON invalido.`
- validar manualmente atajo de guardado:
  - foco en editor + `Ctrl+S` (o `Cmd+S` en macOS) con JSON valido => guarda
  - con `Guardar` deshabilitado (sin cambios o JSON invalido) no dispara guardado
- validar manualmente `Revertir cambios`:
  - editar contenido sin guardar y usar `Revertir cambios` => vuelve al ultimo estado cargado
  - tras revertir, `Guardar` queda deshabilitado y estado vuelve a `Sin cambios pendientes.`
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente guardado de configuracion:
  - guardar un cambio en `scoring/action/sizing`
  - verificar creacion de backup en `data/backups/config/YYYY-MM-DD/`
  - confirmar que la app muestra en pantalla la ruta `Backup: ...` luego del guardado exitoso
- validar manualmente cambios sin guardar:
  - editar JSON y recargar/cerrar pestaña
  - el navegador debe advertir que hay cambios pendientes
- validar manualmente post-guardado:
  - guardar cambios en cualquier archivo de reglas
  - confirmar que `Modificado` se actualiza inmediatamente en la metadata mostrada
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente backups por API:
  - guardar al menos un cambio en `scoring/action/sizing`
  - consultar `GET /config/<name>/backups` y verificar lista con `path`, `filename`, `modified_at`, `size_bytes`
- validar manualmente en UI local:
  - cambiar entre `scoring/action/sizing` y verificar bloque `Backups recientes`
  - confirmar que muestra hasta 5 entradas con fecha, nombre y tamaño
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente restore por API:
  - guardar cambios para generar backups
  - restaurar con `POST /config/<name>/restore` enviando `backup_path` valido
  - verificar que el archivo objetivo vuelve al contenido del backup
- validar manualmente restore desde UI:
  - en `Backups recientes`, usar boton `Usar` para cargar un `backup_path`
  - ejecutar `Restaurar backup` y confirmar dialogo
  - verificar recarga de contenido y metadata del archivo restaurado
- correr `python -m unittest tests.test_server.TestScoringConfigEndpoints -v`
- validar manualmente por API:
  - `GET /config/scoring/backups?limit=5` => 200
  - `GET /config/scoring/backups?limit=0` => 422
  - `GET /config/scoring/backups?limit=101` => 422
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar baseline de scoring para confirmar que ranking/acciones no cambian tras el refactor interno de `_apply_absolute_metric_blends`
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar baseline de scoring para confirmar que ranking/acciones no cambian tras el refactor interno de `_apply_refuerzo_score`
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar baseline de scoring para confirmar que ranking/acciones no cambian tras el refactor interno de `_apply_reduccion_score`
- correr `python -m unittest tests.test_decision_scoring tests.test_pipeline -v`
- validar baseline de scoring para confirmar que ranking/acciones no cambian tras el refactor interno de `_apply_etf_effective_scores`
- validar manualmente en UI local:
  - cambiar `Ver` en backups recientes entre 1 y 20
  - confirmar que la lista se refresca con la nueva cantidad
- validar manualmente restore desde UI:
  - restaurar un backup y confirmar mensaje con:
    - `Origen: <backup usado>`
    - `Backup previo: <backup generado antes de restaurar>`

## Contexto

Este documento complementa `docs/improvement-roadmap.md` (foco dominio financiero) con foco producto/ingenieria y priorizacion por robustez operativa.

## Archivo objetivo

- `docs/product-roadmap.md`

---

## Roadmap por 19 dimensiones

### 1) Funcionalidad

Estado: pipeline completo y funcional; flujo principal cubierto.

Hallazgos:

- validaciones de entrada y errores de spawn ya cubiertos en `/run`.

Roadmap:

- P1: `POST /cancel` para terminar proceso y limpiar estado. (completado)
- P1: Detectar PID file huerfano al arrancar y marcar `interrupted`. (completado)
- P2: Validar `aporte_externo_ars >= 0` en Pydantic. (completado)
- P2: Manejar excepcion de `Popen` con 500 claro. (completado)

### 2) UX / Experiencia

Estado: UX funcional con presets, confirmacion y polling.

Hallazgos:

- Error truncado a 300 chars sin acceso directo a log completo.
- Sin historial persistente de corridas.
- Campo de aporte externo sin ayuda contextual.
- Sin progreso detallado.

Roadmap:

- P1: Boton "Cancelar corrida" cuando `running`. (completado)
- P1: Boton "Ver log completo" en error apuntando a `/status/detail`. (completado)
- P2: Panel de corridas recientes (ultimas 5). (completado)
- P2: Tooltip para "Aporte externo ARS". (completado)
- P3: Barra de progreso estimada. (completado)

### 3) UI / Interfaz

Estado: UI limpia y autocontenida, responsive basico.

Hallazgos:

- Estados solo con emojis (accesibilidad limitada).
- Panel de estado con poco contexto.

Roadmap:

- P2: Modal custom para confirmacion. (completado)
- P2: Texto/ARIA junto a indicadores de estado. (completado)
- P2: Seccion de reportes anteriores (`/reports/`). (completado)
- P3: Indicador de progreso animado. (completado)

### 4) Arquitectura

Estado: capas separadas, sin ciclos; server aislado del pipeline.

Hallazgos:

- `src/decision/scoring.py` mantiene alta complejidad.
- Orquestador principal del real run sigue denso (aunque ya split por modulos de apoyo).
- Faltan contratos formales por `Protocol`.

Roadmap:

- P2: Partir `apply_base_scores` en sub-funciones tematicas. (completado)
- P2: Extraer `_comentario_operativo` de sizing. (completado)
- P3: Formalizar interfaces con `typing.Protocol`. (completado)

### 5) Calidad de codigo

Estado: base clara y consistente, con baja deuda accidental.

Hallazgos:

- Funciones extensas en scoring/sizing.
- Type hints aun heterogeneos en algunos puntos.

Roadmap:

- P2: Centralizar utilidades comunes en `src/common/`. (completado)
- P2: Refactor de funciones largas. (completado)
- P3: Completar type hints donde queden `object` genericos. (completado)

### 6) Testing

Estado: CI activa, 47 archivos de tests y cobertura global 84% (floor 82%).

Hallazgos:

- `src/decision/sizing.py`: 67%.
- `src/clients/bcra.py`: 60%.
- `src/clients/bonistas_client.py`: 62%.
- Sin pruebas de concurrencia para `/run`.

Roadmap:

- P1: Llevar sizing y bcra a >=82%. (completado)
- P1: Subir floor de CI de 82% a 85%. (completado)
- P2: Smoke de scripts Bash en Unix. (completado)
- P3: Test concurrente: segundo `/run` devuelve 409. (completado)

### 7) Seguridad

Estado: entorno local (`127.0.0.1`) y password no persistida en navegador.

Hallazgos:

- Autenticacion por token de sesion ya aplicada en endpoints operativos; resta evolucionar hardening (scope/expiracion/rate-limit por endpoint).
- Sin TLS (mitigado por localhost).
- Sin rate limiting en `POST /run`.

Roadmap:

- P1: Auditar que nunca se impriman credenciales. (completado)
- P1: Filtrar `log_tail` para secretos. (completado)
- P2: Token de sesion simple para `/run`. (completado)
- P2: Limitar largo de `username/password`. (completado)
- P3: Rate limiting de `/run` (3/min). (completado)

### 8) Performance

Estado: retry robusto en Finviz; caches parciales.

Hallazgos:

- Sin tiempo estimado expuesto al usuario.
- Sin cache intradia de precios.

Roadmap:

- P1: Retry con backoff para IOL y BCRA. (completado)
- P2: Exponer `elapsed_seconds`. (completado)
- P3: Cache intradia TTL 15 min. (completado)

### 9) Datos / Persistencia

Estado: CSV/JSON versionados por fecha; sin BD.

Hallazgos:

- Montos monetarios en `float`.
- Sin backup automatico de `data/runtime/`.
- Historial crece sin purga automatica.

Roadmap:

- P1: Backup diario de CSV runtime. (completado)
- P2: Migrar montos criticos a `Decimal`. (completado)
- P2: Retencion configurable (default 90 dias). (completado)
- P3: Validacion de integridad al arranque. (completado)

### 10) DevOps e Infra

Estado: GitHub Actions y distribucion ZIP vigente.

Hallazgos:

- Sin release automation end-to-end.
- Sin Docker para entorno dev/test.
- Cobertura de OS aun centrada en Linux CI.

Roadmap:

- P1: Script de release (version + tag + build). (completado)
- P2: Agregar `macos-latest` a matriz CI. (completado)
- P3: Dockerfile para dev/testing. (completado)

### 11) Mantenibilidad

Estado: modularidad razonable y documentacion operativa.

Hallazgos:

- Sin ADR formales.
- `apply_base_scores` sigue como punto caliente.
- Sin `CONTRIBUTING.md`.

Roadmap:

- P2: Crear `docs/decisions/` con ADRs base. (completado)
- P2: Crear `CONTRIBUTING.md`. (completado)
- P2: Refactor `apply_base_scores`. (completado)

### 12) Escalabilidad

Estado: diseno single-user, objetivo personal.

Hallazgos:

- Historiales sin limite de crecimiento.
- Onboarding de nuevos instrumentos con varios puntos manuales.
- Faltan abstracciones para nuevas APIs.

Roadmap:

- P2: Retencion configurable de historiales. (completado)
- P2: Checklist formal para alta de instrumento. (completado)
- P3: Protocol de clientes externos. (completado)

### 13) Accesibilidad

Estado: labels basicos presentes.

Hallazgos:

- Indicadores por emoji sin texto equivalente.
- Sin `aria-live` en estado.
- Sin `role="alert"` en errores.
- Tablas del reporte con oportunidades semanticas.

Roadmap:

- P2: `aria-label` para estado. (completado)
- P2: `aria-live="polite"` en panel. (completado)
- P2: `role="alert"` en errores. (completado)
- P3: auditoria WCAG de contraste. (completado)

### 14) Compatibilidad

Estado: Windows cubierto; macOS/Linux parcial.

Hallazgos:

- Flujo operativo principal ya puede ejecutarse tanto con Bash como con `pwsh`.
- Scripts Bash base y wrappers PowerShell cross-platform ya implementados.
- Sin matriz formal de navegadores soportados.

Roadmap:

- P1: Fase 1 cross-platform (scripts Bash). (completado)
- P2: Fase 2 con `pwsh` cross-platform. (completado)
- P3: pruebas mobile/responsive del reporte. (completado)

### 15) Observabilidad

Estado: logging plano + `/status/detail`.

Hallazgos:

- Sin logging estructurado JSON opcional.
- `log_tail` corto para fallas largas.
- Sin metricas por fase ni notificaciones de fin de corrida.

Roadmap:

- P1: ampliar `log_tail` a 3000 + `log_lines`. (completado)
- P2: tiempos por fase en pipeline. (completado)
- P2: `LOG_FORMAT=json` opcional. (completado)
- P3: webhook on-completion. (completado)

### 16) Documentacion

Estado: README y guias base existentes.

Hallazgos:

- Falta referenciar mas explicitamente docs de API FastAPI.
- Sin ADRs ni guia de contribucion.
- Roadmaps tecnicos existen pero parte sigue sin implementacion.

Roadmap:

- P1: Referenciar `/docs` y `/openapi.json` en README. (completado)
- P2: `CONTRIBUTING.md`. (completado)
- P2: ADRs minimos. (completado)
- P3: diagrama Mermaid de arquitectura. (completado)

### 17) Integraciones

Estado: multiples APIs externas con fallback a snapshots.

Hallazgos:

- Retry completo concentrado en Finviz.
- Sin circuit breaker por proveedor.
- Sin endpoint de salud de integraciones.

Roadmap:

- P1: `_call_with_retry()` en IOL y BCRA. (completado)
- P2: circuit breaker simple por API. (completado)
- P3: `GET /api-health`. (completado)

### 18) Usabilidad operativa

Estado: operacion con scripts y UI simple.

Hallazgos:

- Sin gestion de reportes previos desde UI.
- Config de scoring solo por edicion manual de JSON.
- Sin scheduler para corrida periodica.

Roadmap:

- P2: Panel de reportes en UI. (completado)
- P3: scheduler opcional. (completado)
- P3: pagina de configuracion basica en UI. (completado)

### 19) Validacion estadistica y madurez de senales

Estado: dimension agregada para gobernar la evolucion del predictor segun volumen historico real.

Hallazgos:

- Varias capacidades avanzadas requieren umbrales minimos de historia para evitar sobreajuste o falsas conclusiones.
- Hoy no hay una visibilidad integrada de calidad historica de senales en reporte/decision.

Roadmap:

- P1 (prerequisitos desbloqueantes):
  - Documentar umbral minimo de corridas por capacidad avanzada:
    - 10 para racha
    - 20 para `serie_confiable`
    - 30 por familia para calibracion
  - Retirar fallback legacy una vez superada esa ventana.
- P2 (cuando haya historia suficiente):
  - Validar metricas de riesgo historicas contra benchmark externo cuando `serie_confiable` se active.
  - Mostrar quality label (`Robusta` / `Parcial` / `Corta` / `Sin historia`) en la tabla de decision del reporte.
  - Agregar seccion de metricas de acierto del predictor en HTML (`%` global y `%` por familia).
  - Revisar thresholds de scoring contra outcomes reales acumulados.
  - Incorporar tablero de evolucion de racha por ticker para distinguir convicciones solidas de senales oscilantes.
- P3 (con volumen estadistico validado):
  - Calibracion por `asset_family` (>=30 outcomes por familia x senal).
  - Multi-horizonte en predictor.
  - Clasificador sobre `signal_votes` como opcion B.

---

## Plan de fases

### v0.3 - Robustez y seguridad (P1)

1. `POST /cancel` + boton UI.
2. Deteccion de PID huerfano al iniciar.
3. Auditoria/filtrado de credenciales en logs.
4. Retry en IOL y BCRA (patron Finviz).
5. Subir cobertura de `sizing.py` y `bcra.py` a >=82%.
6. Backup automatico de `data/runtime/`.
7. Scripts Bash Fase 1 (cross-platform).

Estado v0.3 (P1) al 2026-04-28:

- Completado: item 1.
- Completado: item 2.
- Completado: item 3.
- Completado: item 4.
- Completado: item 5.
- Completado: item 6.
- Completado: item 7.
- Pendiente: sin pendientes P1.

Cierre ejecutivo v0.3:

- Se estabilizo la operacion base del server local: cancelacion, recuperacion de huerfanos y manejo explicito de errores de spawn.
- Se reforzo la capa de integraciones criticas con retry en IOL/BCRA y backup automatico de runtime.
- Se llevo la base a un piso de robustez verificable con cobertura minima reforzada y scripts operativos cross-platform iniciales.

### v0.4 - UX, calidad y observabilidad (P2)

1. Modal custom de confirmacion.
2. Panel de reportes anteriores.
3. Centralizar utilidades comunes en `src/common/`.
4. Refactor `apply_base_scores`.
5. Token de sesion para `/run`.
6. Logs estructurados opcionales.
7. `log_tail` ampliado + tiempos por fase.
8. ADRs iniciales.

Estado v0.4 (P2) al 2026-05-01:

- Completado: item 1.
- Completado: item 2.
- Completado: item 3.
- Completado: item 4.
- Completado: item 5.
- Completado: item 6.
- Completado: item 7.
- Completado: item 8.
- Pendiente: sin pendientes P2.

Cierre ejecutivo v0.4:

- La UX de corrida quedo madura: confirmacion custom, progreso visible, reportes previos, corridas recientes y errores accionables.
- La mantenibilidad subio de forma material: utilidades comunes, ADRs, CONTRIBUTING y refactors relevantes en scoring/sizing.
- La observabilidad y seguridad operativa quedaron alineadas con uso real: token de sesion, logs mas ricos y diagnostico trazable.

### v0.5 - Escalabilidad y polish (P3)

1. Rate limiting en `/run`.
2. Cache intradia de precios.
3. Circuit breakers de APIs.
4. Diagrama de arquitectura.
5. Scheduler opcional.
6. Cierre de deuda documental remanente.

Estado v0.5 (P3) al 2026-05-01:

- Completado: item 1.
- Completado: item 2.
- Completado: item 3.
- Completado: item 4.
- Completado: item 5.
- Completado: item 6.
- Pendiente: sin pendientes P3.

Cierre ejecutivo v0.5:

- Se agrego polish operativo y de escala local: rate limiting, cache intradia, circuit breakers y scheduler opcional.
- El reporte y la documentacion quedaron cerrados con diagrama de arquitectura, auditoria de contraste y validacion responsive estructural.
- La app quedo lista para distribucion con una superficie mas estable para evolucion futura sin arrastrar deuda abierta del roadmap.

---

## Resumen ejecutivo consolidado

- `v0.3` resolvio robustez de base y seguridad operativa minima.
- `v0.4` convirtio la app local en una herramienta mucho mas utilizable, mantenible y observable.
- `v0.5` termino el polish de escalabilidad local, compatibilidad y cierre documental.
- Resultado final:
  - server local endurecido
  - pipeline y scoring mas mantenibles
  - UI operativa con configuracion avanzada
  - reporte HTML mas accesible y portable
  - distribucion ZIP lista para usuarios finales
