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
| Fase 2 - Pesos y umbrales | pendiente | 2026-04-19 |
| Fase 3 - Predictor | pendiente | 2026-04-19 |
| Fase 4 - Verificador | pendiente | 2026-04-19 |
| Fase 5 - Calibracion | pendiente | 2026-04-19 |
| Fase 6 - Integracion y reporte | pendiente | 2026-04-19 |

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
