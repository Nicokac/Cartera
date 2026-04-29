# Documentacion

Indice de la documentacion activa del proyecto.

## Puntos de entrada

- [README.md](../README.md)
- [baseline-actual.md](baseline-actual.md)
- [improvement-roadmap.md](improvement-roadmap.md)
- [prediction-engine-roadmap.md](prediction-engine-roadmap.md)
- [prediction-engine-history.md](prediction-engine-history.md)
- [report-ux-architecture.md](report-ux-architecture.md)
- [asset-taxonomy.md](asset-taxonomy.md)
- [instrument-onboarding-checklist.md](instrument-onboarding-checklist.md)
- [repo-cleanup-map.md](repo-cleanup-map.md)
- [decisions/README.md](decisions/README.md)

## Soporte operativo

- [data/examples/README.md](../data/examples/README.md)
- [data/snapshots/README.md](../data/snapshots/README.md)
- [tests/README.md](../tests/README.md)
- [tests/snapshots/README.md](../tests/snapshots/README.md)
- [data/reference/README.md](../data/reference/README.md)

## Criterio de mantenimiento

- `README.md`: instalacion, uso y layout del repo
- `baseline-actual.md`: capacidades vigentes y baseline funcional, sin depender de una corrida puntual
- `improvement-roadmap.md`: backlog tecnico activo y deuda real
- `prediction-engine-roadmap.md`: arquitectura, fases, contratos y criterios de avance del motor de prediccion direccional
- `prediction-engine-history.md`: bitacora de implementacion y cambios por fase del motor de prediccion
- `report-ux-architecture.md`: arquitectura vigente del reporte ya modularizado y criterio de evolucion visual
- `asset-taxonomy.md`: taxonomia efectiva del motor y fuentes de configuracion
- `data/snapshots/README.md`: directorio canonico de snapshots operativos
- `tests/snapshots/README.md`: legacy snapshots y contrato de fallback
- `repo-cleanup-map.md`: inventario de candidatos a borrado y condiciones
- el track de prediccion llego a Fase 7 (ADX continuo, `relative_volume`, `conviction_label`):
  - integrado al pipeline experimental
  - visible en el renderer HTML
  - con runner propio de verificacion y recalibracion
  - con separacion operativa explicita:
    - `generate_real_report.py` crea observaciones nuevas
    - `run_prediction_cycle.py` solo verifica y recalibra

## Regla de limpieza documental

- si una deuda tecnica ya fue cerrada en codigo y tests, no debe seguir figurando como backlog activo
- si un doc historico sigue siendo util solo por trazabilidad, debe vivir en `docs/archive/`

## Historico

`docs/archive/` guarda roadmaps absorbidos, auditorias cerradas y notas historicas. No es punto de entrada operativo y no debe tomarse como estado actual salvo que se lo consulte por trazabilidad.

Audits recientes:

- [audit-2026-04-24-2dbf950.md](archive/audit-2026-04-24-2dbf950.md) — extraccion `_build_risk_focus_block`, tests decision/actions
- [audit-2026-04-24-8284e87.md](archive/audit-2026-04-24-8284e87.md) — modulo riesgo historico, 317/317
- [audit-2026-04-20-f1081af.md](archive/audit-2026-04-20-f1081af.md) — auditoria factual estado repo
