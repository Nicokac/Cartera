# Bonistas.com como Fuente de Referencia

## Objetivo

Documentar qué campos de `bonistas.com` serían útiles para enriquecer la capa de bonos, letras e instrumentos locales, y cómo se mapearían a la taxonomía actual del proyecto.

Este documento es de referencia funcional. No implica todavía que `bonistas.com` sea una fuente integrada al pipeline.

## Uso propuesto

En una primera etapa, `bonistas.com` conviene usarse como:
- fuente de validación manual
- apoyo de auditoría para bonos locales
- insumo para diseñar señales específicas de renta fija

En una segunda etapa, si el scraping resulta estable:
- cliente dedicado tipo `src/clients/bonistas_client.py`
- columnas `bonistas_*` normalizadas
- integración al pipeline de scoring y reportes

## Campos útiles por instrumento

Estos campos son los que más valor aportarían para una integración inicial:

- `Precio`
- `Variacion diaria`
- `Fecha emision`
- `Fecha vencimiento`
- `Valor Tecnico`
- `Paridad`
- `TIR`
- `MD`
- `TIR Promedio 365d`
- `TIR Min 365d`
- `TIR Max 365d`
- `Sensibilidad TIR`
- `Precio clean`
- `Precio dirty`
- `Cupon corrido`

## Campos de régimen o referencia macro

Además de métricas por instrumento, Bonistas aporta variables de contexto que pueden servir como referencia:

- `Dolar MEP`
- `Dolar CCL`
- `CER`
- `TAMAR`
- `BADLAR`
- `Inflacion mensual`
- `Inflacion interanual`
- `Inflacion esperada REM`

También es útil la tabla de dólares financieros por bonos AL/GD para validar spreads o arbitrajes implícitos.

## Mapeo a columnas canónicas sugeridas

Si se integra una capa Bonistas, conviene normalizar a nombres explícitos:

- `bonistas_precio`
- `bonistas_variacion_diaria_pct`
- `bonistas_fecha_emision`
- `bonistas_fecha_vencimiento`
- `bonistas_dias_al_vencimiento`
- `bonistas_valor_tecnico`
- `bonistas_paridad_pct`
- `bonistas_tir_pct`
- `bonistas_md`
- `bonistas_tir_prom_365d_pct`
- `bonistas_tir_min_365d_pct`
- `bonistas_tir_max_365d_pct`
- `bonistas_precio_clean`
- `bonistas_precio_dirty`
- `bonistas_cupon_corrido`
- `bonistas_cer`
- `bonistas_tamar`
- `bonistas_badlar`
- `bonistas_mep`
- `bonistas_ccl`

## Mapeo a la taxonomía actual

### `bond_sov_ar`

Ejemplos actuales:
- `GD30`
- `AL30`
- `GD35`

Campos más útiles:
- `bonistas_tir_pct`
- `bonistas_paridad_pct`
- `bonistas_md`
- `bonistas_fecha_vencimiento`
- `bonistas_dias_al_vencimiento`
- `bonistas_mep`
- `bonistas_ccl`

Señales potenciales:
- carry relativo
- compresión / descompresión de TIR
- sensibilidad a tasa
- riesgo por duration
- ventana de toma de ganancia con paridad o TIR extremas

### `bond_cer`

Ejemplos actuales:
- `TZX26`

Campos más útiles:
- `bonistas_tir_pct`
- `bonistas_valor_tecnico`
- `bonistas_paridad_pct`
- `bonistas_md`
- `bonistas_fecha_vencimiento`
- `bonistas_dias_al_vencimiento`
- `bonistas_cer`

Señales potenciales:
- rendimiento real CER
- duration real
- relación TIR vs CER
- paridad relativa dentro del bloque CER

### `bond_bopreal`

Ejemplos actuales:
- `BPOC7`

Campos más útiles:
- `bonistas_tir_pct`
- `bonistas_paridad_pct`
- `bonistas_md`
- `bonistas_fecha_vencimiento`
- flags de opcionalidad o put cuando existan observaciones específicas

Señales potenciales:
- TIR relativa entre BOPREALs
- prima/descuento por opcionalidad
- sensibilidad a compresión
- lectura prudencial de liquidez y rescate

