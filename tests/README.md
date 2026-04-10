# Tests

Esta carpeta contiene tests deterministas para la logica extraida a `src/`.

## Ejecucion

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Suites utiles:

```powershell
python -m unittest tests.test_pipeline -v
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_decision_history -v
python -m unittest tests.test_report_render -v
python -m unittest tests.test_generate_real_report -v
```

CI actual:

- workflow: `.github/workflows/ci.yml`
- suites incluidas:
  - `tests.test_bond_analytics`
  - `tests.test_bonistas_client`
  - `tests.test_classify`
  - `tests.test_config`
  - `tests.test_dashboard`
  - `tests.test_pipeline`
  - `tests.test_strategy_rules`
  - `tests.test_sizing`
  - `tests.test_decision_history`
  - `tests.test_report_render`
  - `tests.test_generate_real_report`
  - `tests.test_liquidity`
  - `tests.test_numeric_utils`
  - `tests.test_iol_client`
  - `tests.test_argentinadatos_client`
  - `tests.test_market_data_client`
  - `tests.test_finviz_client`
  - `tests.test_bcra_client`
  - `tests.test_fred_client`
  - `tests.test_pyobd_client`
  - `tests.test_valuation_and_checks`

## Cobertura actual

- cartera y valuacion
- liquidez y sizing
- scoring, acciones y memoria temporal
- render HTML
- clientes principales
- clientes secundarios
- smoke pipeline sin APIs vivas

## Snapshots

Los snapshots de referencia viven en:

- [tests/snapshots/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\tests\snapshots\README.md)
