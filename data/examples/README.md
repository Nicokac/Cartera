# Ejemplos de Configuracion

Esta carpeta documenta la forma esperada de los JSON reales que usa el proyecto.

## Politica actual

- los JSON reales de `data/mappings/` y `data/strategy/` no se versionan
- el repo mantiene solo ejemplos `.json.example`
- los archivos reales se construyen copiando estos ejemplos y ajustando valores

## Como usar

Opcion recomendada:

```powershell
python scripts\bootstrap_example_config.py
```

Eso crea, si faltan:

- `data/mappings/*.json`
- `data/strategy/*.json`

Incluye tambien:

- `data/mappings/prediction_weights.json`

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
