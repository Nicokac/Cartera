# Baseline Actual

## Vigencia

Estado operativo vigente al `2026-04-09 18:32` en `America/Buenos_Aires`.

## Resumen

- overlay tecnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- regimen de mercado activo por `inflacion_local_alta`
- `7` refuerzos: `XLU`, `KO`, `EEM`, `EWZ`, `VIST`, `NEM`, `GOOGL`
- `2` reducciones: `MELI`, `AAPL`
- `0` despliegues
- `29` neutrales
- `GD30` sigue en `Rebalancear / tomar ganancia`
- sizing con fondeo externo de `$600,000`: `XLU`, `KO`, `EEM`
- `EWZ` entro como nuevo `Refuerzo`
- `XLV` salio de `Refuerzo` y quedo en `Mantener / Neutral`
- la liquidez operativa diaria puede alternar entre `CASH_ARS` y `CAUCION` sin romper continuidad temporal

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha`
- reruns del mismo dia no suman persistencia
- validacion real con fecha nueva:
  - `Senales nuevas: 4`
  - `Refuerzos persistentes: 6`
  - `Reducciones persistentes: 0`
  - `Sin historial: 0`
- la liquidez ya no cuenta en los KPIs agregados de memoria
- `CASH_ARS` y `CAUCION` comparten continuidad operativa en memoria temporal
- columnas visibles:
  - `Accion previa`
  - `Delta Score`
  - `Racha`

## Lectura operativa

- la memoria temporal ya quedo validada con dia efectivo distinto
- el regimen de mercado ya impacta el scoring por inflacion local alta
- el gate absoluto suave ya quedo validado en corrida real
- `EEM` se sostuvo en `Refuerzo` con tecnico `Alcista`
- `GOOGL` se sostuvo en `Refuerzo` con tecnico `Alcista`
- `EWZ` escalo a `Refuerzo` como nueva senal relevante del dia
- `XLV` quedo bloqueado en `Mantener / Neutral` por `Momentum_20d_% < 0` con tecnico `Mixta`
- `XLU`, `KO`, `EEM`, `VIST`, `NEM` y `GOOGL` aparecen como refuerzos persistentes
- con fondeo externo de `$600,000`, el sizing priorizo `XLU`, `KO` y `EEM`
- la nueva curva de RSI de reduccion no rompio el bloque de refuerzos y endurecio el lado vendedor en `MELI` y `AAPL`
- `NEM` sigue en `Refuerzo`, pero con menos conviccion que en la corrida anterior
- `bond_cer` mejoro por el flag inflacionario, pero todavia no emite `Refuerzo`
