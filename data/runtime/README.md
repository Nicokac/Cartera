# Runtime

Artefactos operativos persistidos por el proyecto durante corridas reales o smoke avanzados.

## Archivos vigentes

- `decision_history.csv`
  - historial diario del motor de decision
  - usado para memoria temporal entre corridas
- `prediction_history.csv`
  - historial del motor de prediccion direccional
  - se crea a partir de la Fase 1 del track documental de prediccion

## Regla de manejo

- estos archivos no son fuente versionada de verdad operativa
- pueden contener datos reales o historicos derivados de corridas locales
- si hace falta compartir ejemplos, usar `data/examples/` o documentacion, no estos CSV

## Trazabilidad

- baseline funcional: [docs/baseline-actual.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\baseline-actual.md)
- roadmap del motor de prediccion: [docs/prediction-engine-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-roadmap.md)
- historial del motor de prediccion: [docs/prediction-engine-history.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\prediction-engine-history.md)
