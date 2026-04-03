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

Luego de la Fase B, ya no quedan embebidos en codigo:
- pesos de scoring
- thresholds de accion
- pesos y topes de sizing
- politica porcentual de fondeo

Siguen influyendo en la estrategia:
- `DEFENSIVE_TICKERS` en [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
- `AGGRESSIVE_TICKERS` en [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
- heuristicas de bloque via [block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)
- taxonomia textual de consenso en [scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- thresholds de bucket por beta en [sizing_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\sizing_rules.json)

## Principios

- No usar tickers manuales para decidir perfil de riesgo.
- No mezclar politica de inversion con codigo.
- Mantener una ruta de fallback explicita durante la transicion.
- Validar cada fase con snapshot real.

## Fase A. Inventario y aislamiento

- Estado: `Hecho`
- Objetivo: identificar todos los hardcodes que alteran la decision final o el sizing.

### Criterio de cierre

- existe un inventario completo con impacto por regla

### Cierre

- Se relevo el inventario de hardcodes que afectan estrategia en:
  - [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
  - [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [src/decision/actions.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)
  - [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
  - [data/mappings/block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)
- Se creo [docs/strategy-hardcode-inventory.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\strategy-hardcode-inventory.md).

## Fase B. Parametrizacion externa

- Estado: `Hecho`
- Objetivo: mover thresholds y pesos de estrategia a configuracion externa.

### Tareas cerradas

- crear `data/strategy/`
- extraer:
  - umbrales de `score_refuerzo`
  - umbrales de `score_reduccion`
  - umbral de `score_despliegue_liquidez`
  - pesos de momentum
  - castigos por liquidez/core
  - pesos y topes de sizing
- cargar estas reglas desde config

### Criterio de cierre

- cambiar thresholds no requiere tocar codigo Python

### Cierre

- Se creo `data/strategy/` con:
  - [scoring_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
  - [action_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\action_rules.json)
  - [sizing_rules.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\sizing_rules.json)
- [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py) ahora carga `SCORING_RULES`, `ACTION_RULES` y `SIZING_RULES`.
- El pipeline y los runners usan esas reglas externas.
- La suite valida que thresholds externos cambian la accion sin tocar codigo.

## Fase C. Eliminacion de listas de tickers

- Estado: `Pendiente`
- Objetivo: reemplazar `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS`.

### Tareas

- derivar bucket de prudencia desde features:
  - `Beta`
  - tipo de activo
  - volatilidad o proxy equivalente
  - concentracion o peso en cartera
- dejar listas manuales solo como fallback transitorio

### Criterio de cierre

- el bucket de prudencia no depende de ticker hardcodeado

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
