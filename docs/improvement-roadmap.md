# Roadmap de Mejoras

## Criterio

Priorización combinando:

- impacto funcional en corridas reales
- complejidad de implementación
- riesgo de regresión

## Estado actual

Ya quedaron resueltos:

- ejemplos `.json.example` y documentación para clones limpios
- guardas de `Peso_%` en valuación
- CEDEARs sin `finviz_map`
- contrato explícito de `mep_real`
- lazy loading de `config.py`
- cache acotado en Bonistas
- hardening de render HTML con escape consistente
- constantes canónicas para acciones en motor, sizing y renderer

## P1. Alto impacto, baja complejidad

### 1. Reproducibilidad de configuración

- estado: `Documentado`
- complejidad: `Baja`
- impacto: `Alto`

Trabajo ya hecho:

- documentación formal de JSON no versionados
- ejemplos `.json.example` para mappings y strategy
- bootstrap mínimo desde clone limpio

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
- agregado test específico con payload malicioso para render HTML

## P3. Mejora de diseño

### 4. Constantes canónicas para acciones

- estado: `Resuelto`
- complejidad: `Media`
- impacto: `Medio/Bajo`

Trabajo hecho:

- acciones centralizadas en `src/decision/action_constants.py`
- `actions.py`, `sizing.py` y `generate_smoke_report.py` ya no dependen de strings crudos dispersos

### 5. Limpieza final de bootstrap y contratos

- estado: `Pendiente`
- complejidad: `Media`
- impacto: `Medio/Bajo`

Trabajo:

- consolidar helpers comunes de validación
- reducir supuestos implícitos entre módulos

## Orden recomendado

1. limpieza final de bootstrap
