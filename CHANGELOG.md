# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y versionado [SemVer](https://semver.org/lang/es/).

## [Unreleased]

### Added

- script `scripts/setup_local_app.ps1` para bootstrap rapido de entorno local
- guia de tester en `docs/tester-guide.md`

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
