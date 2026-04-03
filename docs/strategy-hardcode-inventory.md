# Inventario de Hardcodes de Estrategia

## Objetivo

Documentar que reglas siguen hardcodeadas y cuales ya quedaron parametrizadas para la estrategia de:
- `Refuerzo`
- `Reducir`
- `Desplegar liquidez`
- `Sizing`

Separacion usada:
- `Estrategia`: altera una decision o monto operativo
- `Integracion`: conecta o traduce datos, pero no decide la estrategia
- `Presentacion`: cambia mensajes o labels, no la logica central

## Estado despues de la Fase F

Ya quedaron eliminados del flujo estrategico:
- listas manuales de tickers defensivos/agresivos
- asignacion de bucket por ticker
- sesgo por bloque manual en scoring
- preferencia por `CAUCION` como fuente de fondeo

Ya quedaron externalizados en `data/strategy/`:
- pesos de `score_refuerzo`
- pesos de `score_reduccion`
- pesos de momentum
- taxonomia textual de consenso
- castigos por liquidez, bono y beta
- thresholds de `Refuerzo`, `Reducir` y `Desplegar liquidez`
- thresholds de rebalanceo de bonos
- pesos de sizing, topes y politica de fondeo
- thresholds de bucket por beta y defaults por tipo

No quedan hardcodes materiales afectando estrategia.

## Inventario vigente

### [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)

#### `consensus_to_score(...)`

- Tipo: `Estrategia`
- Estado:
  - taxonomia textual parametrizada via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
- Impacta en:
  - `Consensus_Score`
  - `score_refuerzo`
  - `score_reduccion`

#### `rank_score(..., neutral=0.5)`

- Tipo: `Estrategia`
- Estado:
  - parametrizado via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)

#### `Ganancia_%_Cap`

- Tipo: `Estrategia`
- Estado:
  - parametrizado via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)

#### `score_refuerzo`

- Tipo: `Estrategia`
- Estado:
  - pesos y castigos parametrizados via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
  - sin sesgo por `Bloque`

#### `score_reduccion`

- Tipo: `Estrategia`
- Estado:
  - pesos y castigos parametrizados via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
  - sin sesgo por `Bloque`

#### `score_despliegue_liquidez`

- Tipo: `Estrategia`
- Estado:
  - pesos parametrizados via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)

### [src/decision/actions.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)

#### `assign_base_action(...)`

- Tipo: `Estrategia`
- Estado:
  - thresholds parametrizados via [action_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\action_rules.json)

#### `assign_action_v2(...)`

- Tipo: `Estrategia`
- Estado:
  - thresholds parametrizados via [action_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\action_rules.json)

#### labels y mensajes

- Tipo: `Presentacion`
- Prioridad:
  - baja

### [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)

#### `_bucket_prudencia(...)`

- Tipo: `Estrategia`
- Estado actual:
  - deriva el bucket desde tipo, beta y peso relativo
  - ya no depende de tickers manuales
- Parametrizado:
  - thresholds beta
  - defaults por tipo
  - threshold de peso relativo

#### `build_operational_proposal(...)`

- Tipo: `Estrategia`
- Estado actual:
  - la fuente de fondeo se elige por score y monto de liquidez candidata
  - ya no depende de buscar `CAUCION` por nombre
- Parametrizado:
  - top candidatos
  - politica porcentual de fondeo
  - threshold de refuerzo fuerte
  - umbrales de bonos via `action_rules`

#### `build_prudent_allocation(...)`

- Tipo: `Estrategia`
- Parametrizado:
  - mezcla peso base / score ajustado
  - fallback de bucket
  - tope por posicion

#### `build_dynamic_allocation(...)`

- Tipo: `Estrategia`
- Parametrizado:
  - mezcla peso base / score ajustado
  - fallback de bucket
  - tope por posicion

## Hardcodes de integracion que no son prioridad estrategica

- [finviz_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\finviz_map.json)
- [ratios.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\ratios.json)
- [vn_factor_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\vn_factor_map.json)
- [block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json) como taxonomia de reporting
- tipos cotizables permitidos en [generate_real_report.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)

## Prioridad actual de remocion

### Prioridad 1

- labels y comentarios de presentacion

## Conclusion

La Fase F deja la estrategia sin hardcodes materiales de decision.

Lo que queda pendiente ya no afecta la logica central, sino principalmente:
- labels y comentarios de presentacion
