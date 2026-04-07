# Cartera de Activos

Motor de análisis de cartera con foco en:

- valuación y consolidación de cartera desde IOL
- scoring operativo de CEDEARs, acciones locales, bonos y liquidez
- overlay técnico
- contexto macro local
- reporte HTML reproducible
- snapshots para control de regresiones

## Estado actual

Baseline operativa vigente al `2026-04-07`:

- overlay técnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- `4` refuerzos: `VIST`, `KO`, `XLU`, `XLV`
- `1` reducción: `MELI`
- scoring absoluto conservador activo (`0.9` relativo / `0.1` absoluto)
- monitoreo de bonos con contexto macro ampliado y volumen spot vía `PyOBD`

## Estructura

- `src/`: lógica canónica del proyecto
- `scripts/`: runners y generación de reportes
- `data/`: mappings y reglas externas
- `docs/`: documentación funcional y de arquitectura
- `tests/`: suite de regresión y convenciones de snapshots
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

Copiá `.env.example` a `.env` y completá:

```env
IOL_USERNAME=tu_usuario_iol@example.com
IOL_PASSWORD=tu_password_iol
FRED_API_KEY=tu_fred_api_key
```

Notas:

- `IOL_USERNAME` y `IOL_PASSWORD` se usan en la corrida real.
- `FRED_API_KEY` habilita `UST 5y` y `UST 10y`.
- si no existe `.env`, el runner real también puede pedir credenciales por terminal.

## Uso rápido

Smoke report:

```powershell
python scripts\generate_smoke_report.py
```

Real report:

```powershell
python scripts\generate_real_report.py
```

Outputs principales:

- `reports\smoke-report.html`
- `reports\real-report.html`
- snapshots en `tests\snapshots\`

## Tests

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Suites puntuales útiles:

```powershell
python -m unittest tests.test_strategy_rules -v
python -m unittest tests.test_sizing -v
python -m unittest tests.test_pyobd_client tests.test_generate_real_report -v
```

## Decisiones de diseño

- la configuración estratégica vive fuera del código en `data\strategy\`
- el notebook `Cartera.ipynb` quedó como interfaz histórica; la lógica viva está en `src\`
- `build_decision_bundle(...)` y `build_sizing_bundle(...)` son la ruta canónica del motor
- bonos usan una capa prudente:
  - `bond_sov_ar` solo monitoreo/rebalanceo
  - `bond_cer`, `bond_bopreal` y `bond_other` pueden emitir `Refuerzo` si cruzan thresholds conservadores

## Documentación recomendada

- [Roadmap de refactorización](c:\Users\kachu\Python user\Colab\Cartera de Activos\docs\refactor-roadmap.md)
- [Roadmap de deshardcodeo](c:\Users\kachu\Python user\Colab\Cartera de Activos\docs\strategy-hardcode-roadmap.md)
- [Roadmap Bonistas](c:\Users\kachu\Python user\Colab\Cartera de Activos\docs\bonistas-roadmap.md)
- [Snapshots](c:\Users\kachu\Python user\Colab\Cartera de Activos\tests\snapshots\README.md)
