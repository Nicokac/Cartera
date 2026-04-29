# Contributing

Guia breve para colaborar en `Cartera de Activos`.

## Requisitos

- Python `3.12`
- Git
- Acceso de red para corridas reales (solo cuando aplica)

## Setup local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\bootstrap_example_config.py
```

Alternativa rapida:

```powershell
.\scripts\setup_local_app.ps1
```

## Convenciones de codigo

- Mantener cambios pequenos y enfocados por commit.
- Preservar modularidad actual:
  - logica canonica en `src/`
  - orquestacion/IO en `scripts/`
  - web local en `server.py` y `static/`
- Preferir tipado explicito y nombres claros.
- Evitar duplicacion: reutilizar utilidades en `src/common/`.
- No incluir credenciales ni datos sensibles en codigo, logs o fixtures.

## Testing

Suite completa:

```powershell
python -m unittest discover -s tests -v
```

Suites rapidas recomendadas segun area:

```powershell
python -m unittest tests.test_server -v
python -m unittest tests.test_generate_real_report -v
python -m unittest tests.test_pipeline -v
```

Antes de abrir PR:

- Ejecutar al menos las suites afectadas por el cambio.
- Si el cambio toca servidor/API local, incluir `tests.test_server`.
- Si el cambio toca runner real, incluir `tests.test_generate_real_report`.

## Flujo de trabajo sugerido

1. Crear rama desde `main`.
2. Implementar un cambio acotado.
3. Ejecutar tests relevantes.
4. Actualizar documentacion impactada.
5. Agregar entrada en `CHANGELOG.md` en `Unreleased`.
6. Abrir PR con:
   - resumen tecnico
   - riesgo/regresiones esperadas
   - que probar manualmente

## Documentacion a mantener

Cuando aplique, actualizar:

- `README.md`
- `docs/ayuda-usuario.txt`
- `docs/product-roadmap.md`
- `CHANGELOG.md`

