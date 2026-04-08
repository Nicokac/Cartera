# Baseline Actual

## Vigencia

Estado operativo vigente al `2026-04-08 18:21:08` en `America/Buenos_Aires`.

## Resumen

- overlay técnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- `7` refuerzos: `XLU`, `XLV`, `NEM`, `KO`, `EEM`, `GOOGL`, `VIST`
- `0` reducciones
- `0` despliegues
- `31` neutrales
- `MELI` salió de `Reducir` y pasó a `Mantener / Neutral`
- régimen de mercado visible y activo por `inflacion_local_alta`

## Memoria temporal

- historial en `data/runtime/decision_history.csv`
- unidad canónica: `ticker + fecha`
- reruns del mismo día no suman persistencia
- validación real con fecha nueva:
  - `Senales nuevas: 3`
  - `Refuerzos persistentes: 5`
  - `Reducciones persistentes: 0`
  - `Sin historial: 0`
- columnas visibles:
  - `Accion previa`
  - `Δ Score`
  - `Racha`

## Lectura operativa

- la memoria temporal ya quedó validada con un día efectivo distinto
- el régimen de mercado ya impactó el scoring por inflación local alta
- `GOOGL` volvió a `Refuerzo`
- `EEM` entró a `Refuerzo`
- `MELI` perdió la señal de `Reducir`
- `bond_cer` mejoró por el flag inflacionario, pero todavía no emite `Refuerzo`
- `GD30` sigue en `Rebalancear / tomar ganancia`
