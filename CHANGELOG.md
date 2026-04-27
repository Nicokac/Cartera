# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y versionado [SemVer](https://semver.org/lang/es/).

## [Unreleased]

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
