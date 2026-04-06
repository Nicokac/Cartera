# Bond Pre-Scoring Context

## Objetivo

Documentar la etapa previa a incorporar nuevas reglas de scoring para bonos locales.

La idea de esta fase es:

- mejorar explicabilidad y comentarios operativos;
- usar la taxonomía local ampliada de Bonistas como capa analítica;
- definir qué contexto macro y de mercado hace falta para interpretar mejor bonos soberanos y ajustables;
- dejar explícito qué datos externos ya existen y cuáles todavía faltan.

## Estado actual

Hoy el proyecto ya cuenta con:

- taxonomía operativa estable:
  - `bond_sov_ar`
  - `bond_cer`
  - `bond_bopreal`
  - `bond_other`
- taxonomía local ampliada analítica:
  - `bond_hard_dollar`
  - `bond_cer`
  - `bond_bopreal`
  - `bond_dual`
  - `bond_dollar_linked`
  - `bond_fixed_rate`
  - `bond_tamar`
  - `bond_badlar`
  - `letter_fixed_rate`
- integración visible de Bonistas en el reporte HTML:
  - `Resumen por subfamilia`
  - `Resumen por taxonomia local`
  - `Monitoreo de bonos`

En esta etapa, la taxonomía local ampliada no cambia todavía el scoring.

Se usa para:

- monitoreo;
- auditoría;
- mejor lectura del bloque `Bonos Locales`;
- futura explicabilidad de comentarios operativos.

Actualizacion validada en corrida real:

- `bond_hard_dollar` ya incorpora `riesgo_pais_bps` en comentarios operativos;
- `bond_cer` ya incorpora `REM inflacion mensual` en comentarios operativos;
- `bond_bopreal` ya incorpora `riesgo_pais_bps` junto con `put_flag`;
- `bond_other` puede seguir operativo como `bond_other`, pero explicarse con taxonomia local `bond_cer` cuando Bonistas lo sugiere.

## Qué domina el análisis por tipo de bono

### bond_hard_dollar

Predominan:

- `TIR`
- `paridad`
- `duration / MD`
- `days_to_maturity`
- contexto de spread soberano

La lectura económica principal es:

- cuánto carry paga el bono;
- cuánta compresión de spread podría capturar;
- cuánto riesgo de duración asume;
- si la paridad deja margen o ya está exigida.

### bond_cer

Predominan:

- `TIR real`
- inflación observada
- inflación esperada
- `duration / MD`
- cercanía al vencimiento

La lectura principal es:

- si la tasa real es suficientemente atractiva;
- cuánto duration está comprando el inversor;
- si el bono ya cotiza muy arriba de par.

### bond_bopreal

Predominan:

- `TIR`
- `paridad`
- `duration / MD`
- `put_flag`
- liquidez y opcionalidad

La lectura principal es:

- carry en dólares;
- protección o flexibilidad por opcionalidad;
- si la paridad sigue razonable para el riesgo que asume.

### bond_other

Hoy esta categoría todavía se mantiene operativamente por prudencia, pero Bonistas ya ayuda a reclasificar analíticamente algunos casos.

Ejemplo actual:

- `TZXD6` y `TZXM7` siguen como `bond_other` en la taxonomía operativa;
- analíticamente ya aparecen como `bond_cer` en `bonistas_local_subfamily`.

## Qué vamos a usar antes del scoring

Antes de tocar reglas de scoring, la siguiente funcionalidad va a usar:

- `bonistas_local_subfamily`
- `bonistas_tir_pct`
- `bonistas_paridad_pct`
- `bonistas_md`
- `bonistas_days_to_maturity`
- `bonistas_tir_vs_avg_365d_pct`
- `bonistas_parity_gap_pct`
- `bonistas_put_flag`

Objetivos concretos:

- comentarios operativos más específicos por taxonomía local;
- mejor explicación en `Decisión final` y en `Bonos Locales`;
- preparación de una capa de contexto para scoring futuro.

## Datos externos ya disponibles o relativamente resueltos

### Bonistas

Sirve para:

- `TIR`
- `paridad`
- `MD`
- `valor técnico`
- fechas de emisión y vencimiento
- `put_flag`
- lectura por familia local

### ArgentinaDatos

La documentación pública muestra datos útiles para contexto macro y de régimen:

- `riesgo país`
- `inflacion mensual`
- `inflacion interanual`
- `indices UVA`
- `dolares`
- `letras capitalizables`

Uso esperado:

- `riesgo país` para `bond_hard_dollar` y `bond_bopreal`;
- inflación para `bond_cer`;
- letras para futura `letter_fixed_rate`.

### BCRA

La fuente oficial ya se usa para:

- `REM inflacion mensual`
- `REM 12m`
- `reservas_bcra_musd`
- `a3500_mayorista`
- `badlar`
- `tamar`

Uso esperado:

- enriquecer comentarios de `bond_cer`;
- preparar contexto de scoring para bonos ajustables por inflacion.

## Datos externos faltantes o a buscar

Estos datos todavía no están integrados y conviene considerarlos para futuras búsquedas o fuentes adicionales.

### Alta prioridad

- `ust_5y_pct`
  - referencia de tasa libre de riesgo
  - fuente faltante
- `ust_10y_pct`
  - referencia de tasa libre de riesgo
  - fuente faltante
- `rem_inflacion_12m_pct`
  - inflacion esperada a horizonte mas largo
  - fuente todavia no integrada

### Prioridad media

