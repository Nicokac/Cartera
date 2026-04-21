# Roadmap del Motor de Prediccion Direccional

## Vigencia

Documento creado el `2026-04-19`. Define la arquitectura objetivo, las fases de implementacion y el criterio de avance del motor de prediccion direccional.

Este documento describe el plan y el contrato tecnico. La bitacora de ejecucion real vive en [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md).

## Estado actual

- estado: `fase 6.1 completada`
- baseline funcional: el motor ya forma parte del pipeline experimental y del renderer
- dependencias nuevas: `ninguna`
- acoplamiento permitido: solo por integracion con `pipeline.py`, `market_data` y el renderer cuando la fase de exposicion llegue

## Motor vigente

El predictor actual es un `weighted signal consensus` sobre `6` senales.

Formula vigente:

```python
consensus_raw = sum(vote * weight) / sum(weight)
direction = "up" if consensus_raw > direction_threshold else "down" if consensus_raw < -direction_threshold else "neutral"
net_strength = abs(consensus_raw)
agreement_ratio = abs(weighted_sum) / active_weight
confidence = net_strength * agreement_ratio
```

Propiedades vigentes:

- cada senal vota `+1`, `0` o `-1`
- los pesos viven en `data/mappings/prediction_weights.json`
- la calibracion usa `IC` historico contra `outcome_numeric`
- la banda neutral del verificador sale de `neutral_return_band`
- el predictor expone:
  - `consensus_raw`
  - `net_strength`
  - `agreement_ratio`
  - `confidence`

Interpretacion correcta del estado actual:

- `consensus_raw` mantiene la intensidad neta firmada del consenso
- `net_strength` expone esa intensidad en valor absoluto
- `agreement_ratio` mide acuerdo entre senales activas, no participacion total
- `confidence` ya no es sinonimo de `abs(consensus_raw)`:
  - ahora penaliza desacuerdo entre senales activas
- los votos siguen siendo discretos; todavia no capturan magnitud interna de cada senal
- el esquema sigue siendo experimental y observacional

## Principio de diseno

El objetivo no es reemplazar el motor de decision actual sino agregar una capa experimental, auditable y desacoplada de prediccion direccional.

La primera iteracion se apoya en consenso ponderado de senales ya disponibles en el pipeline:

- RSI
- momentum 20d
- momentum 60d
- tendencia tecnica
- score unificado
- regimen de mercado

Cada senal vota `+1`, `-1` o `0`. El consenso agregado define:

- `direction`: `up`, `down` o `neutral`
- `confidence`: magnitud del consenso
- `votes`: detalle por senal

## Limitaciones auditables del estado actual

Estas limitaciones ya existen en el codigo actual y deben considerarse deuda conocida, no comportamiento implicito:

1. votos ternarios:
   - se pierde magnitud de la senal
   - casos apenas arriba del umbral y casos extremos votan igual
2. `IC <= 0`:
   - hoy la calibracion manda la senal a `min_weight`
   - eso evita apagarla por completo, pero deja una contribucion positiva minima aun cuando la relacion historica haya sido adversa
3. `confidence`:
   - ya incorpora acuerdo entre senales activas
   - todavia no incorpora participacion total o cobertura efectiva sobre el universo de senales
4. calibracion historica completa:
   - el `IC` no usa ventana rolling
   - puede reaccionar lento frente a drift de regimen
5. `neutral_return_band` global:
   - la misma banda se aplica a activos con perfiles de volatilidad muy distintos
6. cobertura de senales:
   - faltan senales de fuerza de tendencia y volumen relativo
   - las senales actuales no capturan toda la informacion tecnica disponible

## Objetivos no funcionales

- sin dependencia de API externa ni LLM en la primera version
- comportamiento deterministico
- trazabilidad completa por corrida y por ticker
- calibracion incremental solo con evidencia historica suficiente
- cero impacto sobre `decision/` mientras la capa siga experimental

## Supuestos tecnicos

