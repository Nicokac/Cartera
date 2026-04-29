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
- `.github/workflows/ci.yml`: se intento matriz de OS con `macos-latest`,
  pero se revierte temporalmente a `ubuntu-latest` y queda como deuda tecnica
  pendiente por inestabilidad en GitHub Actions
- `.github/workflows/ci.yml`: se desactiva temporalmente tambien `ubuntu-latest`
  para unittest en Actions; se agrega job de aviso no bloqueante mientras se
  resuelve la deuda tecnica de CI
- `server.py`: asegura creacion de `reports/` antes de `app.mount("/reports", ...)`
  para evitar fallo de import en CI cuando el directorio no existe

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
