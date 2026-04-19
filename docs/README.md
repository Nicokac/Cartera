# Documentacion

Indice de la documentacion activa del proyecto.

## Puntos de entrada

- [README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\README.md)
- [baseline-actual.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\baseline-actual.md)
- [improvement-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\improvement-roadmap.md)
- [prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
- [prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
- [report-ux-architecture.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\report-ux-architecture.md)
- [asset-taxonomy.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\asset-taxonomy.md)

## Soporte operativo

- [data/examples/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\examples\README.md)
- [data/snapshots/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\snapshots\README.md)
- [tests/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\tests\README.md)
- [tests/snapshots/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\tests\snapshots\README.md)
- [data/reference/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\reference\README.md)

## Criterio de mantenimiento

- `README.md`: instalacion, uso y layout del repo
- `baseline-actual.md`: capacidades vigentes y baseline funcional, sin depender de una corrida puntual
- `improvement-roadmap.md`: backlog tecnico activo y deuda real
- `prediction-engine-roadmap.md`: arquitectura, fases, contratos y criterios de avance del motor de prediccion direccional
- `prediction-engine-history.md`: bitacora de implementacion y cambios por fase del motor de prediccion
- `report-ux-architecture.md`: arquitectura actual del reporte y deuda de renderer
- `asset-taxonomy.md`: taxonomia efectiva del motor y fuentes de configuracion
- `data/snapshots/README.md`: directorio canonico de snapshots operativos
- `tests/snapshots/README.md`: legacy snapshots y contrato de fallback
- el track de prediccion ya llego a Fase 6:
  - integrado al pipeline experimental
  - visible en el renderer HTML
  - con runner propio de verificacion y recalibracion
  - con separacion operativa explicita:
    - `generate_real_report.py` crea observaciones nuevas
    - `run_prediction_cycle.py` solo verifica y recalibra

## Historico

`docs/archive/` guarda roadmaps absorbidos, auditorias cerradas y notas historicas. No es punto de entrada operativo y no debe tomarse como estado actual salvo que se lo consulte por trazabilidad.