- `technical.py` y `scoring.py` ya exponen la materia prima necesaria
- `market_data.fetch_price_history` es suficiente para verificar outcomes
- `data/runtime/` puede alojar historiales operativos nuevos
- el renderer puede incorporar una seccion nueva sin redefinir el contrato actual del HTML

## Senales candidatas

| Senal | Fuente | Columna esperada | Tipo de voto inicial |
|---|---|---|---|
| RSI | `src/analytics/technical.py` | `RSI_14` | contrarian |
| Momentum 20d | `src/analytics/technical.py` | `Momentum_20d_%` | tendencia |
| Momentum 60d | `src/analytics/technical.py` | `Momentum_60d_%` | tendencia |
| Tendencia tecnica | `src/analytics/technical.py` | `Tech_Trend` | categorial |
| Score unificado | `src/decision/scoring.py` | `score_unificado` | ranking / umbral |
| Regimen de mercado | pipeline | `market_regime_any_active` o equivalente | ajuste de contexto |

## Convenciones de trazabilidad

Cada fase implementada debe actualizar tres lugares:

1. este documento:
   - cambiar estado de la fase
   - ajustar contratos si el codigo real difiere del plan
2. [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md):
   - registrar fecha
   - commit
   - decision tecnica
   - archivos tocados
3. `docs/baseline-actual.md`:
   - solo cuando una fase ya forme parte de la baseline funcional o experimental operativa

## Fases

### Fase 1. Store de predicciones

**Estado:** `completada`

**Objetivo**

Persistir cada prediccion en un historial estructurado bajo `data/runtime/`.

**Archivos esperados**

- `src/prediction/store.py`
- `data/runtime/prediction_history.csv`

**Archivos implementados**

- `src/prediction/store.py`
- `src/prediction/__init__.py`
- `tests/test_prediction_store.py`
- `data/runtime/README.md`

**Contrato minimo**

| Campo | Tipo | Descripcion |
|---|---|---|
| `run_date` | date | fecha de la prediccion |
| `ticker` | str | ticker IOL |
| `direction` | str | `up`, `down`, `neutral` |
| `confidence` | float | magnitud normalizada del consenso |
| `consensus_raw` | float | consenso sin redondeo |
| `signal_votes` | JSON str | votos por senal |
| `horizon_days` | int | horizonte de verificacion |
| `outcome_date` | date | fecha teorica de validacion |
| `outcome` | str | vacio hasta verificar |
| `correct` | bool/null | vacio hasta verificar |

**Notas de implementacion**

- no usar este store para decisiones operativas
- dejar el CSV preparado para crecer sin migraciones complejas
- si el historial contiene datos reales, no versionarlo

**Criterio de salida**

- lectura y escritura deterministicas
- tests de append, carga vacia y roundtrip basico

**Estado de salida**

- store implementado con:
  - `build_prediction_observation`
  - `load_prediction_history`
  - `upsert_prediction_history`
  - `save_prediction_history`
- normalizacion de:
  - fechas
  - ticker
  - `signal_votes`
  - reemplazo por rerun usando clave `run_date + ticker + horizon_days`
- tests base cerrados

### Fase 2. Configuracion de pesos y umbrales

**Estado:** `completada`

**Objetivo**

Externalizar pesos iniciales y reglas de voto a un JSON.

**Archivo esperado**

- `data/mappings/prediction_weights.json`

**Archivos implementados**

- `data/mappings/prediction_weights.json`
- `data/examples/mappings/prediction_weights.json.example`
- `src/config.py`
- `tests/test_config.py`

**Contenido esperado**

- `horizon_days`
- `direction_threshold`
- `neutral_return_band`
- bloque `signals` con `weight` y `vote_rules`

**Regla**

Los umbrales iniciales pueden ser heuristicas, pero deben quedar documentados en este archivo y no hardcodeados en `predictor.py`.

**Criterio de salida**

- el predictor puede correr solo leyendo este JSON
- tests de carga y defaults minimos

**Estado de salida**

- pesos y umbrales iniciales definidos en archivo canonico
- ejemplo agregado al bootstrap de clones limpios
- acceso centralizado disponible via `config.PREDICTION_WEIGHTS`
- cobertura minima agregada en `tests.test_config`

