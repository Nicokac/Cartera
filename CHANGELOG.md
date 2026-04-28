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

### Testing

- cobertura de modulos clave de P1 validada con suites dirigidas:
  - `src/clients/bcra.py`: 82%
  - `src/decision/sizing.py`: 86%

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
