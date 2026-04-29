# ADR-0003: Montos monetarios - float actual y migracion gradual a Decimal

- Estado: Aceptado
- Fecha: 2026-04-28

## Contexto

El pipeline historico usa `float` en calculos monetarios. Para mayor robustez contable, el roadmap prioriza migracion de montos criticos a `Decimal` en etapas.

## Decision

Mantener `float` como baseline actual y migrar gradualmente a `Decimal` en modulos de valuacion/sizing con mayor impacto, evitando un rewrite de alto riesgo en un solo paso.

## Consecuencias

- Positivas:
  - reduce riesgo de regresiones masivas
  - permite validar por etapas con tests dirigidos
  - facilita rollout incremental
- Negativas:
  - conviven temporalmente dos estrategias numericas
  - requiere disciplina para evitar conversiones inconsistentes

## Criterios de implementacion

- migrar primero calculos finales de montos y totales
- encapsular conversiones en funciones utilitarias claras
- ampliar tests de precision y redondeo por bloque migrado

