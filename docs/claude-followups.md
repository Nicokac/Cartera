# Pendientes Reales Post-Claude

## Objetivo

Separar hallazgos reales del estado actual del proyecto de observaciones que ya quedaron resueltas o que solo aplican a un clone incompleto de GitHub.

## Lo que quedó desactualizado del análisis original

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

Estado: `Documentado`

El proyecto local funciona, pero `.gitignore` excluye `*.json`. Eso hace que un clone limpio pueda quedar sin:

- `data/mappings/*.json`
- `data/strategy/*.json`

Decisión actual:

- mantener los JSON reales fuera del repo por ahora
- documentar explícitamente la política
- publicar archivos `.json.example` con la estructura esperada

### P1. Guardas en `valuation.py`

Estado: `Resuelto`

- `Peso_%` ahora usa una guarda explícita contra suma cero en `src/portfolio/valuation.py`
- cuando el total es cero, devuelve `0.0` en vez de `NaN` o `inf`

### P1. CEDEAR sin mapping en Finviz

Estado: `Resuelto`

- en `src/portfolio/classify.py`, un CEDEAR sin `finviz_map` ya no desaparece
- entra al portfolio con `Ticker_Finviz = None` y cobertura parcial

### P2. Checks explícitos de `mep_real`

Estado: `Resuelto`

- scoring, liquidez y valuación ya tratan `mep_real` como válido solo si es numérico y `> 0`
- `0.0` pasa a considerarse MEP ausente, sin depender de truthiness accidental

### P2. `config.py` con eager loading

Estado: `Resuelto`

- `src/config.py` ahora usa carga lazy con cache por atributo
- se mantiene la interfaz `project_config.FINVIZ_MAP`, `SCORING_RULES`, etc.
- el import deja de disparar lectura eager de todos los JSON

### P3. Cache de Bonistas sin poda

Estado: `Pendiente`

- `src/clients/bonistas_client.py` mantiene `_CACHE` sin límite de tamaño

### P3. Strings mágicos para acciones

Estado: `Pendiente`

- acciones operativas y sugeridas siguen circulando como strings literales

## Conclusión

La deuda real vigente ya no es “arreglar todo lo que marcó Claude”, sino:

1. sostener reproducibilidad documental del repo
2. revisar caches y contratos secundarios
3. cerrar limpieza de diseño
