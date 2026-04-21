# Roadmap de Mejoras

## Criterio

La priorizacion activa combina:

- impacto funcional en corridas reales
- riesgo de regresion
- costo de mantenimiento futuro

## Estado general

El proyecto ya salio de la fase de hardening basico. El backlog vigente se concentra en:

1. seguir calibrando scoring y reporte con evidencia real
2. cerrar la migracion operativa de snapshots
3. consolidar el track de prediccion direccional auditada ya integrado sin tocar el motor de decision existente

## Resuelto recientemente

- snapshots operativos canonicos en `data/snapshots/`
- fallback legacy controlado por `ENABLE_LEGACY_SNAPSHOTS`
- README de snapshots con criterio de migracion explicito
- `rank_score` con damping progresivo para cohorts chicos
- tests de borde explicitos para `rank_score` en cohorts `N=3` y `N=4`
- cobertura directa de `report_primitives` y `report_operations`
- logging estructurado en:
  - `valuation`
  - `classify`
  - `bond_analytics`
  - `technical`
- smoke split en:
  - `smoke_run`
  - `smoke_fixtures`
  - `smoke_output`
- `smoke_fixtures` reubicado bajo `tests/` para separar fixtures del arbol de scripts operativos
- CI ampliada a las suites activas del repo
- renderer desacoplado en:
  - `report_renderer`
  - `report_composer`
  - `report_layout`
  - `report_sections`
  - `report_decision`
- flujo de operaciones IOL integrado al reporte con explicaciones operativas
- snapshots endurecidos con:
  - filas utilizables de `Ticker_IOL`
  - coercion numerica defensiva en columnas opcionales
- contrato operativo explicito entre:
  - `generate_real_report.py`
  - `run_prediction_cycle.py`

## Backlog activo

### P1. Afinar calibraciones con evidencia real

- monitorear cohortes chicas luego del damping de `rank_score`
- revisar scoring y sizing solo cuando aparezcan corridas reales borderline
- mantener la narrativa del reporte alineada con cambios efectivos de decision

### P2. Cerrar migracion de snapshots

- retirar el fallback legacy cuando `data/snapshots/` tenga ventana suficiente
- mantener documentado el criterio de retiro
- evitar que vuelvan a aparecer snapshots operativos nuevos en `tests/snapshots/`

### P3. Motor de prediccion direccional

- fase 6.1 ya cerrada:
  - store
  - predictor
  - verificacion
  - calibracion
  - integracion experimental a pipeline, reporte y runner
  - correccion de escala de `score_unificado`
- mantener el motor desacoplado de `decision/` y del scoring operativo vigente
- proximo objetivo:
  - sumar metricas historicas de acierto al HTML
  - decidir si conviene una opcion B con clasificador sobre `signal_votes`
- registrar trazabilidad de cada fase en:
  - [prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
  - [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
- evitar dependencias nuevas o LLM externos mientras siga en etapa experimental
- siguiente secuencia tecnica recomendada:
  - Fase 6.2:
    - apagar senales con `IC <= 0`
    - separar intensidad neta de dispersion en la metrica de confianza
    - evaluar votos continuos en lugar de ternarios donde aplique
  - Fase 6.3:
    - agregar calibracion rolling con fallback a historico completo
  - Fase 7:
    - recien despues sumar `ADX` y `relative_volume`

## Frentes ya absorbidos

Estos temas ya no son backlog activo salvo que reaparezcan con evidencia nueva:

- deuda estructural del renderer principal
- bootstrap de clones limpios
- metadata base del proyecto
- cobertura base y secundaria de clientes
- hardening del CLI real
- memoria temporal diaria
- taxonomia local de bonos externalizada
- calibracion prudente de Finviz
- UX base del reporte HTML

## Regla de mantenimiento

Si una mejora no cambia:

- la decision final
- la resiliencia operativa
- la trazabilidad del pipeline

entonces no deberia competir por prioridad contra deuda estructural real.
