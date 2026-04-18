# Legacy Snapshots

`tests/snapshots/` contiene snapshots historicos previos a la migracion del directorio canonico.

## Estado

- este directorio es legacy
- el path canonico actual es `data/snapshots/`
- `generate_real_report.py` puede leer estos archivos solo como fallback historico
- no deberian agregarse snapshots operativos nuevos en esta carpeta

## Control explicito

El fallback legacy puede desactivarse con:

- `ENABLE_LEGACY_SNAPSHOTS=0`

Cuando el fallback esta habilitado y se usa un snapshot desde esta carpeta, el script emite un warning en logs para que no pase desapercibido.

## Motivo de conservacion temporal

Se conserva para no romper comparaciones historicas durante la transicion al nuevo directorio operativo.

## Convencion

- `YYYY-MM-DD_real_portfolio_master.csv`
- `YYYY-MM-DD_real_decision_table.csv`
- `YYYY-MM-DD_real_technical_overlay.csv`
- `YYYY-MM-DD_real_kpis.json`
- `YYYY-MM-DD_real_liquidity_contract.json`

## Objetivo

- comparar salidas entre iteraciones del motor
- detectar regresiones sin depender de APIs vivas

## Baseline vigente

La baseline funcional actual es la corrida real del `2026-04-09 07:31`.

Lectura operativa:

- overlay tecnico activo `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- regimen de mercado activo por `inflacion_local_alta`
- memoria temporal diaria validada con cambio de fecha efectiva
- refuerzos actuales:
  - `XLU`
  - `NEM`
  - `KO`
  - `EEM`
  - `VIST`
  - `GOOGL`
- reducciones actuales:
  - `MELI`
  - `AAPL`
- `GD30` sigue en `Rebalancear / tomar ganancia`
- con fondeo externo de `$600,000`, el sizing prioriza `XLU`, `NEM` y `KO`

## Contrato de memoria temporal

- una observacion canonica por `ticker + fecha`
- si hay reruns del mismo dia, se reemplaza el snapshot diario
- la liquidez no cuenta en los KPIs agregados de persistencia
- el HTML expone:
  - `Accion previa`
  - `Delta Score`
  - `Racha`
