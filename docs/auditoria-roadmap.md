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
- ausencia de metadata minima del proyecto
- falsos cortes de memoria temporal por alternancia entre efectivo y caucion operativa

### Hallazgos validos pero reclasificados

Estos puntos siguen siendo razonables, pero no son bugs P0:

- scoring relativo sin piso absoluto general
- inferencia por prefijos en taxonomia/local bond analytics aun embebida en codigo

### Hallazgos vigentes que si conviene trabajar

- calibraciones futuras del scoring absoluto vs relativo
- mejoras puntuales de DX e infraestructura solo si aparece evidencia real

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

- estado: `Resuelto`
- impacto: `Medio/Alto`
- complejidad: `Media`

Trabajo cerrado:

1. workflow simple de `unittest`
2. bootstrap automatico de config de ejemplo
3. suites estables:
   - `tests.test_config`
   - `tests.test_strategy_rules`
   - `tests.test_sizing`
   - `tests.test_report_render`
   - clientes principales

## P2. Calidad del motor

### 3. Revisar scoring absoluto vs relativo

- estado: `Validado en corrida real`
- impacto: `Alto`
- complejidad: `Media`

Motivo:

- el ranking relativo siempre produce ganadores y perdedores
- eso no siempre coincide con un mercado donde nadie merece refuerzo

Avance actual:

1. no se toco `rank_score(...)` global
2. ya existe un gate absoluto suave y configurable en `absolute_scoring.refuerzo_gate`
3. hoy limita `Refuerzo` cuando el momentum de 20 dias es negativo y el tecnico no es alcista
4. corrida real `2026-04-09` validada:
   - `XLV` salio de `Refuerzo`
   - `GOOGL` siguio en `Refuerzo` con tecnico `Alcista`
   - `EEM` siguio en `Refuerzo` con momentum positivo y tecnico `Alcista`

Trabajo pendiente asociado:

1. revisar si necesita calibracion por subfamilia

### 4. Revisar senal tecnica de reduccion

- estado: `Resuelto`
- impacto: `Medio`
- complejidad: `Media`

Trabajo cerrado:

1. el subscore RSI de reduccion ya usa una curva propia
2. `oversold` penaliza menos la venta tecnica y `overbought` la refuerza
3. hay test explicito para verificar `overbought > oversold` en `tech_reduccion`

### 5. Alinear narrativa con scoring

- estado: `Resuelto`
- impacto: `Medio`
- complejidad: `Baja/Media`

Trabajo cerrado:

1. `_join_reasons(...)` ya puede mostrar hasta tres senales sin volver el texto verboso
2. la narrativa ahora puede surfacer calidad y valuacion relativas cuando los thresholds absolutos no alcanzan
3. `ganancia extendida` deja de quedar tapada por senales relativas mas debiles

### 6. Hacer visible el fallback de UST/FRED

- estado: `Resuelto`
- impacto: `Medio`
- complejidad: `Baja`

Trabajo cerrado:

1. `build_real_bonistas_bundle(...)` ahora marca `ust_status`
2. el reporte HTML muestra cuando `FRED` no estuvo disponible
3. hay tests para el bundle real y el render

## P3. DX e infraestructura

### 7. Crear `pyproject.toml`

- estado: `Resuelto`
- impacto: `Medio`
- complejidad: `Baja`

Trabajo cerrado:

1. metadata minima del proyecto
2. dependencias base declaradas para tooling moderno

### 8. Hardening del CLI real

- estado: `Resuelto`
- impacto: `Medio/Bajo`
- complejidad: `Baja`

Trabajo cerrado:

1. `prompt_yes_no(...)` ahora reintenta hasta recibir una respuesta valida
2. `prompt_money_ars(...)` ya no rompe la corrida con texto invalido o montos negativos
3. hay tests explicitos para ambos prompts

### 9. Continuidad temporal de liquidez operativa

- estado: `Resuelto`
- impacto: `Bajo/Medio`
- complejidad: `Baja`

Trabajo cerrado:

1. `CASH_ARS` y `CAUCION` comparten continuidad temporal en la memoria observacional
2. se evita marcar falsos `sin_historial` cuando la caja diaria rota a caucion
3. hay test explicito para esa equivalencia operativa

## Orden sugerido

1. calibraciones futuras de scoring con nuevas corridas reales
2. limpieza final de deuda menor si aparece evidencia real

## Criterio de cierre

Esta auditoria se considera absorbida cuando:

- no queden hallazgos tecnicos activos confundidos con issues ya resueltos
- el setup minimo de colaboracion sea evidente
- el siguiente trabajo pendiente ya sea evolutivo, no correctivo
