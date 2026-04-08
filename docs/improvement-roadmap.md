# Roadmap de Mejoras

## Criterio

Priorización combinando:

- impacto funcional en corridas reales
- complejidad de implementación
- riesgo de regresión

## P1. Alto impacto, baja complejidad

### 1. Reproducibilidad de configuración

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Alto`

Trabajo:

- documentar formalmente que los JSON reales no se versionan
- agregar ejemplos `.json.example` para mappings y strategy
- explicar bootstrap mínimo desde clone limpio

### 2. Guardas de `Peso_%` en valuación

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Alto`

Trabajo:

- evitar división contra suma cero
- devolver `0` o `NaN` controlado según el caso
- cubrir con tests

### 3. CEDEAR sin mapping Finviz

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Alto`

Trabajo:

- no descartar el activo silenciosamente
- incluirlo con soporte parcial o warning explícito

## P2. Impacto medio, complejidad baja/media

### 4. Contrato explícito de `mep_real`

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Medio`

### 5. Lazy loading de `config.py`

- estado: `Pendiente`
- complejidad: `Media`
- impacto: `Medio`

### 6. Cache con poda en Bonistas

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Medio`

## P3. Mejora de diseño

### 7. Enum o constantes canónicas para acciones

- estado: `Pendiente`
- complejidad: `Media`
- impacto: `Medio/Bajo`

### 8. Hardening extra de render

- estado: `Pendiente`
- complejidad: `Baja`
- impacto: `Bajo`

## Orden recomendado

1. reproducibilidad y ejemplos de config
2. guardas en valuación
3. CEDEAR sin mapping
4. contrato explícito de `mep_real`
5. lazy loading
6. cache Bonistas
7. enums y limpieza final
