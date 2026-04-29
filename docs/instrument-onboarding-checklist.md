# Checklist de Alta de Instrumento

Guia operativa para incorporar un instrumento nuevo sin romper pipeline, scoring ni reporte.

## 1) Identificacion y taxonomia

- Definir `ticker` canonico IOL (`Ticker_IOL`).
- Definir familia y subfamilia objetivo (`asset_family` / `asset_subfamily`).
- Validar que la clasificacion no contradiga la taxonomia vigente en:
  - `docs/asset-taxonomy.md`
  - `data/mappings/instrument_profile_map.json`

## 2) Mappings minimos

- Revisar/actualizar `data/mappings/instrument_profile_map.json`:
  - alta del ticker con `asset_family` y `asset_subfamily`.
- Si aplica market data externa, revisar/actualizar:
  - `data/mappings/finviz_map.json`
  - `data/mappings/ratios.json`
  - `data/mappings/vn_factor_map.json`
  - `data/mappings/block_map.json`
- Si es bono local, revisar `data/mappings/bond_local_subfamily_rules.json`.

## 3) Reglas de estrategia

- Verificar impacto en:
  - `data/strategy/scoring_rules.json`
  - `data/strategy/action_rules.json`
  - `data/strategy/sizing_rules.json`
- Confirmar que no se generen acciones incoherentes (ejemplo: liquidez tratada como equity).

## 4) Validacion funcional

- Ejecutar una corrida smoke:
  - `python scripts/generate_smoke_report.py`
- Ejecutar una corrida real (si corresponde).
- Confirmar en reporte:
  - aparece en bloque correcto
  - scoring y accion son consistentes
  - no rompe tabla de integridad

## 5) Tests minimos sugeridos

- Ejecutar suites base:
  - `python -m unittest tests.test_pipeline -v`
  - `python -m unittest tests.test_strategy_rules -v`
  - `python -m unittest tests.test_report_sections -v`
- Si toca server/UI:
  - `python -m unittest tests.test_server -v`

## 6) Cierre documental

- Actualizar docs impactados:
  - `docs/asset-taxonomy.md` (si cambia taxonomia efectiva)
  - `docs/baseline-actual.md` (si cambia comportamiento visible)
  - `README.md` (si cambia operacion)
- Registrar en `CHANGELOG.md` (`Unreleased`).

