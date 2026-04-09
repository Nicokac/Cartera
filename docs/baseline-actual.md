# Baseline Actual

## Vigencia

Estado operativo vigente al `2026-04-09 07:01` en `America/Buenos_Aires`.

## Resumen

- overlay tecnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- regimen de mercado activo por `inflacion_local_alta`
- `6` refuerzos: `XLU`, `NEM`, `KO`, `EEM`, `VIST`, `GOOGL`
- `2` reducciones: `MELI`, `AAPL`
- `1` despliegue: `CASH_ARS`
- `30` neutrales
- `GD30` sigue en `Rebalancear / tomar ganancia`
- sizing con fondeo externo de `$600,000`: `XLU`, `NEM`, `KO`
- `XLV` salio de `Refuerzo` y quedo en `Mantener / Neutral`

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha`
- reruns del mismo dia no suman persistencia
- validacion real con fecha nueva:
  - `Senales nuevas: 3`
  - `Refuerzos persistentes: 5`
  - `Reducciones persistentes: 0`
  - `Sin historial: 0`
- la liquidez ya no cuenta en los KPIs agregados de memoria
- columnas visibles:
  - `Accion previa`
  - `Δ Score`
  - `Racha`

## Lectura operativa

- la memoria temporal ya quedo validada con dia efectivo distinto
- el regimen de mercado ya impacta el scoring por inflacion local alta
- el gate absoluto suave ya quedo validado en corrida real
- `EEM` se sostuvo en `Refuerzo` con tecnico `Alcista` y momentum positivo
- `GOOGL` se sostuvo en `Refuerzo` con tecnico `Alcista`
- `XLV` quedo bloqueado en `Mantener / Neutral` por `Momentum_20d_% < 0` con tecnico `Mixta`
- `VIST`, `XLU`, `KO` y `NEM` aparecen como refuerzos persistentes
- con fondeo externo de `$600,000`, el sizing priorizo `XLU`, `NEM` y `KO`
- la nueva curva de RSI de reduccion no rompio el bloque de refuerzos y endurecio el lado vendedor en `MELI` y `AAPL`
- `bond_cer` mejoro por el flag inflacionario, pero todavia no emite `Refuerzo`
