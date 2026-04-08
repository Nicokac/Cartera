# Taxonomía de Activos

## Objetivo

Definir la taxonomía canónica que usa el motor para scoring, acciones y sizing.

## Familias vigentes

### `stock`

Subfamilias:

- `stock_growth`
- `stock_defensive_dividend`
- `stock_commodity`
- `stock_argentina`

### `etf`

Subfamilias:

- `etf_core`
- `etf_sector`
- `etf_country_region`

### `bond`

Subfamilias:

- `bond_sov_ar`
- `bond_cer`
- `bond_bopreal`
- `bond_other`

### `liquidity`

Subfamilia:

- `liquidity_other`

## Lectura actual

- `stock_growth` quedó más exigente para `Refuerzo`
- `stock_commodity` tiene un freno técnico extra cuando `Tech_Trend = Mixta`
- `etf_sector` sigue siendo la subfamilia ETF con más tolerancia a `Refuerzo`
- `etf_country_region` requiere más soporte para dejar neutralidad
- `bond_sov_ar` sigue en monitoreo/rebalanceo, sin `Refuerzo` automático

## Casos de referencia

- `GOOGL`: `stock_growth`, hoy `Mantener / Neutral`
- `NEM`: `stock_commodity`, hoy `Refuerzo`
- `XLU` y `XLV`: `etf_sector`, hoy `Refuerzo`
- `GD30`: `bond_sov_ar`, hoy `Rebalancear / tomar ganancia`

## Fuente efectiva

La taxonomía efectiva vive en:

- `src/decision/scoring.py`
- `data/strategy/scoring_rules.json`
- `data/strategy/action_rules.json`
