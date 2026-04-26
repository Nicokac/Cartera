# Tests

Esta carpeta contiene tests deterministas para la logica extraida a `src/` y para los runners de reporte.

## Ejecucion

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Suites utiles:

```powershell
python -m unittest tests.test_pipeline -v
python -m unittest tests.test_smoke_run -v
python -m unittest tests.test_smoke_output -v
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_technical -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_decision_history -v
python -m unittest tests.test_prediction_store -v
python -m unittest tests.test_prediction_predictor -v
python -m unittest tests.test_prediction_verifier -v
python -m unittest tests.test_prediction_calibration -v
python -m unittest tests.test_prediction_cycle -v
python -m unittest tests.test_operations -v
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

## CI actual

- workflow: `.github/workflows/ci.yml`
- bootstrap automatico de configuracion de ejemplo antes de correr tests
- ese bootstrap no intenta reconstruir todos los mappings versionados:
  - solo completa archivos con `.json.example`
  - principalmente `data/strategy/*.json` y contratos opcionales de soporte
- suites incluidas:
  - `tests.test_bond_analytics`
  - `tests.test_bonistas_client`
  - `tests.test_classify`
  - `tests.test_config`
  - `tests.test_dashboard`
  - `tests.test_pipeline`
  - `tests.test_smoke_run`
  - `tests.test_smoke_output`
  - `tests.test_strategy_rules`
  - `tests.test_technical`
  - `tests.test_sizing`
  - `tests.test_decision_history`
  - `tests.test_prediction_store`
  - `tests.test_prediction_predictor`
  - `tests.test_prediction_verifier`
  - `tests.test_prediction_calibration`
  - `tests.test_prediction_cycle`
  - `tests.test_operations`
  - `tests.test_report_primitives`
  - `tests.test_report_operations`
  - `tests.test_report_render`
  - `tests.test_generate_real_report`
  - `tests.test_iol_client`
  - `tests.test_argentinadatos_client`
  - `tests.test_liquidity`
  - `tests.test_market_data_client`
  - `tests.test_finviz_client`
  - `tests.test_bcra_client`
  - `tests.test_fred_client`
  - `tests.test_numeric_utils`
  - `tests.test_pyobd_client`
  - `tests.test_valuation_and_checks`

Suites locales adicionales (no bloqueantes de CI por ahora):

- `tests.test_generate_real_report_split_cli`
- `tests.test_generate_real_report_split_runtime`
- `tests.test_generate_real_report_split_snapshots`
- `tests.test_generate_real_report_split_bonistas`
- `tests.test_report_sections_prediction`

## Cobertura actual

- cartera y valuacion
- smoke pipeline y salida formateada
- liquidez y sizing
- scoring, acciones y memoria temporal
- persistencia base del motor de prediccion direccional
- configuracion base del motor de prediccion direccional
- predictor base del motor de prediccion direccional
- guardrails de escala para `score_unificado` dentro del predictor
- verificacion base del motor de prediccion direccional
- calibracion base del motor de prediccion direccional
- runner de mantenimiento del motor de prediccion direccional
- operaciones y snapshots
- render HTML
- clientes principales y secundarios
- validacion de runners sin APIs vivas

## Snapshots

Los snapshots de referencia viven en:

- [tests/snapshots/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\tests\snapshots\README.md)
