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
