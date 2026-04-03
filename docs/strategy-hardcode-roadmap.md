# Roadmap de Deshardcodeo de Estrategia

## Objetivo

Eliminar datos hardcodeados que hoy influyen en la estrategia de:
- `Refuerzo`
- `Reducir`
- `Desplegar liquidez`
- `Sizing`

La meta es que la decision dependa de datos observables y reglas parametrizadas, no de listas fijas de tickers.

## Alcance

Este roadmap cubre solo hardcodes que afectan la estrategia. No incluye mappings operativos necesarios para:
- traducir tickers entre proveedores
- ratios de CEDEAR
- factores VN de bonos

## Estado actual

Luego de la Fase E, ya no quedan influyendo de forma material:
- listas manuales de tickers
- sesgo por bloque via `BLOCK_MAP`
- pesos y thresholds embebidos en codigo
- preferencia fija por `CAUCION` como fuente de fondeo

Siguen influyendo en la estrategia:
- taxonomia textual de consenso en [scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- thresholds de bucket por beta en [sizing_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\sizing_rules.json)

## Principios

- No usar tickers manuales para decidir perfil de riesgo.
- No mezclar politica de inversion con codigo.
- Mantener una ruta de fallback explicita durante la transicion.
- Validar cada fase con snapshot real.

## Fase A. Inventario y aislamiento

- Estado: `Hecho`

### Cierre

- Se relevo el inventario de hardcodes que afectan estrategia.
- Se creo [docs/strategy-hardcode-inventory.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\strategy-hardcode-inventory.md).

## Fase B. Parametrizacion externa

- Estado: `Hecho`

### Cierre

- Se creo `data/strategy/` con reglas externas de scoring, acciones y sizing.
- El pipeline y los runners usan esas reglas externas.
- Los thresholds y pesos operativos ya no viven embebidos en codigo.

## Fase C. Eliminacion de listas de tickers

- Estado: `Hecho`

### Cierre

- [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py) ya no usa listas de tickers para definir `Bucket_Prudencia`.
- El bucket ahora se deriva desde tipo, beta y peso relativo.

## Fase D. Desacople de `BLOCK_MAP` en scoring

- Estado: `Hecho`

### Cierre

- [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py) dejo de usar `Es_Core`.
- `Bloque` sigue existiendo para reporting, pero ya no sesga la decision.

## Fase E. Politica de liquidez explicita

- Estado: `Hecho`
- Objetivo: separar decision de mercado de politica de fondeo.

### Tareas cerradas

- usar `usar_liquidez_iol` y `aporte_externo_ars` como inputs del sizing real
- impedir que el reporte sugiera desplegar liquidez cuando la politica la bloquea
- eliminar la preferencia fija por `CAUCION` como fuente de fondeo
- seleccionar la fuente de fondeo por score y monto de liquidez candidata

### Criterio de cierre

- la estrategia operativa respeta siempre la politica de fondeo elegida

### Cierre

- el runner real ya pregunta politica de fondeo antes de armar la estrategia
- la liquidez se bloquea cuando el usuario decide no usar IOL
- [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py) ya no privilegia `CAUCION` por nombre
- la fuente de fondeo ahora sale de la liquidez efectivamente candidata, ordenada por score y monto
- [tests/test_sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\tests\test_sizing.py) valida que una liquidez con mejor score desplaza a caucion como fuente

## Fase F. Validacion y cierre

- Estado: `Pendiente`
- Objetivo: confirmar que la estrategia sigue siendo util despues del deshardcodeo.

### Tareas

- comparar decisiones antes/despues con snapshot real
- revisar cambios en:
  - top refuerzos
  - top reducciones
  - fuente de fondeo
  - sizing
- ajustar solo parametros externos, no codigo

### Criterio de cierre

- la estrategia queda explicable, auditable y sin sesgos por ticker manual

## Registro de avances

### 2026-04-03

- Se cerro la Fase A con el relevamiento completo de hardcodes que afectan la estrategia.
- Se creo [docs/strategy-hardcode-inventory.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\strategy-hardcode-inventory.md) como documento base de inventario.
- Se cerro la Fase B con la externalizacion de thresholds y pesos de estrategia a `data/strategy/`.
- El pipeline ya toma reglas de scoring, acciones y sizing desde archivos configurables.
- Se cerro la Fase C con la eliminacion de `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS` del sizing.
- Se cerro la Fase D con la eliminacion del sesgo por `BLOCK_MAP` dentro del scoring.
- Se cerro la Fase E con la politica de fondeo explicita y la eliminacion de la preferencia fija por caucion.
