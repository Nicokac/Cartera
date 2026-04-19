# Historial del Motor de Prediccion Direccional

## Proposito

Bitacora operativa y tecnica del nuevo track de prediccion direccional.

Este documento no reemplaza el roadmap. Sirve para registrar:

- que fase se abrio o cerro
- que decisiones de diseno cambiaron
- que archivos se tocaron
- que deuda quedo abierta

## Regla de uso

Cada vez que se cierre una fase o un hito relevante, agregar una entrada nueva arriba de todo con este formato:

```md
## YYYY-MM-DD - Fase X - estado

- commit:
- alcance:
- decisiones:
- archivos:
- tests:
- deuda / notas:
```

No borrar entradas anteriores. Si una decision cambia, agregar una entrada nueva explicando el cambio.

## Estado consolidado

| Fase | Estado | Ultima actualizacion |
|---|---|---|
| Fase 1 - Store | completada | 2026-04-19 |
| Fase 2 - Pesos y umbrales | completada | 2026-04-19 |
| Fase 3 - Predictor | completada | 2026-04-19 |
| Fase 4 - Verificador | completada | 2026-04-19 |
| Fase 5 - Calibracion | pendiente | 2026-04-19 |
| Fase 6 - Integracion y reporte | pendiente | 2026-04-19 |

## 2026-04-19 - Fase 4 - completada

- commit: pendiente
- alcance:
  - se implementa el verificador de outcomes vencidos sobre `prediction_history.csv`
  - queda cerrada la semantica minima de resultado real
- decisiones:
  - `neutral` se determina con `neutral_return_band`
  - para fechas no habiles se toma el primer cierre disponible en fecha mayor o igual a la objetivo
  - si falta precio de entrada o salida, la prediccion queda pendiente y no se fuerza outcome
- archivos:
  - `src/prediction/verifier.py`
  - `src/prediction/__init__.py`
  - `tests/test_prediction_verifier.py`
- tests:
  - `up`
  - `down`
  - `neutral`
  - precio faltante
  - prediccion aun no vencida
- deuda / notas:
  - Fase 5 debe decidir si calibra sobre outcome ternario o binarizacion derivada
  - todavia no existe runner integrado que ejecute verificacion sobre el CSV real

## 2026-04-19 - Fase 3 - completada

- commit: pendiente
- alcance:
  - se implementa el predictor heuristico de consenso ponderado
  - queda separado como modulo puro, sin integracion todavia al pipeline
- decisiones:
  - el predictor consume `weights` externos, no lee config por su cuenta
  - cada senal vota `+1`, `-1` o `0`
  - el consenso usa `sum(weight * vote) / sum(weight)`
  - `market_regime` vota negativo solo con flags bajistas explicitos; si no hay flags y la regla lo habilita, vota positivo
- archivos:
  - `src/prediction/predictor.py`
  - `src/prediction/__init__.py`
  - `tests/test_prediction_predictor.py`
- tests:
  - voto de RSI
  - voto de momentum 20d y 60d
  - voto de tendencia tecnica
  - voto de score unificado
  - voto de market regime
  - consensos `up`, `down` y `neutral`
  - faltantes como neutral
- deuda / notas:
  - Fase 4 debe verificar outcomes reales
  - Fase 6 debe decidir como se mapea la fila del pipeline al `row` del predictor

## 2026-04-19 - Fase 2 - completada

- commit: pendiente
- alcance:
  - se define el archivo canonico de pesos y umbrales iniciales
  - se integra la configuracion nueva al sistema de mappings del proyecto
- decisiones:
  - `prediction_weights.json` vive en `data/mappings/`
  - se versiona tambien su `.json.example` para bootstrap de clones limpios
  - el acceso canonico queda en `config.PREDICTION_WEIGHTS`
- archivos:
  - `data/mappings/prediction_weights.json`
  - `data/examples/mappings/prediction_weights.json.example`
  - `src/config.py`
  - `tests/test_config.py`
  - `.gitignore`
- tests:
  - carga del mapping desde `config`
  - validacion minima de estructura base
- deuda / notas:
  - Fase 3 debe consumir esta configuracion sin hardcodes paralelos
  - la semantica exacta de cada `vote_rule` se cierra cuando exista `predictor.py`

## 2026-04-19 - Fase 1 - completada

- commit: pendiente
- alcance:
  - se implementa el store inicial del motor de prediccion
  - queda definido el contrato persistido en `data/runtime/prediction_history.csv`
- decisiones:
  - la clave de reemplazo por rerun es `run_date + ticker + horizon_days`
  - `signal_votes` se persiste como JSON string ordenado para facilitar auditabilidad
  - `outcome_date` se calcula en dias habiles con `BDay`
- archivos:
  - `src/prediction/store.py`
  - `src/prediction/__init__.py`
  - `tests/test_prediction_store.py`
  - `data/runtime/README.md`
- tests:
  - roundtrip save/load
  - normalizacion de observaciones
  - upsert por rerun
  - calculo de `outcome_date`
- deuda / notas:
  - Fase 2 debe externalizar `horizon_days` y umbrales a JSON
  - Fase 3 todavia no existe; el store no esta integrado al pipeline

## 2026-04-19 - Apertura del track - planificado

- commit: pendiente
- alcance:
  - se abre el track documental del motor de prediccion direccional
  - se separa el plan tecnico del historial de implementacion
- decisiones:
  - la primera version no usa LLM externo
  - el motor arranca como consenso ponderado de senales ya disponibles
  - la trazabilidad queda repartida entre roadmap, historial y baseline
- archivos:
  - `docs/prediction-engine-roadmap.md`
  - `docs/prediction-engine-history.md`
  - `docs/README.md`
  - `docs/improvement-roadmap.md`
  - `docs/baseline-actual.md`
- tests:
  - no aplica, cambio documental
- deuda / notas:
  - falta implementar Fase 1
  - cualquier cambio de contrato debe actualizar primero el roadmap y luego este historial
