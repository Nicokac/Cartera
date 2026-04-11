# Baseline Actual

## Vigencia

Estado operativo vigente al `2026-04-11 00:48` en `America/Buenos_Aires`.

## Resumen

- overlay tecnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- regimen de mercado activo por `inflacion_local_alta`
- `6` refuerzos: `XLU`, `NEM`, `KO`, `EWZ`, `VIST`, `GOOGL`
- `1` reduccion: `MELI`
- `0` despliegues
- `31` neutrales
- `GD30` sigue en `Rebalancear / tomar ganancia`
- sizing con fondeo externo de `$600,000`: `XLU`, `NEM`, `KO`
- `AAPL` sigue en `Mantener / Neutral`
- `XLU` volvio a `Refuerzo`
- `VIST` volvio a `Refuerzo`
- `EEM` salio de `Refuerzo` y quedo en `Mantener / Neutral`
- `SMA200` ya se integra al scoring tecnico con peso prudente y validacion real
- la calibracion conservadora de Finviz recupero cobertura completa de fundamentals
- la liquidez operativa diaria puede alternar entre `CASH_ARS` y `CAUCION` sin romper continuidad temporal

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha`
- reruns del mismo dia no suman persistencia
- validacion real con fecha nueva:
  - `Senales nuevas: 3`
  - `Refuerzos persistentes: 4`
  - `Reducciones persistentes: 1`
  - `Sin historial: 0`
- la liquidez ya no cuenta en los KPIs agregados de memoria
- `CASH_ARS` y `CAUCION` comparten continuidad operativa en memoria temporal
- columnas visibles:
  - `Accion previa`
  - `Delta Score`
  - `Racha`

## Lectura operativa

- la memoria temporal registra una nueva rotacion real del bloque comprador
- el regimen de mercado ya impacta el scoring por inflacion local alta
- el gate absoluto suave ya quedo validado en corrida real
- `XLU`, `NEM` y `KO` quedaron como trio principal del sizing defensivo
- `GOOGL` se sostuvo en `Refuerzo` con tecnico `Alcista` y confirmacion de largo plazo
- `EWZ` se mantiene fuerte, pero ya no entra en el top-3 de sizing
- `VIST` volvio a `Refuerzo`
- `XLU` recupero `Refuerzo` y paso a liderar el sizing
- `EEM` cedio conviccion y quedo neutral
- con fondeo externo de `$600,000`, el sizing priorizo `XLU`, `NEM` y `KO`
- la nueva curva de RSI de reduccion no rompio el bloque de refuerzos y endurecio el lado vendedor en `MELI` y `AAPL`
- `SMA200` ya confirma de forma suave a los ganadores estructurales:
  - `NEM`
  - `KO`
  - `EWZ`
  - `XLU`
  - `GOOGL`
- y agrega algo de presion a nombres todavia por debajo de largo plazo:
  - `MELI`
  - `MSFT`
  - `DISN`
  - `V`
- la calibracion mas conservadora de Finviz subio la cobertura a `24/24` fundamentals y `17/24` ratings
- la mejora de cobertura no fue cosmetica: movio la decision final y el sizing
- `bond_cer` mejoro por el flag inflacionario, pero todavia no emite `Refuerzo`
