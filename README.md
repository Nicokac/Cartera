# Cartera de Activos

Motor de analisis de cartera para IOL con foco en:

- consolidacion y valuacion de cartera
- scoring operativo para CEDEARs, acciones locales, bonos y liquidez
- overlay tecnico y contexto macro
- memoria temporal diaria entre corridas
- reporte HTML reproducible para smoke y real run

## Estado del proyecto

El repo esta en una etapa operativa estable:

- pipeline canonico concentrado en `src/`
- renderer HTML modularizado en:
  - `report_renderer`
  - `report_composer`
  - `report_layout`
  - `report_sections`
  - `report_decision`
  - `report_primitives`
  - `report_operations`
- runner real modularizado en:
  - `generate_real_report` (orquestacion)
  - `generate_real_report_cli`
  - `generate_real_report_runtime`
  - `generate_real_report_snapshots`
  - `generate_real_report_bonistas`
- metricas historicas de riesgo por posicion y portfolio (`analytics/portfolio_risk.py`) con metodologia de universo comparable y circuit breaker `serie_confiable`
- flujo de operaciones reales integrado al reporte
- snapshots operativos movidos a `data/snapshots/` con fallback legacy controlado
- capa experimental de prediccion direccional integrada al smoke y al real run
- CI basada en `unittest` con suites estables declaradas en `.github/workflows/ci.yml`

Resumen funcional vigente:

