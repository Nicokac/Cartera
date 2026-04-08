# Runbook del notebook

`Cartera.ipynb` queda como interfaz de uso y exploración. La lógica canónica vive en `src/`.

## Ruta canónica

- configuración: `src/config.py`
- clientes externos: `src/clients/`
- cartera y valuación: `src/portfolio/`
- analytics descriptivo: `src/analytics/`
- scoring, acciones y sizing: `src/decision/`
- orquestación de alto nivel: `src/pipeline.py`

## Uso recomendado

1. Ejecutar el notebook de arriba hacia abajo.
2. Usar `Run all` cuando cambien datos base o mappings.
3. Evitar editar reglas de negocio dentro del notebook.
4. Si cambia una regla, tocar primero `src/` y después actualizar el notebook si hiciera falta.

## Verificación mínima antes de tocar lógica

```powershell
python -m unittest discover -s tests -v
```

## Qué no guardar

- credenciales de IOL
- payloads sensibles sin normalizar
- salidas temporales del kernel
