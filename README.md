# Cartera de Activos

Motor de análisis de cartera con foco en:

- valuación y consolidación desde IOL
- scoring operativo de CEDEARs, acciones locales, bonos y liquidez
- overlay técnico
- contexto macro local
- reporte HTML reproducible
- snapshots y tests de regresión

## Estado actual

Baseline operativa vigente al `2026-04-08`:

- overlay técnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- memoria temporal diaria observacional ya validada con cambio de fecha efectiva
- régimen de mercado visible en el HTML

## Estructura

- `src/`: lógica canónica del proyecto
- `scripts/`: runners y generación de reportes
- `data/`: mappings, reglas, runtime y ejemplos
- `docs/`: documentación funcional y de arquitectura
- `tests/`: suite de regresión y snapshots
- `reports/`: HTMLs generados

## Requisitos

- Python `3.12` recomendado
- acceso de red para corridas reales
- credenciales válidas de IOL para el flujo real

Instalación:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Variables de entorno

```env
IOL_USERNAME=tu_usuario_iol@example.com
IOL_PASSWORD=tu_password_iol
FRED_API_KEY=tu_fred_api_key
```

## Uso rápido

```powershell
python scripts\generate_smoke_report.py
python scripts\generate_real_report.py
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

Suites puntuales:

```powershell
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_report_render -v
python -m unittest tests.test_generate_real_report -v
```

## Memoria temporal

- historial diario en `data\runtime\decision_history.csv`
- unidad canónica: `ticker + fecha`
- reruns del mismo día reemplazan la observación
- hoy agrega:
  - `accion_previa`
  - `score_delta_vs_dia_anterior`
  - `racha`

## Documentación

Entrada canónica:

- [docs/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\README.md)

Documentos agregados para la siguiente etapa:

- [docs/claude-followups.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\claude-followups.md)
- [docs/improvement-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\improvement-roadmap.md)
- [data/examples/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\examples\README.md)
