# Roadmap de Auditoria

## Objetivo

Traducir la auditoria externa a un backlog util para el estado real del repo al `2026-04-09`.

Este documento no copia el analisis crudo. Filtra:

- hallazgos ya resueltos
- hallazgos parcialmente validos
- trabajo real pendiente

## Resumen de triage

### Hallazgos descartados por estar resueltos

Estos puntos aparecieron en la auditoria, pero ya no describen el estado actual del proyecto:

- `config.py` con carga eager bloqueante
- CEDEARs sin `finviz_map` descartados silenciosamente
- `Peso_%` roto por suma cero o `NaN`
- `mep_real` tratado por truthiness accidental
- fondeo usando una sola fuente de liquidez
- cache de Bonistas sin cota
- duplicacion principal entre `assign_base_action(...)` y `assign_action_v2(...)`
- cobertura inexistente de clientes principales
- ausencia de `requirements.txt`

### Hallazgos validos pero reclasificados

Estos puntos siguen siendo razonables, pero no son bugs P0:

- scoring relativo sin piso absoluto
- narrativa con thresholds absolutos que no siempre refleja el ranking relativo
- validacion de input CLI mejorable en `generate_real_report.py`
- inferencia por prefijos en taxonomia/local bond analytics aun embebida en codigo

### Hallazgos vigentes que si conviene trabajar

- posible mejora de la capa tecnica de reduccion
- evolucion del scoring absoluto vs relativo
- mejoras de DX e infraestructura (`CI`, tooling)

## Backlog vigente

## P1. Reproducibilidad y colaboracion

### 1. Formalizar setup de clone limpio

- estado: `Resuelto`
- impacto: `Alto`
- complejidad: `Baja`

Trabajo cerrado:

1. seccion explicita de clone limpio en `README.md`
2. referencia directa a `data/examples/README.md`
3. script de bootstrap opcional para copiar ejemplos a rutas reales

### 2. Evaluar CI minima

- estado: `Pendiente`
- impacto: `Medio/Alto`
- complejidad: `Media`

Propuesta:

1. workflow simple de `unittest`
2. correr al menos:
   - `tests.test_strategy_rules`
   - `tests.test_sizing`
   - `tests.test_report_render`
   - clientes principales

## P2. Calidad del motor

### 3. Revisar scoring absoluto vs relativo

- estado: `Pendiente`
- impacto: `Alto`
- complejidad: `Media`

Motivo:

- el ranking relativo siempre produce ganadores y perdedores
- eso no siempre coincide con un mercado donde nadie merece refuerzo

Propuesta:

1. no tocar `rank_score(...)` global
2. experimentar un gate absoluto solo sobre `score_refuerzo`
3. validar en snapshots reales antes de mover baseline

### 4. Revisar señal tecnica de reduccion

- estado: `Pendiente`
- impacto: `Medio`
- complejidad: `Media`

Motivo:

- hoy ya no existe el bug viejo de `1 - tech_refuerzo`
- pero sigue siendo valido revisar si la pata de reduccion debe ser mas independiente

Propuesta:

1. testear casos extremos:
   - oversold
   - overbought
   - momentum positivo fuerte
   - tecnico mixto
2. decidir si la reduccion tecnica necesita pesos o transforms propios adicionales

### 5. Alinear narrativa con scoring

- estado: `Pendiente`
- impacto: `Medio`
- complejidad: `Baja/Media`

Motivo:

- ya se mejoro `_join_reasons(...)`
- todavia puede haber desacoples entre thresholds absolutos del texto y ranking relativo del score

Propuesta:

1. revisar `narrative_thresholds`
2. decidir si ciertas señales deben derivarse de percentiles internos y no de umbrales fijos

## P3. DX e infraestructura

### 6. Crear `pyproject.toml`

- estado: `Resuelto`
- impacto: `Medio`
- complejidad: `Baja`

Trabajo cerrado:

1. metadata minima del proyecto
2. dependencias base declaradas para tooling moderno

### 7. Hardening del CLI real

- estado: `Pendiente`
- impacto: `Medio/Bajo`
- complejidad: `Baja`

Motivo:

- el ingreso manual de montos externos todavia puede mejorar

Propuesta:

1. validar input vacio, texto invalido y negativos
2. devolver mensajes de error claros sin romper la corrida

## Orden sugerido

1. CI minima
2. experimento controlado de scoring absoluto vs relativo
3. revision fina de tecnica de reduccion
4. alineacion final de narrativa
5. hardening del CLI real

## Criterio de cierre

Esta auditoria se considera absorbida cuando:

- no queden hallazgos tecnicos activos confundidos con issues ya resueltos
- el setup minimo de colaboracion sea evidente
- el siguiente trabajo pendiente ya sea evolutivo, no correctivo
