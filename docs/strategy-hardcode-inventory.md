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

## Estado despues de la Fase C

Ya quedaron eliminados del flujo estrategico:
- listas manuales de tickers defensivos/agresivos
- asignacion de bucket por ticker

Ya quedaron externalizados en `data/strategy/`:
- pesos de `score_refuerzo`
- pesos de `score_reduccion`
- pesos de momentum
- castigos por liquidez, bono, beta y core
- thresholds de `Refuerzo`, `Reducir` y `Desplegar liquidez`
- thresholds de rebalanceo de bonos
- pesos de sizing, topes y politica de fondeo
- thresholds de bucket por beta y defaults por tipo

Siguen hardcodeados y afectan estrategia:
- sesgo por bloque via `BLOCK_MAP`
- taxonomia textual de consenso
- preferencia por `CAUCION` como fuente cuando se usa liquidez IOL

## Inventario vigente

### [data/mappings/block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)

#### `BLOCK_MAP`

- Tipo: `Estrategia`
- Impacta en:
  - `Bloque`
  - flag `Es_Core`
  - sesgos del scoring

### [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)

#### `consensus_to_score(...)`

- Tipo: `Estrategia`
- Hardcode vigente:
  - listas fijas de palabras positivas, negativas y neutras
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

#### `score_reduccion`

- Tipo: `Estrategia`
- Estado:
  - pesos y castigos parametrizados via [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)

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
- Hardcode vigente:
  - eleccion preferente de `CAUCION` como fuente cuando se usa liquidez IOL
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
- tipos cotizables permitidos en [generate_real_report.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)

## Prioridad actual de remocion

### Prioridad 1

- sesgo `Es_Core` derivado de `BLOCK_MAP`
- preferencia explicita por `CAUCION` como fuente de fondeo

### Prioridad 2

- taxonomia textual de `consensus_to_score(...)`

### Prioridad 3

- labels y comentarios de presentacion

## Conclusion

La Fase C elimino el sesgo por ticker manual del sizing.

Lo que queda pendiente para la estrategia es principalmente:
- sesgo por bloque manual
- heuristica textual de consenso
- una preferencia fija por caucion dentro del fondeo
