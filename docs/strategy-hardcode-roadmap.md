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

Luego de la Fase C, ya no quedan influyendo por ticker manual:
- bucket de prudencia
- peso base del sizing
- asignacion final por ticker

Siguen influyendo en la estrategia:
- heuristicas de bloque via [block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)
- taxonomia textual de consenso en [scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- preferencia explicita por `CAUCION` como fuente cuando se usa liquidez IOL en [sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
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
- Objetivo: reemplazar `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS`.

### Tareas cerradas

- derivar bucket de prudencia desde features:
  - `Beta`
  - tipo de activo
  - peso relativo en cartera
- eliminar la dependencia efectiva de listas manuales en sizing

### Criterio de cierre

- el bucket de prudencia no depende de ticker hardcodeado

### Cierre

- [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py) ya no usa listas de tickers para definir `Bucket_Prudencia`.
- El bucket ahora se deriva desde:
  - tipo de activo
  - thresholds de beta
  - peso relativo
- [data/strategy/sizing_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\sizing_rules.json) incorpora reglas de bucket por features.
- [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py) dejo de exponer `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS` al runtime.
- El pipeline, el smoke run y el runner real quedaron desacoplados de esas listas.

## Fase D. Desacople de `BLOCK_MAP` en scoring

- Estado: `Pendiente`
- Objetivo: que el scoring no dependa de etiquetas fijas de bloque para premiar o castigar activos.

### Tareas

- auditar usos de `Bloque` dentro de scoring
- reemplazar sesgos por senales derivadas:
  - diversificacion
  - peso relativo
  - exposicion sectorial o geografica si esta disponible
- conservar `Bloque` solo para reporting

### Criterio de cierre

- `BLOCK_MAP` deja de influir materialmente en `Refuerzo` o `Reducir`

## Fase E. Politica de liquidez explicita

- Estado: `En progreso`
- Objetivo: separar decision de mercado de politica de fondeo.

### Tareas

- usar `usar_liquidez_iol` y `aporte_externo_ars` como inputs obligatorios del sizing real
- impedir que el reporte sugiera desplegar liquidez cuando la politica la bloquea
- documentar reglas de fondeo en reporte y snapshots

### Criterio de cierre

- la estrategia operativa respeta siempre la politica de fondeo elegida

### Avance actual

- ya se incorporo la politica de fondeo al runner real
- ya se bloquea la liquidez IOL cuando el usuario decide no usarla

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
