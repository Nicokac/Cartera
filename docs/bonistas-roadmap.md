# Roadmap Bonistas

## Objetivo

Integrar `bonistas.com` como fuente complementaria para bonos, letras e instrumentos locales, sin acoplarla prematuramente al pipeline principal.

La prioridad no es reemplazar otras fuentes, sino enriquecer:
- explicabilidad de bonos
- reclasificación de instrumentos locales
- señales específicas de renta fija

## Principios

- empezar con una integración mínima y auditable
- evitar dependencias innecesarias en la primera versión
- separar scraping, normalización y uso analítico
- no acoplar el cliente a scoring hasta validar estabilidad

## Etapas

### Etapa 1. Cliente mínimo y contrato canónico

- Estado: `En progreso`

Objetivo:
- crear un cliente reusable en `src/clients/bonistas_client.py`
- definir el contrato de salida `bonistas_*`
- resolver tickers de cartera actual

Entregables:
- `normalize_bonistas_ticker(...)`
- `get_instrument_data(...)`
- `get_listing(...)`
- `get_macro_variables(...)`
- `get_bonds_for_portfolio(...)`
- cache en memoria por TTL
- `data/mappings/bonistas_ticker_map.json`

No incluye todavía:
- integración al pipeline
- persistencia en disco
- scoring de bonos

### Etapa 2. Enriquecimiento analítico

- Estado: `Pendiente`

Objetivo:
- consumir los datos Bonistas desde una capa analítica propia

Entregables sugeridos:
- `src/analytics/bond_analytics.py`
- derivadas como:
  - `days_to_maturity`
  - `duration_bucket`
  - `tir_real_relativa`
  - `paridad_relativa_subfamily`
  - `cer_parity_gap`
  - `bopreal_put_flag`

### Etapa 3. Reclasificación taxonómica

- Estado: `Pendiente`

Objetivo:
- usar listados Bonistas para reducir `bond_other`

Entregables sugeridos:
- sugerencia de reclasificación por instrumento
- validación manual antes de sobreescribir taxonomía actual

Subfamilias posibles a futuro:
- `bond_hard_dollar`
- `bond_dual`
- `bond_dollar_linked`
- `bond_fixed_rate`
- `bond_tamar`
- `bond_badlar`
- `letter_fixed_rate`

### Etapa 4. Integración al pipeline

- Estado: `Pendiente`

Objetivo:
- enchufar Bonistas al flujo real sin romper estabilidad

Orden sugerido:
1. exponer columnas `bonistas_*` en reportes
2. usar Bonistas para explicabilidad
3. recién después evaluar uso en scoring

### Etapa 5. Persistencia y hardening

- Estado: `Pendiente`

Objetivo:
- mejorar robustez operativa

Líneas posibles:
- cache opcional a disco
- tolerancia a cambios de layout
- tests con fixtures HTML locales
- monitoreo de parse status

## Estado actual

Primera implementación objetivo:
- cliente mínimo
- cache en memoria
- contrato de salida normalizado
- tests de contrato básico sin red

Avance concreto actual:
- `bonistas_client.py` creado
- contrato `bonistas_*` definido
- mapping de tickers inicial creado
- inferencia básica de subfamilia por ticker agregada
- parser mínimo de página individual ya cubierto con tests sin red

## Criterio de cierre de la Etapa 1

- existe `bonistas_client.py`
- el cliente devuelve columnas `bonistas_*` consistentes
- la normalización de tickers está desacoplada en mappings
- hay tests mínimos de contrato

## Actualizacion 2026-04-05

Estado revisado:
- Etapa 1: `Hecho`
- Etapa 2: `Hecho`
- Etapa 4: `En progreso`

Avance validado en corrida real:
- el reporte HTML ya expone un bloque `Bonos Locales`
- el monitor de bonos ya muestra:
  - `bonistas_tir_pct`
  - `bonistas_paridad_pct`
  - `bonistas_md`
  - `bonistas_duration_bucket`
  - `bonistas_days_to_maturity`
  - `bonistas_tir_vs_avg_365d_pct`
  - `bonistas_parity_gap_pct`
  - `bonistas_put_flag`
- la capa analitica ya infiere `asset_subfamily` de bonos cuando no viene propagada desde valuacion
- la normalizacion de paridad operativa ya funciona para:
  - `bond_sov_ar`
  - `bond_bopreal`
- las variables macro ya filtran tasas implausibles, por lo que `BADLAR` puede quedar en `-` antes de mostrar un valor basura

