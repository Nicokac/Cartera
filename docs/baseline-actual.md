# Baseline Actual

## Vigencia

Estado operativo vigente al `2026-04-11 00:16` en `America/Buenos_Aires`.

## Resumen

- overlay tecnico `24/24`
- Finviz fundamentals `20/24`
- Finviz ratings `15/24`
- regimen de mercado activo por `inflacion_local_alta`
- `5` refuerzos: `NEM`, `KO`, `EWZ`, `EEM`, `GOOGL`
- `1` reduccion: `MELI`
- `0` despliegues
- `32` neutrales
- `GD30` sigue en `Rebalancear / tomar ganancia`
- sizing con fondeo externo de `$600,000`: `NEM`, `KO`, `EWZ`
- `AAPL` salio de `Reducir` y quedo en `Mantener / Neutral`
- `XLU` salio de `Refuerzo` y quedo en `Mantener / Neutral`
- `VIST` sigue fuera de `Refuerzo`
- `SMA200` ya se integra al scoring tecnico con peso prudente y validacion real
- la liquidez operativa diaria puede alternar entre `CASH_ARS` y `CAUCION` sin romper continuidad temporal

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha`
- reruns del mismo dia no suman persistencia
- validacion real con fecha nueva:
  - `Senales nuevas: 0`
  - `Refuerzos persistentes: 5`
  - `Reducciones persistentes: 1`
  - `Sin historial: 0`
- la liquidez ya no cuenta en los KPIs agregados de memoria
- `CASH_ARS` y `CAUCION` comparten continuidad operativa en memoria temporal
- columnas visibles:
  - `Accion previa`
  - `Delta Score`
  - `Racha`

## Lectura operativa

- la memoria temporal ya quedo estabilizada sin nuevas senales en el rerun validado
- el regimen de mercado ya impacta el scoring por inflacion local alta
- el gate absoluto suave ya quedo validado en corrida real
- `NEM`, `KO` y `EWZ` quedaron como trio principal del sizing defensivo
- `GOOGL` se sostuvo en `Refuerzo` con tecnico `Alcista` y confirmacion de largo plazo
- `EWZ` se mantiene como senal fuerte y cerca de maximos de `52w`
- `VIST` sigue en `Mantener / Neutral`
- `XLU` salio de `Refuerzo` y paso a monitoreo
- con fondeo externo de `$600,000`, el sizing priorizo `NEM`, `KO` y `EWZ`
- la nueva curva de RSI de reduccion no rompio el bloque de refuerzos y endurecio el lado vendedor en `MELI` y `AAPL`
- `SMA200` ya confirma de forma suave a los ganadores estructurales:
  - `NEM`
  - `KO`
  - `EWZ`
  - `EEM`
  - `GOOGL`
- y agrega algo de presion a nombres todavia por debajo de largo plazo:
  - `MELI`
  - `MSFT`
  - `DISN`
  - `V`
- la cobertura Finviz cayo a `20/24` fundamentals y `15/24` ratings en esta corrida, sin romper el pipeline
- `bond_cer` mejoro por el flag inflacionario, pero todavia no emite `Refuerzo`
