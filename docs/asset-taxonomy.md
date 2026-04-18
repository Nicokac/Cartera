# Taxonomia de Activos

## Objetivo

Definir la taxonomia canonica que usa el motor para scoring, acciones y sizing.

## Familias vigentes

### `stock`

Subfamilias:

- `stock_growth`
- `stock_defensive_dividend`
- `stock_commodity`
- `stock_argentina`
- `stock_other`

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

## Lectura vigente

- `stock_growth` es la subfamilia de equity mas exigente para `Refuerzo`
- `stock_commodity` incorpora frenos tecnicos cuando el setup pierde calidad
- `etf_sector` sigue siendo la subfamilia ETF con mas tolerancia a `Refuerzo`
- `etf_country_region` necesita soporte adicional para salir de neutralidad
- `bond_sov_ar` sigue teniendo sesgo de monitoreo o rebalanceo, no de compra agresiva
- `liquidity_other` no debe contaminar lectura de conviccion de riesgo

## Casos de referencia

- `GOOGL`: `stock_growth`
- `NEM`: `stock_commodity`
- `XLU` y `XLV`: `etf_sector`
- `EEM`: `etf_country_region`
- `GD30`: `bond_sov_ar`
- `PAMP`: `stock_other`

## Fuente efectiva

La taxonomia efectiva vive en:

- `src/decision/scoring.py`
- `src/portfolio/classify.py`
- `data/strategy/scoring_rules.json`
- `data/strategy/action_rules.json`
- `data/mappings/bond_local_subfamily_rules.json`
