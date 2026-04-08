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

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Medio`

Trabajo:

- reemplazar `_CACHE` por cache acotado o LRU
- evitar crecimiento indefinido en procesos largos

### 3. Hardening extra de render

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Medio/Bajo`

Trabajo:

- revisar que todo texto libre insertado al HTML pase por escape consistente
- cubrir con tests de render

## P3. Mejora de diseño

### 4. Enum o constantes canónicas para acciones

- estado: `Pendiente`
- complejidad: `Media`
- impacto: `Medio/Bajo`

### 5. Limpieza final de bootstrap y contratos

- estado: `Pendiente`
- complejidad: `Media`
- impacto: `Medio/Bajo`

Trabajo:

- consolidar helpers comunes de validación
- reducir supuestos implícitos entre módulos

## Orden recomendado

1. cache Bonistas
2. hardening de render
3. enums o constantes canónicas para acciones
4. limpieza final de bootstrap
