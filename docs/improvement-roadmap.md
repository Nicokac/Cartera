# Roadmap de Mejoras

## Criterio

La priorizacion activa combina:

- impacto funcional en corridas reales
- riesgo de regresion
- costo de mantenimiento futuro

## Estado general

El proyecto ya salio de la fase de hardening basico. El backlog vigente se concentra en:

1. bajar complejidad estructural del renderer
2. terminar de separar fixtures de smoke del codigo productivo
3. seguir calibrando scoring y reporte con evidencia real

## Resuelto recientemente

- snapshots operativos canonicos en `data/snapshots/`
- fallback legacy controlado por `ENABLE_LEGACY_SNAPSHOTS`
- README de snapshots con criterio de migracion explicito
- `rank_score` con damping progresivo para cohorts chicos
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
- CI ampliada a las suites activas del repo
- renderer desacoplado en modulos de primitives, operations y orquestacion
- flujo de operaciones IOL integrado al reporte con explicaciones operativas

## Backlog activo

### P1. Reducir deuda del renderer

- extraer mas secciones de `render_report()` a helpers puros
- reducir tamaño y complejidad cognitiva de `scripts/report_renderer.py`
- mantener contratos estables con `generate_smoke_report.py` y `generate_real_report.py`

### P2. Reubicar fixtures de smoke

- mover `scripts/smoke_fixtures.py` a una zona de fixtures de test
- evitar que mocks de pruebas vivan dentro del arbol de scripts operativos
- simplificar imports de `test_smoke_run.py` y `test_smoke_output.py`

### P3. Afinar calibraciones con evidencia real

- monitorear cohortes chicas luego del damping de `rank_score`
- revisar scoring y sizing solo cuando aparezcan corridas reales borderline
- mantener la narrativa del reporte alineada con cambios efectivos de decision

### P4. Cerrar migracion de snapshots

- retirar el fallback legacy cuando `data/snapshots/` tenga ventana suficiente
- mantener documentado el criterio de retiro
- evitar que vuelvan a aparecer snapshots operativos nuevos en `tests/snapshots/`

## Frentes ya absorbidos

Estos temas ya no son backlog activo salvo que reaparezcan con evidencia nueva:

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