### Fase 3. Predictor

**Estado:** `completada`

**Objetivo**

Convertir una fila enriquecida del pipeline en direccion, confianza y votos auditables.

**Archivos esperados**

- `src/prediction/__init__.py`
- `src/prediction/predictor.py`

**Archivos implementados**

- `src/prediction/predictor.py`
- `src/prediction/__init__.py`
- `tests/test_prediction_predictor.py`

**Firma esperada**

```python
def predict(row: dict, weights: dict) -> dict:
    ...
```

**Salida minima**

```python
{
    "direction": "up",
    "confidence": 0.56,
    "consensus_raw": 0.56,
    "votes": {"rsi": 1, "momentum_20d": 1, "sma_trend": -1},
}
```

**Criterio de salida**

- tests unitarios por senal
- test de consenso ponderado
- test de threshold a `neutral`

**Estado de salida**

- predictor puro implementado con:
  - `vote_signal`
  - `predict`
- cobertura cerrada para:
  - votos por senal
  - consenso alcista
  - consenso bajista
  - neutral por threshold
  - faltantes como voto neutro
- la fase todavia no integra pipeline ni store automatico

### Fase 4. Verificador

**Estado:** `completada`

**Objetivo**

Completar outcomes vencidos comparando precio en `run_date` contra precio en `outcome_date`.

**Archivo esperado**

- `src/prediction/verifier.py`

**Archivos implementados**

- `src/prediction/verifier.py`
- `src/prediction/__init__.py`
- `tests/test_prediction_verifier.py`

**Decisiones obligatorias**

- definir banda de retorno para `neutral`
- definir politica para fechas no habiles
- definir que hacer cuando falte precio de entrada o salida

**Criterio de salida**

- las predicciones vencidas pueden pasar de `pendiente` a `outcome`
- tests con casos `up`, `down`, `neutral` y datos faltantes

**Estado de salida**

- verificador implementado con:
  - `classify_outcome`
  - `build_verification_period`
  - `resolve_close_on_or_after`
  - `verify_prediction_history`
- la banda neutral se toma desde `prediction_weights.json` salvo override explicito
- politica de fechas no habiles:
  - se usa la primera rueda disponible `>= fecha objetivo`
- politica de datos faltantes:
  - si falta precio de entrada o salida, la prediccion queda pendiente

### Fase 5. Calibracion de pesos

**Estado:** `completada`

**Objetivo**

Ajustar pesos con evidencia historica usando IC o una metrica equivalente.

**Archivo esperado**

- `src/prediction/calibration.py`

**Archivos implementados**

- `src/prediction/calibration.py`
- `src/prediction/__init__.py`
- `tests/test_prediction_calibration.py`
- `data/mappings/prediction_weights.json`
- `data/examples/mappings/prediction_weights.json.example`

**Regla de seguridad**

No recalibrar con menos de `30` outcomes utiles salvo que se documente una excepcion explicita.

**Notas**

- calibrar contra outcome real, no solo contra `correct`
- preservar un peso minimo para no apagar completamente una senal sin evidencia suficiente

**Criterio de salida**

- los pesos cambian con datos reales
- se versiona una estrategia explicita de recalibracion

**Estado de salida**

- calibracion implementada contra outcome ternario `-1 / 0 / 1`
- si no hay muestra minima, el peso se conserva y la senal queda marcada como `insufficient_samples`
- si hay muestra suficiente:
  - `IC > 0` ajusta el peso dentro de `[min_weight, max_weight]`
  - `IC <= 0` manda la senal al peso minimo
- la configuracion ahora incluye:
  - `calibration.min_samples`
  - `calibration.min_weight`
  - `calibration.max_weight`

### Fase 6. Integracion al pipeline y al reporte

**Estado:** `completada`

**Objetivo**

Integrar el motor como capa experimental visible, sin alterar el motor de decision.

**Archivos esperados**

- `src/pipeline.py`
- `scripts/report_renderer.py`
- `scripts/run_prediction_cycle.py`

**Archivos implementados**

