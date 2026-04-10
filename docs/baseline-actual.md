# Baseline Actual

## Vigencia

Estado operativo vigente al `2026-04-09 23:33` en `America/Buenos_Aires`.

## Resumen

- overlay tecnico `24/24`
- Finviz fundamentals `20/24`
- Finviz ratings `15/24`
- regimen de mercado activo por `inflacion_local_alta`
- `6` refuerzos: `KO`, `EWZ`, `EEM`, `GOOGL`, `NEM`, `XLU`
- `2` reducciones: `MELI`, `AAPL`
- `0` despliegues
- `30` neutrales
- `GD30` sigue en `Rebalancear / tomar ganancia`
- sizing con fondeo externo de `$600,000`: `KO`, `EWZ`, `EEM`
- `EWZ` se consolido como `Refuerzo` y entro al sizing
- `VIST` salio de `Refuerzo` y quedo en `Mantener / Neutral`
- `XLV` sigue fuera de `Refuerzo`
- la liquidez operativa diaria puede alternar entre `CASH_ARS` y `CAUCION` sin romper continuidad temporal

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha`
- reruns del mismo dia no suman persistencia
- validacion real con fecha nueva:
  - `Senales nuevas: 5`
  - `Refuerzos persistentes: 5`
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
- `KO`, `EWZ` y `EEM` quedaron como trio principal del sizing defensivo
- `GOOGL` se sostuvo en `Refuerzo` con tecnico `Alcista`
- `EWZ` gano mas conviccion y se afirmo como senal relevante del dia
- `VIST` perdio el `Refuerzo` y paso a `Mantener / Neutral`
- `XLU` sigue en `Refuerzo`, pero con menos conviccion
- con fondeo externo de `$600,000`, el sizing priorizo `KO`, `EWZ` y `EEM`
- la nueva curva de RSI de reduccion no rompio el bloque de refuerzos y endurecio el lado vendedor en `MELI` y `AAPL`
- `NEM` sigue en `Refuerzo`, pero con menos conviccion que en corridas previas
- la cobertura Finviz cayo a `20/24` fundamentals y `15/24` ratings en esta corrida, sin romper el pipeline
- `bond_cer` mejoro por el flag inflacionario, pero todavia no emite `Refuerzo`
