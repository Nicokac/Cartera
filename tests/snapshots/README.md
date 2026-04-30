# Legacy Snapshots

`tests/snapshots/` contiene snapshots historicos previos a la migracion del directorio canonico.

## Estado

- este directorio es legacy
- el path canonico actual es `data/snapshots/`
- `generate_real_report.py` puede leer estos archivos solo como fallback historico
- no deberian agregarse snapshots operativos nuevos en esta carpeta
- no debe usarse este directorio como verdad principal para nuevas corridas

## Control explicito

El fallback legacy puede desactivarse con:

- `ENABLE_LEGACY_SNAPSHOTS=0`
- tambien se desactiva automaticamente cuando `data/snapshots/` ya tiene ventana
  operativa suficiente (>=20 snapshots de portfolio master).

Cuando el fallback esta habilitado y se usa un snapshot desde esta carpeta, el script emite un warning en logs para que no pase desapercibido.

## Motivo de conservacion temporal

Se conserva para no romper comparaciones historicas durante la transicion al nuevo directorio operativo.

## Convencion

- `YYYY-MM-DD_real_portfolio_master.csv`
- `YYYY-MM-DD_real_decision_table.csv`
- `YYYY-MM-DD_real_technical_overlay.csv`
- `YYYY-MM-DD_real_kpis.json`
- `YYYY-MM-DD_real_liquidity_contract.json`

## Uso esperado

Estos archivos se conservan solo para:

- comparaciones historicas durante la transicion
- fixtures de regresion
- validaciones puntuales del fallback legacy

## Contrato de memoria temporal

- una observacion canonica por `ticker + fecha`
- si hay reruns del mismo dia, se reemplaza el snapshot diario
- la liquidez no cuenta en los KPIs agregados de persistencia
- el HTML expone:
  - `Accion previa`
  - `Delta Score`
  - `Racha`