- [baseline-actual.md](docs/baseline-actual.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

## Estructura

- `src/`: logica canonica del motor
- `scripts/`: runners, renderer y utilitarios de soporte
- `data/`: snapshots, referencias y ejemplos de configuracion
- `docs/`: documentacion activa
- `docs/archive/`: historico y material absorbido
- `tests/`: suite de regresion y fixtures
- `reports/`: HTMLs generados
- `static/`: frontend del servidor web local
- `server.py`: servidor web local (FastAPI)
- `dist/`: distribuibles generados (excluido de git; ver `scripts/build_dist.ps1`)

## Requisitos

- Python `3.12`
- acceso de red para corridas reales
- credenciales validas de IOL para el flujo real

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Setup rapido (recomendado para testers):

```powershell
.\scripts\setup_local_app.ps1
```

Instalacion alternativa desde metadata del proyecto:

```powershell
pip install .
```

Extra opcional para herramientas BYMA:

```powershell
pip install .[byma]
```

## Clone limpio

El repo mezcla dos politicas de configuracion:

- algunos mappings canonicos de `data/mappings/` si se versionan
- los JSON de `data/strategy/` y los ejemplos de soporte siguen entrando por bootstrap

Politica vigente:

- `data/examples/` no busca espejar `data/mappings/` de forma 1:1
- `data/examples/` existe para bootstrap y para documentar el contrato minimo de archivos no versionados o personalizables
- si un mapping canonico ya vive versionado en git, no necesita tener `.json.example` por simetria

Para bootstrap minimo en un clone limpio:

```powershell
python scripts\bootstrap_example_config.py
```

Eso copia los `.json.example` de `data/examples/` a sus rutas reales si todavia no existen.

En la practica hoy se usa para crear:

- `data/strategy/*.json`
- cualquier mapping opcional que no venga ya versionado en el repo

Mas detalle:

- [data/examples/README.md](data/examples/README.md)

## Variables de entorno

```env
IOL_USERNAME=tu_usuario_iol@example.com
IOL_PASSWORD=tu_password_iol
FRED_API_KEY=tu_fred_api_key
ENABLE_LEGACY_SNAPSHOTS=1
```

Notas:

- `ENABLE_LEGACY_SNAPSHOTS=0` fuerza el uso exclusivo de `data/snapshots/`
- `LOG_FORMAT=json` habilita logs estructurados JSON en el runner real
- el runner real puede pedir credenciales por terminal si no estan cargadas
- en la app local, el password IOL no se persiste; solo puede recordarse el usuario en el navegador

## Distribucion para usuarios finales

Para generar el zip distribuible (`dist/cartera-v0.2.0-win64.zip`):

```powershell
.\scripts\build_dist.ps1
```

El zip incluye Python 3.12 embeddable y todas las dependencias pre-instaladas.
No requiere Python instalado en la maquina del usuario final.

Contenido del zip:

- `Iniciar Cartera.bat`: doble clic para arrancar la app y abrir el browser
- `Detener Cartera.bat`: detiene la app
- `LEEME.txt`: instrucciones para usuarios no tecnicos
- `app/`: codigo fuente, Python embeddable y dependencias

Estrategia de actualizacion: el zip no incluye `data/runtime/`, `reports/` ni
`data/strategy/`, por lo que esos datos sobreviven al extraer el nuevo zip con
"reemplazar todo". El usuario solo tiene que pedir el zip nuevo a Nicolas Kachuk.

Nota: el primer build descarga Python embeddable y todas las dependencias (~5-10 min).
Las corridas siguientes reutilizan el cache en `dist/_cache/`.

## Uso rapido

Servidor web local:

```powershell
.\scripts\run_local_app.ps1
```

Menu interactivo local (start/status/stop/logs/open browser). Alternativa directa:

```powershell
.\scripts\start_local_app.ps1
```

Abre `http://127.0.0.1:8000` en el browser. El formulario permite lanzar el pipeline real
con parametros y ver el estado en tiempo real. El reporte generado queda disponible en
`http://127.0.0.1:8000/reports/real-report.html`.
Flujo del formulario local:

- solicita `Usuario IOL` y `Password IOL` para cada corrida
- permite marcar `Recordar solo usuario` (sin persistir password)
- expone presets de fondeo:
  - `Solo liquidez IOL` (`use_iol_liquidity=true`, `aporte_externo_ars=0`)
  - `Aporte externo` (`use_iol_liquidity=false`, `aporte_externo_ars` editable)
- muestra un dialogo de confirmacion antes de ejecutar con usuario y resumen de fondeo
- muestra boton `Cancelar corrida` mientras el estado esta en `running`
- si se cancela una corrida, el estado final pasa a `interrupted`
- si el servidor se reinicia durante una corrida, al volver a iniciar marca la corrida previa como `interrupted`
- muestra seccion `Reportes anteriores` con HTMLs disponibles en `reports/`

Health check: `http://127.0.0.1:8000/health`.
Estado detallado: `http://127.0.0.1:8000/status/detail`.
`/status/detail` filtra credenciales sensibles en `error` y `log_tail` (`IOL_USERNAME`, `IOL_PASSWORD`, `username`, `password`).
`/status/detail` expone `log_tail` ampliado, `log_lines` y `elapsed_seconds` para diagnostico rapido.
`POST /run` requiere token de sesion en header `X-Session-Token` (la UI lo obtiene automaticamente via `GET /session`).
`POST /run` valida `aporte_externo_ars >= 0` y limita `username/password` a 200 caracteres.

Comandos de operacion local:

```powershell
.\scripts\status_local_app.ps1
.\scripts\status_local_app.ps1 -Detailed
.\scripts\stop_local_app.ps1
.\scripts\smoke_local_app.ps1
```

Equivalentes Bash (macOS/Linux):

```bash
./scripts/setup_local_app.sh
./scripts/start_local_app.sh --bind-host 127.0.0.1 --port 8000
./scripts/status_local_app.sh --detailed
./scripts/stop_local_app.sh
./scripts/smoke_local_app.sh
./scripts/run_local_app.sh
```

Modo manual equivalente (primer plano):

```powershell
python server.py
```

Smoke report:

```powershell
python scripts\generate_smoke_report.py
```

Validacion smoke interna:

```powershell
python scripts\smoke_run.py
```

Real run:

```powershell
python scripts\generate_real_report.py
```

Backup runtime automatico:

- cada corrida real genera backup diario de `data/runtime/*.csv` en `data/backups/YYYY-MM-DD/`
- incluye historiales operativos (`decision_history.csv`, `prediction_history.csv`) cuando existan
- el log de corrida (`data/runtime/server_run.log`) ahora incluye duracion por fase
  con lineas `Fase <nombre>: <seg>s` para diagnostico de performance

Real run no interactivo:

```powershell
python scripts\generate_real_report.py `
  --username tu_usuario_iol@example.com `
  --password tu_password_iol `
  --no-use-iol-liquidity `
  --aporte-externo-ars 600000 `
  --non-interactive
```

## Tests

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Suites utiles:

```powershell
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_technical -v
python -m unittest tests.test_report_primitives -v
python -m unittest tests.test_report_operations -v
python -m unittest tests.test_report_render_core -v
python -m unittest tests.test_report_render_operations -v
python -m unittest tests.test_report_render_ui -v
python -m unittest tests.test_generate_real_report -v
python -m unittest tests.test_generate_real_report_split_cli -v
python -m unittest tests.test_generate_real_report_split_runtime -v
python -m unittest tests.test_generate_real_report_split_snapshots -v
python -m unittest tests.test_generate_real_report_split_bonistas -v
python -m unittest tests.test_report_sections_prediction -v
```

CI actual:

- workflow: `.github/workflows/ci.yml`
- bootstrap automatico de configuracion de ejemplo antes de testear
- bateria estable del repo sin red real ni credenciales
- coverage minima exigida en CI sobre la suite estable actual: `82%`
- target de mediano plazo: `90%`

## Versionado

- esquema: SemVer (`MAJOR.MINOR.PATCH`)
- fuente de verdad de version de paquete: `pyproject.toml` (`[project].version`)
- historial de cambios: [CHANGELOG.md](CHANGELOG.md)
- recomendacion de release:
  1. actualizar `CHANGELOG.md` y version en `pyproject.toml`
  2. mergear a `main`
  3. crear tag `vX.Y.Z`

## Estado de deuda tecnica

Pendientes reales abiertos:

- retirar el fallback legacy cuando `data/snapshots/` tenga una ventana operativa suficiente
- calibracion por `asset_family` en prediccion (bloqueada por datos: requiere >= 30 outcomes verificados por familia x senal)
- monitorear crecimiento de `tests/test_report_render_operations.py` y `tests/test_generate_real_report_split_runtime.py`

Frentes ya cerrados recientemente:

- distribuible win64 para usuarios finales: `scripts/build_dist.ps1`, bat files y estrategia de updates sin romper datos
- endpoint `/version` y footer de version en UI con mensaje de contacto para updates
- `report_renderer.py` ya quedo como orquestador puro
- `rank_score` ya tiene tests de borde explicitos para cohorts `N=3` y `N=4`
- snapshots previos ahora validan filas utilizables de `Ticker_IOL` y coercion numerica defensiva
- el ciclo operativo entre `generate_real_report.py` y `run_prediction_cycle.py` ya quedo documentado
- `analytics/portfolio_risk.py`: metricas historicas por posicion y portfolio con universo comparable y `serie_confiable`
- `_build_risk_focus_block` extraida de `build_summary_section` al nivel de modulo en `report_sections.py`
- `test_decision_actions.py`: 19 tests sobre `assign_base_action`, `assign_action_v2` y `enrich_decision_explanations`
- `test_decision_scoring.py`: 28 tests sobre helpers y smoke de `apply_base_scores`
- `test_portfolio_risk.py`: 7 tests sobre el modulo de riesgo historico
- `test_report_sections.py`: 8 tests sobre `_build_risk_focus_block`
- artefactos generados fuera de versionado: `.coverage*`, `htmlcov/` y `reports/*.html`
- suite split de real run en modulos: `split_cli`, `split_runtime`, `split_snapshots`, `split_bonistas`
- O-018 cerrado: `test_strategy_rules.py` se splitteo por dominio (`strategy_rules_fundamentals`, `strategy_rules_technical_scoring`, `strategy_rules_taxonomy`, `strategy_rules_narrative`, `strategy_rules_market_regime`) y `tests/test_strategy_rules.py` queda como wrapper de carga

## Memoria temporal

- historial diario en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha_efectiva_de_mercado`
- reruns del mismo dia reemplazan la observacion
- corridas de fin de semana o preapertura no inflan persistencia artificial
- el HTML expone:
  - `Accion previa`
  - `Delta Score`
  - `Racha`

## Documentacion

Entrada canonica:

- [docs/README.md](docs/README.md)
- [docs/repo-cleanup-map.md](docs/repo-cleanup-map.md)
- [docs/tester-guide.md](docs/tester-guide.md)
- [CHANGELOG.md](CHANGELOG.md)

Configuracion de ejemplo:

- [data/examples/README.md](data/examples/README.md)

Track de prediccion direccional:

- [docs/prediction-engine-roadmap.md](docs/prediction-engine-roadmap.md)
- [docs/prediction-engine-history.md](docs/prediction-engine-history.md)

Estado actual del track:

- Fase 1 cerrada: store local de predicciones en `src/prediction/store.py`
- Fase 2 cerrada: pesos y umbrales canonicos en `data/mappings/prediction_weights.json`
- Fase 3 cerrada: predictor heuristico en `src/prediction/predictor.py`
- Fase 4 cerrada: verificador de outcomes en `src/prediction/verifier.py`
- Fase 5 cerrada: calibracion de pesos en `src/prediction/calibration.py`
- Fase 6 cerrada: integracion experimental al pipeline, renderer y runner `scripts/run_prediction_cycle.py`
- Fase 6.1 cerrada: correccion de escala de `score_unificado` en el predictor para alinear votos con la salida real del scoring
- Fase 6.2 cerrada: zona muerta en votos continuos, RSI continuo, `IC <= 0` apaga senal
- Fase 6.3 cerrada: calibracion rolling con fallback al historico completo
- Fase 7 cerrada: ADX continuo y `relative_volume` continua incorporados; hardening de `sma_trend` y `conviction_label`

Ciclo operativo actual de prediccion:

1. `python scripts\generate_real_report.py`
   - genera predicciones nuevas para la corrida actual
   - persiste la observacion nueva en `data/runtime/prediction_history.csv`
   - renderiza la seccion `Prediccion` en el HTML
2. `python scripts\run_prediction_cycle.py`
   - no genera predicciones nuevas
   - verifica outcomes ya vencidos en el historial
   - recalibra `data/mappings/prediction_weights.json` si hay muestra suficiente

Regla practica:

- `generate_real_report.py` = alta de observaciones nuevas
- `run_prediction_cycle.py` = mantenimiento historico del track
- si solo corres `run_prediction_cycle.py`, el historial se mantiene pero no crece
- el smoke puede validar la integracion, pero la persistencia operativa real se consolida en el real run

Comandos utiles del track:

```powershell
python -m unittest tests.test_prediction_store tests.test_prediction_predictor tests.test_prediction_verifier tests.test_prediction_calibration tests.test_prediction_cycle -v
python scripts\run_prediction_cycle.py
```
