# Cartera de Activos

Motor de analisis de cartera con foco en:

- consolidacion y valuacion desde IOL
- scoring operativo para CEDEARs, acciones locales, bonos y liquidez
- overlay tecnico y contexto macro
- memoria temporal diaria
- reporte HTML reproducible

## Estado actual

Baseline operativa vigente al `2026-04-09 23:33`:

- overlay tecnico `24/24`
- Finviz fundamentals `20/24`
- Finviz ratings `15/24`
- regimen de mercado visible en HTML
- memoria temporal diaria validada con cambio de fecha efectiva
- `6` refuerzos: `KO`, `EWZ`, `EEM`, `GOOGL`, `NEM`, `XLU`
- `2` reducciones: `MELI`, `AAPL`
- sizing vigente con fondeo externo de `$600,000`: `KO`, `EWZ`, `EEM`

Detalle completo:

- [baseline-actual.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\baseline-actual.md)

## Estructura

- `src/`: logica canonica del proyecto
- `scripts/`: runners y generacion de reportes
- `data/`: mappings, reglas, runtime y ejemplos
- `docs/`: documentacion activa e historica
- `tests/`: suite de regresion y snapshots
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

## Clone limpio

Los JSON reales de `data/mappings/` y `data/strategy/` no se versionan.

Bootstrap minimo:

```powershell
python scripts\bootstrap_example_config.py
```

Eso copia los `.json.example` de `data/examples/` a sus rutas reales si todavia no existen.

Documentacion asociada:

- [data/examples/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\examples\README.md)

## Variables de entorno

```env
IOL_USERNAME=tu_usuario_iol@example.com
IOL_PASSWORD=tu_password_iol
FRED_API_KEY=tu_fred_api_key
```

## Uso rapido

```powershell
python scripts\generate_smoke_report.py
python scripts\generate_real_report.py
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

Suites utiles:

```powershell
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_report_render -v
python -m unittest tests.test_generate_real_report -v
```

CI actual:

- workflow: `.github/workflows/ci.yml`
- corre la bateria estable completa del repo activo sin red real ni credenciales
- hace bootstrap automatico de configuracion de ejemplo antes de ejecutar tests

## Memoria temporal

- historial diario en `data/runtime/decision_history.csv`
- unidad canonica: `ticker + fecha`
- reruns del mismo dia reemplazan la observacion
- el HTML expone:
  - `Accion previa`
  - `Δ Score`
  - `Racha`

## Documentacion

Entrada canonica:

- [docs/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\README.md)

Configuracion de ejemplo para clones limpios:

- [data/examples/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\examples\README.md)
