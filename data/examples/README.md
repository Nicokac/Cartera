# Ejemplos de Configuracion

Esta carpeta documenta la forma esperada de los JSON reales que usa el proyecto.

## Politica actual

- los JSON de `data/strategy/` no se versionan
- varios mappings canonicos de `data/mappings/` si se versionan en git
- el repo mantiene `.json.example` para bootstrap y para documentar el contrato esperado
- los archivos faltantes se pueden crear copiando estos ejemplos y ajustando valores

Politica elegida para esta carpeta:

- `data/examples/` no es un espejo 1:1 de `data/mappings/`
- los `.json.example` existen solo para archivos bootstrappeables o para contratos que conviene documentar de forma minima
- un mapping canonico versionado puede no tener `.json.example` y eso no se considera inconsistencia por si sola

Mappings canonicos hoy versionados:

- `argentina_equity_map.json`
- `block_map.json`
- `bond_local_subfamily_rules.json`
- `finviz_map.json`
- `instrument_profile_map.json`
- `prediction_weights.json`
- `ratios.json`
- `vn_factor_map.json`

## Como usar

Opcion recomendada:

```powershell
python scripts\bootstrap_example_config.py
```

Eso crea, si faltan:

- `data/strategy/*.json`
- cualquier `data/mappings/*.json` que tenga `.json.example` y no exista localmente

Incluye tambien:

- `data/mappings/prediction_weights.json`

Ese archivo ahora tambien define el bloque:

- `calibration.min_samples`
- `calibration.min_weight`
- `calibration.max_weight`

Opciones utiles:

```powershell
python scripts\bootstrap_example_config.py --dry-run
python scripts\bootstrap_example_config.py --overwrite
```

## Alcance

Los ejemplos no replican tus datos reales ni tu estrategia exacta.

Sirven para:

- mostrar estructura esperada
- facilitar bootstrap desde un clone limpio
- explicar el contrato de configuracion del proyecto

## Regla de mantenimiento

- si cambia el contrato esperado por `src/` o `scripts/`, primero se actualiza el `.json.example`
- los ejemplos deben seguir siendo suficientes para que CI y un clone limpio puedan bootstrapping sin credenciales reales
- la documentacion de esta carpeta debe reflejar que algunos mappings reales ya viven versionados en `data/mappings/`
- no agregar `.json.example` solo para mantener simetria visual con archivos ya versionados
