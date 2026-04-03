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

## Estado despues de la Fase B

Ya quedaron externalizados en `data/strategy/`:
- pesos de `score_refuerzo`
- pesos de `score_reduccion`
- pesos de momentum
- castigos por liquidez, bono, beta y core
- thresholds de `Refuerzo`, `Reducir` y `Desplegar liquidez`
- thresholds de rebalanceo de bonos
- pesos de sizing, topes y politica de fondeo

Siguen hardcodeados y afectan estrategia:
- listas de tickers defensivos/agresivos
- sesgo por bloque via `BLOCK_MAP`
- taxonomia textual de consenso

## Inventario vigente

### [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)

#### `DEFENSIVE_TICKERS`

- Tipo: `Estrategia`
- Impacta en:
  - `Bucket_Prudencia`
  - `Peso_Base`
  - `Monto_ARS`

#### `AGGRESSIVE_TICKERS`

- Tipo: `Estrategia`
- Impacta en:
  - `Bucket_Prudencia`
  - `Peso_Base`
  - `Monto_ARS`

#### `FCI_CASH_MANAGEMENT`

- Tipo: `Integracion`
- Impacta en:
  - clasificacion de liquidez
  - reconstruccion de cash management

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
  - ya parametrizado via `data/strategy/scoring_rules.json`

#### `Ganancia_%_Cap`

- Tipo: `Estrategia`
- Estado:
  - ya parametrizado via `data/strategy/scoring_rules.json`

#### `score_refuerzo`

- Tipo: `Estrategia`
- Estado:
  - pesos y castigos ya parametrizados via `data/strategy/scoring_rules.json`

#### `score_reduccion`

- Tipo: `Estrategia`
- Estado:
  - pesos y castigos ya parametrizados via `data/strategy/scoring_rules.json`

#### `score_despliegue_liquidez`

- Tipo: `Estrategia`
- Estado:
  - pesos ya parametrizados via `data/strategy/scoring_rules.json`

### [src/decision/actions.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)

#### `assign_base_action(...)`

- Tipo: `Estrategia`
- Estado:
  - thresholds ya parametrizados via `data/strategy/action_rules.json`

#### `assign_action_v2(...)`

- Tipo: `Estrategia`
- Estado:
  - thresholds ya parametrizados via `data/strategy/action_rules.json`

#### labels y mensajes

- Tipo: `Presentacion`
- Prioridad:
  - baja

### [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)

#### `_bucket_prudencia(...)`

- Tipo: `Estrategia`
- Hardcode vigente:
  - prioridad de listas manuales de tickers
- Parametrizado:
  - thresholds beta via `data/strategy/sizing_rules.json`

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

## Prioridad actual de remocion

### Prioridad 1

- `DEFENSIVE_TICKERS`
- `AGGRESSIVE_TICKERS`
- sesgo `Es_Core` derivado de `BLOCK_MAP`

### Prioridad 2

- preferencia explicita por `CAUCION` como fuente de fondeo
- taxonomia textual de `consensus_to_score(...)`

### Prioridad 3

- labels y comentarios de presentacion

## Conclusión

La Fase B elimino del codigo la mayor parte de los thresholds y pesos operativos.

Lo que queda pendiente para la estrategia es principalmente:
- sesgo por ticker manual
- sesgo por bloque manual
- una parte de la heuristica textual de consenso
