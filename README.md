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
- el runner real puede pedir credenciales por terminal si no estan cargadas

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
Health check: `http://127.0.0.1:8000/health`.

Comandos de operacion local:

```powershell
.\scripts\status_local_app.ps1
.\scripts\stop_local_app.ps1
.\scripts\smoke_local_app.ps1
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
python -m unittest tests.test_report_render -v
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

## Estado de deuda tecnica

Pendientes reales abiertos:

- retirar el fallback legacy cuando `data/snapshots/` tenga una ventana operativa suficiente
- calibracion por `asset_family` en prediccion (bloqueada por datos: requiere >= 30 outcomes verificados por familia x senal)
- `tests/test_strategy_rules.py` sigue como outlier de tamano y candidato a split
- monitorear crecimiento de `tests/test_report_render_operations.py` y `tests/test_generate_real_report_split_runtime.py`

Frentes ya cerrados recientemente:

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
