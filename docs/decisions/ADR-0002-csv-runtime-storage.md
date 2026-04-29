# ADR-0002: Persistencia operativa en CSV (sin DB por ahora)

- Estado: Aceptado
- Fecha: 2026-04-28

## Contexto

El producto es single-user/local-first. Los historiales operativos (`decision_history`, `prediction_history`) hoy se consumen y depuran con tooling simple.

## Decision

Mantener persistencia operativa en CSV/JSON bajo `data/runtime/` y `data/snapshots/`, sin introducir base de datos en esta fase.

## Consecuencias

- Positivas:
  - simplicidad operativa y distribucion por ZIP
  - inspeccion y backup directos de archivos
  - menor complejidad para soporte local
- Negativas:
  - riesgo de corrupcion de archivo individual
  - crecimiento indefinido sin politicas de retencion
  - menor integridad transaccional comparado con DB

## Mitigaciones vigentes

- backup diario automatico de `data/runtime/*.csv`
- validaciones defensivas de lectura en pipeline

## Re-evaluacion

Revisar esta decision si:

- se requiere multiusuario,
- se agregan escrituras concurrentes,
- o el volumen de historial vuelve costosa la operacion por archivos.

