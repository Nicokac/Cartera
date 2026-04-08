# Pendientes Reales Post-Claude

## Objetivo

Separar hallazgos reales del estado actual del proyecto de observaciones que ya quedaron resueltas o que solo aplican a un clone incompleto de GitHub.

## Qué quedó desactualizado del análisis original

Estos puntos ya no describen el estado actual del repo local:

- `tech_reduccion = 1 - tech_refuerzo`
  - ya fue reemplazado por `reduction_subscores` propios en `src/decision/scoring.py`
- duplicación principal en acciones
  - `assign_base_action(...)` y `assign_action_v2(...)` ya comparten `_assign_action(...)`
- duplicación principal en sizing
  - `build_prudent_allocation(...)` y `build_dynamic_allocation(...)` ya comparten `_prepare_allocation_frame(...)`
- bonos sin capacidad de `Refuerzo`
  - hoy existe `Refuerzo` conservador para `bond_cer`, `bond_bopreal` y `bond_other`
- overlay técnico no configurable
  - hoy los rangos y subscores viven en `data/strategy/scoring_rules.json`

## Hallazgos reales vigentes

### P1. Reproducibilidad del repo

El proyecto local funciona, pero `.gitignore` excluye `*.json`. Eso hace que un clone limpio pueda quedar sin:

- `data/mappings/*.json`
- `data/strategy/*.json`

No es un blocker del workspace actual, pero sí una deuda real de distribución.

Decisión actual:

- mantener los JSON reales fuera del repo por ahora
- documentar explícitamente la política
- publicar archivos `.json.example` con la estructura esperada

### P1. Guardas en `valuation.py`

`Peso_%` todavía se calcula contra `Valorizado_ARS.sum()` sin una guarda explícita para suma cero.

### P1. CEDEAR sin mapping en Finviz

En `src/portfolio/classify.py`, un CEDEAR sin `finviz_map` puede quedar fuera silenciosamente.

### P2. Checks explícitos de `mep_real`

Todavía hay usos tipo `bool(mep_real)` o guards basados en truthiness.

### P2. `config.py` con eager loading

Los JSON se cargan al importar el módulo.

### P3. Cache de Bonistas sin poda

`src/clients/bonistas_client.py` mantiene `_CACHE` sin límite de tamaño.

### P3. Strings mágicos para acciones

Acciones operativas y sugeridas siguen circulando como strings literales.

## Conclusión

La deuda real vigente ya no es “arreglar todo lo que marcó Claude”, sino:

1. mejorar reproducibilidad del repo
2. endurecer guardas de valuación
3. evitar pérdida silenciosa de CEDEARs
4. limpiar contratos y bootstrap
