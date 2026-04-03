# Inventario de Hardcodes de Estrategia

## Objetivo

Documentar todos los hardcodes que hoy afectan la estrategia de:
- `Refuerzo`
- `Reducir`
- `Desplegar liquidez`
- `Sizing`

Separaci\u00f3n usada en este inventario:
- `Estrategia`: altera una decisi\u00f3n o monto operativo
- `Integraci\u00f3n`: necesario para conectar o traducir datos, pero no decide la estrategia
- `Presentaci\u00f3n`: afecta mensajes o labels, no la l\u00f3gica central

## Resumen ejecutivo

Los hardcodes m\u00e1s prioritarios a remover son:
- listas de tickers defensivos/agresivos
- pesos de buckets
- thresholds de scoring y acci\u00f3n
- pesos internos del score
- sesgos por bloque como `Es_Core`

Estos son los que hoy alteran materialmente:
- qui\u00e9n queda en `Refuerzo`
- qui\u00e9n queda en `Reducir`
- qui\u00e9n se considera `Desplegar liquidez`
- cu\u00e1nto capital recibe cada candidato

## Inventario por archivo

### [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)

#### `DEFENSIVE_TICKERS`

- Tipo: `Estrategia`
- Impacta en:
  - `Bucket_Prudencia`
  - `Peso_Base`
  - `Monto_ARS`
- Consumido por:
  - [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py) `_bucket_prudencia(...)`
- Riesgo:
  - un ticker recibe trato defensivo por nombre, no por datos observables

#### `AGGRESSIVE_TICKERS`

- Tipo: `Estrategia`
- Impacta en:
  - `Bucket_Prudencia`
  - `Peso_Base`
  - `Monto_ARS`
- Consumido por:
  - [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py) `_bucket_prudencia(...)`
- Riesgo:
  - un ticker recibe castigo/agresividad fija por nombre

#### `BUCKET_WEIGHTS`

- Tipo: `Estrategia`
- Impacta en:
  - peso base del sizing
  - asignaci\u00f3n prudente
  - asignaci\u00f3n din\u00e1mica
