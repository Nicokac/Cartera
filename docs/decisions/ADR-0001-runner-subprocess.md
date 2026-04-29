# ADR-0001: Runner en subprocess para app local

- Estado: Aceptado
- Fecha: 2026-04-28

## Contexto

La app local web (`server.py`) ejecuta corridas reales que pueden tardar varios minutos, consumir red externa y fallar por causas operativas. Se necesita aislamiento entre el servidor y la corrida.

## Decision

Mantener la ejecucion del runner real (`scripts/generate_real_report.py`) en un `subprocess` lanzado desde `POST /run`.

## Consecuencias

- Positivas:
  - aislamiento de fallas del runner respecto del proceso web
  - posibilidad de cancelar corrida (`POST /cancel`)
  - logs centralizados por corrida (`data/runtime/server_run.log`)
- Negativas:
  - manejo adicional de ciclo de vida (PID, limpieza, estados)
  - necesidad de vigilar corridas huerfanas al reinicio del server

## Alternativas consideradas

- In-process/thread en el mismo servidor:
  - descartado por menor aislamiento y mayor riesgo de bloquear/degradar el server.