- `src/pipeline.py`
- `src/__init__.py`
- `scripts/generate_real_report.py`
- `scripts/smoke_run.py`
- `scripts/smoke_output.py`
- `scripts/report_renderer.py`
- `scripts/run_prediction_cycle.py`
- `tests/test_pipeline.py`
- `tests/test_smoke_run.py`
- `tests/test_smoke_output.py`
- `tests/test_report_render.py`
- `tests/test_prediction_cycle.py`

**Reglas**

- la prediccion no debe contaminar scoring ni sizing
- la seccion HTML debe poder ocultarse si no hay predicciones disponibles
- el runner puede ejecutar:
  - prediccion
  - store
  - verificacion
  - calibracion condicional

**Criterio de salida**

- la corrida genera predicciones persistidas
- el reporte puede mostrarlas sin romper el flujo actual

**Estado de salida**

- `build_prediction_bundle(...)` queda integrado al pipeline canonico
- `generate_real_report.py` ya:
  - construye el bundle de prediccion
  - persiste observaciones en `prediction_history.csv`
  - expone la seccion `Prediccion` en el HTML
- `smoke_run.py` y `smoke_output.py` incluyen la capa experimental para validar el flujo sin APIs reales
- `report_renderer.py` agrega:
  - navegacion condicional a `Prediccion`
  - resumen ejecutivo de predicciones
  - tabla colapsable con direccion, confianza, score y votos por senal
- `scripts/run_prediction_cycle.py` ejecuta el ciclo de mantenimiento:
  - carga historial
  - verifica outcomes vencidos
  - recalibra pesos
  - persiste historial y pesos

**Contrato operativo vigente**

- `generate_real_report.py` es el punto canonico de alta de observaciones nuevas:
  - corre pipeline
  - arma `prediction_bundle`
  - persiste `history_observation` en `prediction_history.csv`
  - deja visible la capa experimental en el HTML
- `run_prediction_cycle.py` es un runner de mantenimiento:
  - no genera predicciones nuevas
  - solo trabaja sobre el historial ya persistido
  - verifica outcomes vencidos y recalibra pesos si corresponde
- orden recomendado de uso:
  1. correr `generate_real_report.py` para registrar una nueva corrida
  2. correr `run_prediction_cycle.py` al cierre de rueda o en un job separado para mantenimiento historico

**Separacion intencional**

- esta separacion evita mezclar:
  - generacion de observaciones nuevas
  - mantenimiento historico y recalibracion
- tambien reduce el riesgo de que un runner de mantenimiento agregue filas duplicadas o predicciones fuera de contexto de reporte

### Fase 6.1. Correccion de escala del voto `score_unificado`

**Estado:** `completada`

**Objetivo**

Corregir el sesgo bajista estructural introducido por usar umbrales incompatibles con la escala real de `score_unificado`.

**Archivos implementados**

- `data/mappings/prediction_weights.json`
- `data/examples/mappings/prediction_weights.json.example`
- `tests/test_prediction_predictor.py`

**Decision tecnica**

- el `score_unificado` real del proyecto opera en escala centrada alrededor de cero, no en rango `0..1`
- por eso el voto ahora usa:
  - `high_threshold = 0.1`
  - `low_threshold = -0.1`

**Criterio de salida**

- nombres con score positivo moderado ya no votan bajista por defecto
- el predictor conserva neutralidad cerca de cero
- quedan tests de guardia para los tres casos: positivo, negativo y neutro

### Fase 6.2. Hardening interno del consenso

**Estado:** `en curso`

**Objetivo**

Mejorar el motor actual sin cambiar la arquitectura base ni requerir columnas nuevas en el pipeline.

**Alcance tecnico esperado**

- apagar senales con `IC <= 0` en lugar de llevarlas obligatoriamente a `min_weight`
- separar `confidence` de `consensus_raw`
- agregar una metrica de dispersion o acuerdo entre senales
- evaluar votos continuos en rango acotado `[-1, 1]` para senales donde hoy el voto es ternario por umbral

**Secuencia recomendada**

1. cambio de seguridad:
   - `IC <= 0 -> weight = 0`
