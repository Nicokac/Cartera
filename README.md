# Cartera de Activos

Motor de analisis de cartera para IOL con foco en:

- consolidacion y valuacion de cartera
- scoring operativo para CEDEARs, acciones locales, bonos y liquidez
- overlay tecnico y contexto macro
- memoria temporal diaria entre corridas
- reporte HTML reproducible para smoke y real run

## Estado del proyecto

El repo esta en una etapa operativa estable:

- pipeline canonico concentrado en `src/`
- renderer HTML modularizado en `report_primitives`, `report_operations` y `report_renderer`
- flujo de operaciones reales integrado al reporte
- snapshots operativos movidos a `data/snapshots/` con fallback legacy controlado
- CI basada en `unittest` con `27` suites declaradas en `.github/workflows/ci.yml`

Resumen funcional vigente:

- [baseline-actual.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\baseline-actual.md)

## Estructura

- `src/`: logica canonica del motor
- `scripts/`: runners, renderer y utilitarios de soporte
- `data/`: snapshots, referencias y ejemplos de configuracion
- `docs/`: documentacion activa
- `docs/archive/`: historico y material absorbido
- `tests/`: suite de regresion y fixtures
- `reports/`: HTMLs generados

## Requisitos

- Python `3.12`
- acceso de red para corridas reales
- credenciales validas de IOL para el flujo real

## Instalacion

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Instalacion alternativa desde metadata del proyecto:

```powershell
pip install .
```

Extra opcional para herramientas BYMA:

```powershell
pip install .[byma]
```

## Clone limpio

Los JSON reales de `data/mappings/` y `data/strategy/` no se versionan. Para bootstrap minimo:

```powershell
python scripts\bootstrap_example_config.py
```

Eso copia los `.json.example` de `data/examples/` a sus rutas reales si todavia no existen.

Mas detalle:

- [data/examples/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\examples\README.md)

## Variables de entorno

```env
IOL_USERNAME=tu_usuario_iol@example.com
IOL_PASSWORD=tu_password_iol
FRED_API_KEY=tu_fred_api_key
ENABLE_LEGACY_SNAPSHOTS=1
```

Notas:

- `ENABLE_LEGACY_SNAPSHOTS=0` fuerza el uso exclusivo de `data/snapshots/`
- el runner real puede pedir credenciales por terminal si no estan cargadas

## Uso rapido

Smoke report:

```powershell
python scripts\generate_smoke_report.py
```

Validacion smoke interna:

```powershell
python scripts\smoke_run.py
```

Real run:

```powershell
python scripts\generate_real_report.py
```

## Tests

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Suites utiles:

```powershell
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_technical -v
python -m unittest tests.test_report_primitives -v
python -m unittest tests.test_report_operations -v
python -m unittest tests.test_report_render -v
python -m unittest tests.test_generate_real_report -v
```

CI actual:

- workflow: `.github/workflows/ci.yml`
- bootstrap automatico de configuracion de ejemplo antes de testear
- bateria estable del repo sin red real ni credenciales

## Memoria temporal

- historial diario en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha_efectiva_de_mercado`
- reruns del mismo dia reemplazan la observacion
- corridas de fin de semana o preapertura no inflan persistencia artificial
- el HTML expone:
  - `Accion previa`
  - `Delta Score`
  - `Racha`

## Documentacion

Entrada canonica:

- [docs/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\README.md)

Configuracion de ejemplo:

- [data/examples/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\examples\README.md)

Track de prediccion direccional:

- [docs/prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
- [docs/prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
