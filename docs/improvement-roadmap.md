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
- logging estructurado en: `valuation`, `classify`, `bond_analytics`, `technical`
- smoke split en `smoke_run`, `smoke_fixtures`, `smoke_output`
- `smoke_fixtures` reubicado bajo `tests/`
- CI ampliada a las suites activas del repo
- renderer desacoplado en: `report_renderer`, `report_composer`, `report_layout`, `report_sections`, `report_decision`
- flujo de operaciones IOL integrado al reporte con explicaciones operativas
- snapshots endurecidos con coercion numerica defensiva
- contrato operativo explicito entre `generate_real_report.py` y `run_prediction_cycle.py`
- motor de prediccion: Fases 6.2 (zona muerta, RSI continuo, IC <= 0 apaga), 6.3 (rolling), 7 (ADX, relative_volume) completadas
- hardening de senales: votos graduados en `sma_trend`, escala continua en `relative_volume`
- `conviction_label` integrado en `predict()`, `prediction_history.csv` y reporte HTML
- PRPEDOB reclasificado como FCI de renta fija USD: sale de `FCI_CASH_MANAGEMENT`, entra a `FCI_REPORTED_AS_FUND`
- `build_position_transition_bundle` distingue alta genuina de reclasificacion taxonomica (`change_kind = "reclasificacion"`)
- `instrument_profile_map.json`: perfiles FCI agregados para ADBAICA, IOLPORA y PRPEDOB con `asset_family=fci`
- `analytics/portfolio_risk.py`: modulo de riesgo historico con universo comparable, `serie_confiable` como circuit breaker, quality labels y metadata de cobertura
- seccion de riesgo historico en el reporte con focus blocks por tipo (mercado / renta fija) y tabla filtrable por calidad e historia
- `_build_risk_focus_block` extraida de `build_summary_section` al nivel de modulo (O-008)
- `test_decision_actions.py`: 19 tests para `assign_base_action`, `assign_action_v2`, `enrich_decision_explanations` (O-007 cerrado)
- `test_decision_scoring.py`: 34 tests; se agrego cobertura unitaria directa para `build_decision_base`, escenarios absolutos en `apply_base_scores` y ramas avanzadas (`asset_subfamily_adjustments`, `market_regime`, `refuerzo_gate`)
- `test_portfolio_risk.py`: 9 tests; se agregaron edge cases de `serie_confiable=False` y exclusiones normalizadas de `CAUCION/CASH_USD/FCI` (O-009 cerrado)
- `test_report_sections.py`: 8 tests para `_build_risk_focus_block` (O-011 cerrado)
- CI ampliada a 37 suites (`test_market_regime_scoring`, `test_portfolio_risk`, `test_decision_actions`, `test_decision_scoring`, `test_report_sections` agregados)

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

- Fases 1–7 cerradas; hardening de senales continuas y `conviction_label` integrados
- mantener el motor desacoplado de `decision/` y del scoring operativo vigente
- deuda estructural pendiente (ambas bloqueadas por datos):
  - **calibracion por `asset_family`**: requiere >= 30 outcomes verificados por familia x senal antes de implementar; hoy todo corre con pesos globales
  - **multi-horizonte**: requiere cambios en store (clave compuesta), verifier (por horizonte) y renderer (tabla por horizonte)
- proximo objetivo cuando haya historial suficiente:
  - sumar metricas historicas de acierto al HTML
  - decidir si conviene una opcion B con clasificador sobre `signal_votes`
- registrar trazabilidad de cada fase en:
  - [prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
  - [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
- evitar dependencias nuevas o LLM externos mientras siga en etapa experimental

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
