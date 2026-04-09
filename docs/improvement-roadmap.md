# Roadmap de Mejoras

## Criterio

Priorizacion combinando:

- impacto funcional en corridas reales
- complejidad de implementacion
- riesgo de regresion

## Estado actual

Ya quedaron resueltos:

- ejemplos `.json.example` y documentacion para clones limpios
- guardas de `Peso_%` en valuacion
- CEDEARs sin `finviz_map`
- contrato explicito de `mep_real`
- lazy loading de `config.py`
- cache acotado en Bonistas
- hardening de render HTML con escape consistente
- constantes canonicas para acciones en motor, sizing y renderer
- bootstrap numerico comun para conversiones y validaciones escalares
- warnings de pandas en `tests/test_sizing.py`
- cobertura base de clientes externos (`iol`, `argentinadatos`, `market_data`, `finviz_client`)

## P1. Alto impacto, baja complejidad

### 1. Reproducibilidad de configuracion

- estado: `Documentado`
- complejidad: `Baja`
- impacto: `Alto`

Trabajo ya hecho:

- documentacion formal de JSON no versionados
- ejemplos `.json.example` para mappings y strategy
- bootstrap minimo desde clone limpio

## P2. Impacto medio, complejidad baja/media

### 2. Cache con poda en Bonistas

- estado: `Resuelto`
- complejidad: `Baja`
- impacto: `Medio`

Trabajo hecho:

- `_CACHE` ahora usa capacidad acotada
- entradas vencidas se purgan al consultar
- hay helper `clear_cache()` para tests y corridas controladas

### 3. Hardening extra de render

- estado: `Resuelto`
- complejidad: `Baja`
- impacto: `Medio/Bajo`

Trabajo hecho:

- macros, motivos, drivers y etiquetas visibles pasan por escape consistente
- agregado test especifico con payload malicioso para render HTML

## P3. Mejora de diseño

### 4. Constantes canonicas para acciones

- estado: `Resuelto`
- complejidad: `Media`
- impacto: `Medio/Bajo`

Trabajo hecho:

- acciones centralizadas en `src/decision/action_constants.py`
- `actions.py`, `sizing.py` y `generate_smoke_report.py` ya no dependen de strings crudos dispersos

### 5. Limpieza final de bootstrap y contratos

- estado: `Resuelto`
- complejidad: `Media`
- impacto: `Medio/Bajo`

Trabajo hecho:

- helper comun en `src/common/numeric.py`
- validaciones numericas escalares unificadas en scoring, liquidez, valuacion y sizing

## Proximo foco

Si seguimos mejorando, el trabajo ya pasa de hardening a evolucion de producto:

1. ajustar scoring o persistencia con evidencia de nuevas corridas reales
2. ampliar cobertura en integraciones secundarias o de borde
3. revisar mejoras de diseño de scoring absoluto vs relativo