Baseline Bonistas v1:
- `bond_sov_ar`
  - `GD30`: `87.24%`
  - `AL30`: `85.11%`
  - `GD35`: `75.64%`
- `bond_bopreal`
  - `BPOC7`: `102.00%`
- `bond_cer`
  - `TZX26`: `102.00%`
- `bond_other`
  - `TZXD6`: `100.30%`
  - `TZXM7`: `99.30%`

Proximo foco:
- ampliar taxonomia local detallada sin romper `asset_subfamily`
- usar taxonomia local detallada para reclasificar mejor:
  - `bond_dual`
  - `bond_fixed_rate`
  - `bond_dollar_linked`
  - `bond_tamar`
- despues recien evaluar uso gradual en scoring de bonos

## Actualizacion 2026-04-05 - Explicabilidad pre-scoring

Avance validado:

- el bloque `Bonos Locales` ya muestra contexto macro adicional:
  - `Riesgo pais`
  - `REM inflacion`
- los comentarios operativos ya usan contexto por taxonomia local:
  - `bond_hard_dollar`
  - `bond_cer`
  - `bond_bopreal`

Casos de referencia ya observados en corrida real:

- `GD30`
  - comentario con `paridad`, `TIR` y `riesgo pais`
- `AL30`
  - comentario con `paridad`, `TIR` y `riesgo pais`
- `BPOC7`
  - comentario con `paridad`, `PUT` y `riesgo pais`
- `TZX26`
  - comentario con `TIR real`, `paridad` y `REM`
- `TZXD6`
  - comentario CER usando taxonomia local ampliada
- `TZXM7`
  - comentario CER usando taxonomia local ampliada

Conclusion de etapa:

- la explicabilidad pre-scoring de bonos ya quedo estable;
- el siguiente salto ya no es de renderer ni de taxonomia;
- el siguiente salto logico es scoring de bonos usando este contexto.

## Actualizacion 2026-04-05 - Cierre UST Pre-Scoring

Avance validado:

- el reporte HTML ya puede mostrar:
  - `UST 5y`
  - `UST 10y`
- la capa analitica ya deriva `spread_vs_ust` para:
  - `bond_hard_dollar`
  - `bond_bopreal`
- los comentarios operativos ya usan esa lectura relativa cuando FRED esta disponible.

Casos observados en corrida real:

- `GD30`
  - `spread 3.9% sobre UST`
- `AL30`
  - `spread 5.2% sobre UST`
- `BPOC7`
  - `spread -0.5% sobre UST`

Estado de la etapa:

- explicabilidad pre-scoring con:
  - `riesgo pais`
  - `REM`
  - `UST`
  - `Hecho`
- scoring de bonos:
  - `Pendiente`

## Actualizacion 2026-04-05 - REM 12m via Excel BCRA

Avance validado:

- la fuente oficial elegida para `REM 12m` es el Excel del BCRA;
- el pipeline ya puede propagar:
  - `rem_inflacion_mensual_pct`
  - `rem_inflacion_12m_pct`
- el renderer de `Bonos Locales` ya puede exponer ambas referencias;
- los comentarios operativos de `bond_cer` ya pueden usar:
  - `TIR real`
  - `paridad`
  - `REM 12m`
  - `REM mensual`

Criterio de esta subetapa:

- no se toca scoring;
- se mejora la lectura estrategica de bonos CER;
- se consolida la fuente oficial del BCRA como referencia para expectativas de inflacion.

## Actualizacion 2026-04-05 - BCRA monetarias v4.0

Avance validado a nivel de implementacion:

- el pipeline ya puede consumir desde la API oficial del BCRA:
  - `reservas_bcra_musd`
  - `a3500_mayorista`
  - `badlar`
  - `badlar_tea`
  - `tamar`
  - `tamar_tea`
- `TAMAR` se descubre desde el catalogo oficial de variables y no queda hardcodeada;
- `BADLAR` y `TAMAR` oficiales pueden sobreescribir el dato puntual de Bonistas cuando la API esta disponible;
- el renderer de `Bonos Locales` ya queda preparado para exponer:
  - `Reservas BCRA`
  - `A3500`

Criterio de esta subetapa:

- sigue siendo contexto pre-scoring;
- se prioriza fuente oficial sobre scraping cuando hay superposicion;
- el siguiente paso natural pasa a ser decidir si estas referencias se usan solo en monitoreo o tambien en comentarios operativos.