- Consumido por:
  - [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
- Riesgo:
  - la pol\u00edtica de distribuci\u00f3n est\u00e1 embebida en c\u00f3digo/config fija

#### `FCI_CASH_MANAGEMENT`

- Tipo: `Integraci\u00f3n`
- Impacta en:
  - clasificaci\u00f3n de liquidez
  - reconstrucci\u00f3n de cash management
- Consumido por:
  - [src/portfolio/liquidity.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\liquidity.py)
- Prioridad:
  - media
- Nota:
  - no decide refuerzo/reducci\u00f3n directamente, pero s\u00ed afecta la base de liquidez operativa

### [data/mappings/block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)

#### `BLOCK_MAP`

- Tipo: `Estrategia`
- Impacta en:
  - `Bloque`
  - flag `Es_Core`
  - castigos y sesgos del scoring
- Consumido por:
  - [src/portfolio/classify.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\classify.py)
  - [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Riesgo:
  - el score usa una etiqueta manual de bloque para premiar/castigar activos

### [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)

#### `consensus_to_score(...)`

- Tipo: `Estrategia`
- Hardcode:
  - listas fijas de palabras positivas, negativas y neutras
- Impacta en:
  - `Consensus_Score`
  - `score_refuerzo`
  - `score_reduccion`
- Riesgo:
  - dependencia de taxonom\u00eda manual y cerrada de textos de analistas

#### `rank_score(..., neutral=0.5)`

- Tipo: `Estrategia`
- Hardcode:
  - neutral fijo en `0.5`
- Impacta en:
  - cualquier feature faltante o incompleta
- Riesgo:
  - el modelo asume una neutralidad arbitraria uniforme

#### `Ganancia_%_Cap = clip(-100, 150)`

- Tipo: `Estrategia`
- Impacta en:
  - castigo/premio por ganancias grandes
- Riesgo:
  - cap fijo sin par\u00e1metro externo

#### `Momentum_Refuerzo`

- Tipo: `Estrategia`
- Hardcode:
  - `0.2` semana
  - `0.4` mes
  - `0.4` YTD
- Impacta en:
  - `score_refuerzo`
- Riesgo:
  - pesos de momentum fijos, no calibrables

#### `Momentum_Reduccion`

- Tipo: `Estrategia`
- Hardcode:
  - `0.2` semana
  - `0.4` mes
  - `0.4` YTD
- Impacta en:
  - `score_reduccion`

#### `score_refuerzo`

- Tipo: `Estrategia`
- Hardcode:
  - `0.20 * s_low_weight`
  - `0.25 * Momentum_Refuerzo`
  - `0.15 * s_consensus_good`
  - `0.10 * s_beta_ok`
  - `0.10 * s_mep_ok`
  - `0.10 * s_pe_ok`
  - `0.10 * (1 - s_big_gain)`
  - castigo liquidez `-0.35`
  - castigo bono `-0.08`
  - castigo beta alta `-0.08` si `Beta > 1.8`
  - castigo core `-0.05`
- Impacta en:
  - selecci\u00f3n de refuerzos

#### `score_reduccion`

- Tipo: `Estrategia`
- Hardcode:
  - `0.25 * s_high_weight`
  - `0.20 * Momentum_Reduccion`
  - `0.15 * s_beta_risk`
  - `0.10 * s_mep_premium`
  - `0.10 * s_consensus_bad`
  - `0.10 * s_pe_expensive`
  - `0.10 * s_big_gain`
  - castigo liquidez `-0.25`
  - castigo core `-0.12`
  - castigo bono `-0.05`
- Impacta en:
  - selecci\u00f3n de reducciones

#### `score_despliegue_liquidez`

- Tipo: `Estrategia`
- Hardcode:
  - `0.60` peso relativo
  - `0.40` ganancia inversa
- Impacta en:
  - qu\u00e9 liquidez queda candidata a despliegue

### [src/decision/actions.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)

#### `assign_base_action(...)`

- Tipo: `Estrategia`
- Hardcode:
  - `score_refuerzo >= 0.60`
  - gap contra reducci\u00f3n `>= 0.10`
  - `score_reduccion >= 0.60`
  - `score_despliegue_liquidez >= 0.55`
- Impacta en:
  - acci\u00f3n sugerida base

#### `assign_action_v2(...)`

- Tipo: `Estrategia`
- Hardcode:
  - `score_refuerzo_v2 >= 0.60`
  - gap contra reducci\u00f3n `>= 0.10`
  - `score_reduccion_v2 >= 0.60`
  - `score_despliegue_liquidez >= 0.55`
- Impacta en:
  - acci\u00f3n sugerida final antes del sizing

#### Labels y mensajes

- Tipo: `Presentaci\u00f3n`
- Hardcode:
  - `Refuerzo`
  - `Reducir`
  - `Desplegar liquidez`
  - `Mantener / Neutral`
- Impacta en:
  - reporte
  - legibilidad
- Prioridad:
  - baja

### [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)

#### `_bucket_prudencia(...)`

- Tipo: `Estrategia`
- Hardcode:
  - prioridad de listas manuales de tickers
  - `Beta <= 0.8` => `Defensivo`
  - `Beta >= 1.3` => `Agresivo`
  - default => `Intermedio`
- Impacta en:
  - bucket de prudencia
  - sizing prudente
  - sizing din\u00e1mico

#### `build_operational_proposal(...)`

- Tipo: `Estrategia`
- Hardcode:
  - elecci\u00f3n preferente de `CAUCION` como fuente
  - `n_refuerzo_fuerte >= 3` => `30%`
  - `n_refuerzo_fuerte >= 1` => `20%`
  - else `10%`
  - top `3` para refuerzos, reducciones, bonos y fondeo
- Impacta en:
  - fuente de fondeo
  - porcentaje de despliegue
  - monto total de fondeo

#### `build_prudent_allocation(...)`

- Tipo: `Estrategia`
- Hardcode:
  - mezcla `0.80 * Peso_Base + 0.20 * Score_Ajustado`
  - fallback bucket `0.60`
  - tope por posici\u00f3n `65%`
- Impacta en:
  - asignaci\u00f3n final por ticker

#### `build_dynamic_allocation(...)`

- Tipo: `Estrategia`
- Hardcode:
  - mezcla `0.80 * Peso_Base + 0.20 * Score_Ajustado`
  - fallback bucket `0.60`
  - tope `65%`
- Impacta en:
  - distribuci\u00f3n del capital entre refuerzos

## Hardcodes de integraci\u00f3n que no son prioridad estrat\u00e9gica

Estos existen, pero no son el foco inmediato del roadmap:
- [data/mappings/finviz_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\finviz_map.json)
- [data/mappings/ratios.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\ratios.json)
- [data/mappings/vn_factor_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\vn_factor_map.json)
- tipos cotizables permitidos en [scripts/generate_real_report.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)

## Prioridad de remoci\u00f3n

### Prioridad 1

- `DEFENSIVE_TICKERS`
- `AGGRESSIVE_TICKERS`
- thresholds de `assign_base_action(...)`
- thresholds de `assign_action_v2(...)`
- pesos y castigos de `score_refuerzo`
- pesos y castigos de `score_reduccion`

### Prioridad 2

- sesgo `Es_Core` derivado de `BLOCK_MAP`
- thresholds de bucket por `Beta`
- l\u00f3gica de `n_refuerzo_fuerte` para porcentaje de fondeo
- topes fijos de `65%`

### Prioridad 3

- taxonom\u00eda textual de `consensus_to_score(...)`
- labels y comentarios de presentaci\u00f3n

## Conclusi\u00f3n

La estrategia hoy no depende de precios o cartera hardcodeada, pero s\u00ed depende de reglas hardcodeadas que introducen sesgo:
- por ticker
- por bloque
- por threshold
- por pesos internos del modelo

La Fase A queda cerrada cuando este inventario se toma como base para parametrizar y deshardcodear el motor sin tocar primero la capa de integraci\u00f3n.