### `bond_other`

Ejemplos actuales:
- `TZXM7`
- `TZXD6`

Uso principal inicial:
- ayudar a reclasificar instrumentos hoy mal agrupados
- reducir dependencia del bucket residual `bond_other`

## Subfamilias nuevas posibles

Bonistas permitiría evolucionar la taxonomía de bonos a algo más fino:

- `bond_hard_dollar`
- `bond_cer`
- `bond_bopreal`
- `bond_dual`
- `bond_dollar_linked`
- `bond_fixed_rate`
- `bond_tamar`
- `bond_badlar`
- `letter_fixed_rate`

Esto sería útil sobre todo si el objetivo pasa de un modelo prudencial genérico a uno más económico-financiero por tipo de instrumento.

## Prioridad de integración sugerida

### Etapa 1

Extraer primero:
- `TIR`
- `Paridad`
- `MD`
- `Fecha vencimiento`
- `Valor Tecnico`
- `Precio clean`
- `Precio dirty`

Más referencias:
- `CER`
- `TAMAR`
- `BADLAR`
- `MEP`
- `CCL`

### Etapa 2

Usar esos datos para:
- enriquecer explicabilidad de bonos
- reclasificar `bond_other`
- construir señales específicas por subfamilia

### Etapa 3

Si la fuente se mantiene estable:
- integrar `bonistas_client.py`
- persistir columnas `bonistas_*`
- sumar señales al scoring real de bonos

## Beneficio esperado

El principal beneficio de Bonistas no es sumar más datos por sumar, sino salir de una lógica de bonos basada casi solo en:
- peso
- ganancia
- prudencia general

y pasar a una lógica más propia de renta fija, apoyada en:
- TIR
- paridad
- duration
- vencimiento
- indexación
- referencias locales

## Referencias

- https://bonistas.com/
- https://bonistas.com/variables
- https://bonistas.com/bonos-cer-hoy
- https://bonistas.com/bonos-bopreal-hoy

## Actualizacion 2026-04-05

### Baseline operativa Bonistas v1

Bloque validado en reporte real:
- `CER`: `738.7059`
- `TAMAR`: `26.31`
- `BADLAR`: `-` cuando el parser detecta un valor implausible

Resumen por subfamilia validado:
- `bond_sov_ar`: `3` instrumentos, `TIR_Promedio 8.97`, `Paridad_Promedio 82.66`
- `bond_bopreal`: `1` instrumento, `TIR_Promedio 3.40`, `Paridad_Promedio 102.00`
- `bond_cer`: `1` instrumento, `TIR_Promedio -8.10`, `Paridad_Promedio 102.00`
- `bond_other`: `2` instrumentos, `TIR_Promedio 0.15`, `Paridad_Promedio 99.80`

### Taxonomia local ampliada

Ademas de la taxonomia operativa actual del scoring:
- `bond_sov_ar`
- `bond_cer`
- `bond_bopreal`
- `bond_other`

Bonistas ya permite una taxonomia local mas fina para instrumentos locales:
- `bond_hard_dollar`
- `bond_cer`
- `bond_bopreal`
- `bond_dual`
- `bond_dollar_linked`
- `bond_fixed_rate`
- `bond_tamar`
- `bond_badlar`
- `letter_fixed_rate`

Criterio recomendado:
- mantener `asset_subfamily` estable para scoring actual
- usar una capa local detallada separada para analitica y monitoreo
- promover tickers desde `bond_other` solo cuando la nueva clasificacion este validada

### Mapeo recomendado entre capas

Taxonomia operativa actual:
- `bond_sov_ar` -> soberanos AL/GD visibles hoy en cartera
- `bond_cer` -> instrumentos CER
- `bond_bopreal` -> BOPREAL
- `bond_other` -> residual prudente

Taxonomia local detallada propuesta:
- `bond_sov_ar` puede convivir con `bond_hard_dollar` como lectura de mercado local
- `bond_other` deberia reducirse a medida que Bonistas permita identificar:
  - `bond_dual`
  - `bond_fixed_rate`
  - `bond_dollar_linked`
  - `bond_tamar`
