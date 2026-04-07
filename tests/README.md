# Tests y snapshots

Esta carpeta contiene tests deterministas para la lógica extraída a `src/`.

Cobertura inicial de Fase 8:
- clasificación de activos
- reconstrucción de liquidez
- valuación y cartera maestra
- checks de integridad
- fondeo y sizing

Ejecución local:

```powershell
python -m unittest discover -s tests -v
```

Snapshots:
- guardar corridas de referencia en `tests/snapshots/`
- preferir `json` o `csv` chicos, derivados de datos ya normalizados
- no guardar credenciales ni payloads crudos sensibles de IOL

Memoria temporal:
- el historial diario observacional del runner real vive en `data/runtime/decision_history.csv`
- una misma fecha no debe contar múltiples veces para persistencia