2. cambio semantico:
   - renombrar o redefinir `confidence` para que no prometa mas de lo que mide
3. cambio de expresividad:
   - migrar gradualmente de votos ternarios a continuos donde sea defendible

**Estado actual de ejecucion**

- subpaso 1 abierto:
  - cerrado:
    - la calibracion deja de mandar `IC <= 0` a `min_weight`
    - la nueva regla vigente pasa a ser `IC <= 0 -> weight = 0`
- subpaso 2 abierto:
  - `confidence` deja de ser solo `abs(consensus_raw)`
  - se agrega `agreement_ratio` y `net_strength`
  - `confidence` pasa a ser intensidad neta ajustada por acuerdo
- subpaso 3 sigue pendiente:
  - abierto en modo opt-in:
    - el predictor ya soporta `vote_mode = continuous` para senales numericas
    - los pesos canonicos todavia no lo activan por default
    - falta decidir en que senales y con que parametros queda habilitado operativamente

**Criterio de salida**

- sin romper store, verifier ni renderer
- tests unitarios nuevos para:
  - `IC` negativo
  - ausencia de contribucion cuando el peso se apaga
  - diferencia entre intensidad neta y dispersion
  - clipping y neutralidad en votos continuos

### Fase 6.3. Calibracion rolling

**Estado:** `planificada`

**Objetivo**

Hacer que la calibracion responda mejor a drift de utilidad sin abandonar el fallback historico.

**Alcance tecnico esperado**

- agregar ventana rolling configurable en `calibration`
- usar muestra reciente cuando cumpla minimo estadistico
- caer al historico completo cuando la ventana reciente no alcance

**Configuracion candidata**

- `calibration.lookback_samples`
- `calibration.min_recent_samples`
- `calibration.fallback_to_full_history`

**Criterio de salida**

- el comportamiento queda documentado y deterministico
- la muestra reciente no introduce ruido excesivo por falta de datos

### Fase 7. Expansion de senales

**Estado:** `planificada`

**Objetivo**

Sumar informacion nueva solo despues de endurecer el uso de las senales actuales.

**Senales candidatas prioritarias**

- `ADX`:
  - fuerza de tendencia
- `relative_volume`:
  - volumen actual vs media de `20d`

**Dependencias**

- nuevas columnas en el pipeline tecnico
- tests de integracion y de predictor
- actualizacion de `prediction_weights.json`

**Criterio de entrada**

- Fase 6.2 cerrada
- Fase 6.3 al menos implementada o descartada explicitamente

## Recomendacion tecnica vigente

Orden recomendado de mejora:

1. Fase 6.2
2. Fase 6.3
3. Fase 7

Razon:

- primero conviene mejorar como el motor usa las senales existentes
- despues conviene hacer la calibracion mas reactiva
- recien entonces agregar nuevas features al pipeline

## Riesgos principales

### Calidad de datos

- huecos de mercado
- simbolos con mapping imperfecto
- fechas no habiles
- retornos espurios por datos faltantes

### Sobreajuste temprano

- pocos outcomes pueden mover pesos por ruido
- umbrales muy agresivos pueden producir confianza artificial

### Redundancia de senales

- momentum 20d, momentum 60d y tendencia tecnica no son independientes
- el consenso no debe interpretarse como evidencia estadisticamente ortogonal

## Criterios de exito

El track se considera util cuando:

1. supera `55%` de acierto direccional sostenido en una muestra suficiente
2. la calibracion produce pesos divergentes de los iniciales
3. la capa se mantiene auditable y desacoplada del motor de decisiones

## Fuera de alcance inicial

- integrar LLM externo
- reemplazar scoring o sizing
- entrenar un clasificador supervisado desde el dia 1
- usar la prediccion como input obligatorio para la accion final

## Evolucion futura posible

Si la capa de consenso llega a una base historica suficiente, se puede sumar una opcion B:

- `scikit-learn` sobre `signal_votes`
- calibracion comparativa entre modelo heuristico y clasificador
- seleccion de predictor sin romper store, verifier ni renderer