- `reservas_bcra_usd`
  - contexto de fragilidad o fortaleza externa
  - fuente faltante
- `tipo_cambio_mayorista`
  - contexto cambiario para soberanos y dollar-linked
  - fuente faltante
- `badlar`
  - benchmark para instrumentos tasa variable
  - fuente aún no resuelta de forma robusta
- `tamar`
  - benchmark para instrumentos tasa TAMAR
  - fuente aún no resuelta de forma robusta fuera del scraping puntual

### Prioridad específica por taxonomía futura

- `dual_reference_context`
  - para `bond_dual`
- `dollar_linked_reference_context`
  - para `bond_dollar_linked`
- `fixed_rate_curve_context`
  - para `bond_fixed_rate` y `letter_fixed_rate`

## Fuentes candidatas por dato

### Ya identificadas

- Bonistas
- ArgentinaDatos
- BCRA

### A buscar o validar

- curva Treasury de EE.UU.
- REM de BCRA
- reservas internacionales BCRA
- tipo de cambio mayorista BCRA
- series BADLAR/TAMAR robustas y consistentes

## Criterio de implementación

El orden recomendado para la siguiente etapa es:

1. usar `bonistas_local_subfamily` para comentarios y explicabilidad;
2. integrar un primer dato externo de contexto, idealmente `riesgo país`;
3. evaluar luego `REM` y curva Treasury;
4. recién después abrir scoring nuevo para bonos.

Estado actual de ese orden:

1. `Hecho`
2. `Hecho`
3. `Parcialmente hecho`
4. `Pendiente`

## Decisión vigente

Se deja asentado que:

- la próxima etapa de bonos no empieza por scoring;
- empieza por explicabilidad y contexto;
- la taxonomía local ampliada ya es suficientemente estable como para usarse en comentarios operativos;
- `riesgo país` ya quedó integrado para `bond_hard_dollar` y `bond_bopreal`;
- `REM inflacion mensual` ya quedó integrado para `bond_cer`;
- los siguientes datos externos prioritarios a buscar son:
  - `UST 5y / 10y`
  - `REM inflacion esperada 12m`
  - `reservas BCRA`
  - `tipo de cambio mayorista`

## Actualizacion 2026-04-05 - Cierre UST Pre-Scoring

Se deja asentado que la curva Treasury ya quedo integrada de forma opcional en esta etapa pre-scoring.

Alcance actual:

- el bloque `Bonos Locales` ya muestra:
  - `UST 5y`
  - `UST 10y`
- la capa analitica ya deriva `spread_vs_ust` para:
  - `bond_hard_dollar`
  - `bond_bopreal`
- los comentarios operativos ya usan esa referencia cuando la data esta disponible.

Casos validados en corrida real:

- `GD30`
  - `TIR 7.8%`
  - `spread 3.9% sobre UST`
- `AL30`
  - `TIR 9.1%`
  - `spread 5.2% sobre UST`
- `BPOC7`
  - `TIR 3.4%`
  - `spread -0.5% sobre UST`

Criterio vigente:

- `UST` ya no queda como dato faltante de primer nivel para explicabilidad;
- sigue siendo una integracion opcional y con fallback limpio;
- no modifica scoring;
- el proximo faltante relevante para contexto previo al scoring pasa a ser:
  - `REM inflacion esperada 12m`
  - `reservas BCRA`
  - `tipo de cambio mayorista`

## Actualizacion 2026-04-05 - REM 12m via Excel BCRA

Se deja asentado que `REM inflacion esperada 12m` pasa a quedar integrado desde la fuente oficial del BCRA.

Fuente primaria:

- `Base de Resultados del REM web.xlsx`
- publicada por BCRA
- consumida con `pandas.read_excel()`

Alcance actual:

- el bloque `Bonos Locales` ya puede mostrar:
  - `REM inflacion`
  - `REM 12m`
- la capa analitica ya propaga:
  - `bonistas_rem_inflacion_mensual_pct`
  - `bonistas_rem_inflacion_12m_pct`
- los comentarios de `bond_cer` ya pueden usar ambas referencias cuando estan disponibles.

Criterio vigente:

- `REM 12m` deja de ser un faltante de primer nivel para explicabilidad;
- la fuente elegida es oficial y no depende de API no documentada;
- no modifica scoring;
- los siguientes faltantes relevantes pasan a ser:
  - series historicas para tendencia
  - contexto de liquidez de mercado

## Actualizacion 2026-04-05 - BCRA API v4.0 monetarias

Se deja asentado que la API oficial del BCRA ya queda integrada para referencias monetarias y cambiarias basicas.

Alcance actual:

- el bloque `Bonos Locales` ya puede mostrar:
  - `Reservas BCRA`
  - `A3500`
  - `BADLAR`
  - `TAMAR`
- `BADLAR` y `TAMAR` oficiales pasan a tener prioridad sobre el scraping puntual cuando la API responde;
- la fuente elegida es publica, sin autenticacion y oficial.

Criterio vigente:

- no modifica scoring;
- reduce dependencia operativa del scraping de Bonistas para tasas de referencia;
- deja mejor preparado el contexto previo a scoring para:
  - `bond_hard_dollar`
  - `bond_bopreal`
  - `bond_tamar`
  - `bond_badlar`
  - futura lectura de `bond_dollar_linked`

Corrida real validada:

- `TAMAR`: `26.31`
- `BADLAR`: `25.375`
- `Reservas BCRA`: `43381.0`
- `A3500`: `1387.72`
