# Operational Snapshots

`data/snapshots/` es el directorio canonico para snapshots operativos generados por corridas reales.

## Objetivo

- guardar snapshots diarios usados por `generate_real_report.py`
- comparar la cartera actual contra la ultima foto valida previa
- sostener la feature de `position_transitions` fuera del arbol de tests
- mantener el historial operativo real separado de fixtures y snapshots legacy

## Convencion de nombres

- `YYYY-MM-DD_real_portfolio_master.csv`
- `YYYY-MM-DD_real_decision_table.csv`
- `YYYY-MM-DD_real_technical_overlay.csv`
- `YYYY-MM-DD_real_kpis.json`
- `YYYY-MM-DD_real_liquidity_contract.json`

## Estado actual de migracion

- `data/snapshots/` es el path canonico desde el commit `c1fd5bb`
- `tests/snapshots/` queda como directorio legacy y solo se consulta como fallback historico
- mientras no exista una migracion operativa explicita, los snapshots historicos previos pueden seguir viviendo en `tests/snapshots/`

## Politica recomendada

- toda corrida real nueva debe escribir en `data/snapshots/`
- no agregar snapshots operativos nuevos en `tests/snapshots/`
- si se necesita comparar contra snapshots historicos, el fallback legacy sigue habilitado temporalmente
- si un snapshot esta corrupto o no cumple el schema minimo, el runner debe descartarlo y seguir buscando uno valido

## Control del fallback legacy

`generate_real_report.py` consulta primero `data/snapshots/`.

Si `ENABLE_LEGACY_SNAPSHOTS` no esta desactivado, tambien puede consultar `tests/snapshots/` como fallback historico.

- valor por defecto: `ENABLE_LEGACY_SNAPSHOTS=1`
- para forzar solo el directorio canonico: `ENABLE_LEGACY_SNAPSHOTS=0`
- si se usa un snapshot legacy, el script emite un warning explicito en logs

## Criterio de retiro del fallback legacy

Se puede eliminar `LEGACY_SNAPSHOTS_DIR` del codigo cuando se cumplan estas dos condiciones:

1. exista al menos una ventana operativa suficiente de snapshots reales en `data/snapshots/`
2. ya no haya dependencia explicita de snapshots historicos alojados en `tests/snapshots/`

Hasta entonces, el fallback se mantiene solo por compatibilidad historica, no como directorio principal.
