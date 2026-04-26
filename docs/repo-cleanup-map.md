# Mapa de Limpieza del Repo

Documento operativo para decidir que se puede borrar y bajo que condiciones, sin mezclar deuda tecnica con material historico util.

## Borrable ahora (bajo control de commit)

1. `reports/real-report.html`
2. `reports/smoke-report.html`

Motivo:

- son artefactos generados
- cambian seguido y agregan ruido en diffs
- se pueden regenerar con `scripts/generate_real_report.py` y `scripts/generate_smoke_report.py`

Accion sugerida:

- decidir si se dejan versionados por conveniencia visual o si se pasan a no versionados con regla de `.gitignore`

## Borrable ahora (local, no versionado)

1. `data/runtime/decision_history.csv`
2. `data/runtime/prediction_history.csv`
3. carpetas temporales `tmp_*` que puedan quedar tras cortes de tests

Motivo:

- son artefactos de runtime
- no forman parte del contrato versionado
- su regeneracion no afecta el codigo fuente

## Borrable despues (condicional)

1. `tests/snapshots/*.csv|*.json`

Condiciones para borrar:

- retirar fallback legacy (`ENABLE_LEGACY_SNAPSHOTS`)
- confirmar ventana operativa suficiente en `data/snapshots/`
- validar que no haya pruebas o scripts que dependan de esos archivos

## Mantener (no borrar)

1. `docs/archive/*`

Motivo:

- trazabilidad historica de auditorias y decisiones
- util para explicar cambios de arquitectura y cierres de deuda

## Checklist antes de borrar algo versionado

1. buscar referencias: `rg -n "<ruta_o_patron>"`
2. correr pruebas relevantes (minimo suites de reporte y snapshots)
3. actualizar docs (`README.md`, `docs/README.md`, `tests/README.md`) si cambia contrato operativo
