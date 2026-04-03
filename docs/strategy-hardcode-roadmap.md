# Roadmap de Deshardcodeo de Estrategia

## Objetivo

Eliminar datos hardcodeados que hoy influyen en la estrategia de:
- `Refuerzo`
- `Reducir`
- `Desplegar liquidez`
- `Sizing`

La meta es que la decisión dependa de datos observables y reglas parametrizadas, no de listas fijas de tickers.

## Alcance

Este roadmap cubre solo hardcodes que afectan la estrategia. No incluye mappings operativos necesarios para:
- traducir tickers entre proveedores
- ratios de CEDEAR
- factores VN de bonos

## Estado actual

Hoy siguen influyendo en la estrategia:
- `DEFENSIVE_TICKERS` en [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
- `AGGRESSIVE_TICKERS` en [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
- `BUCKET_WEIGHTS` en [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
- heurísticas de bloque vía `BLOCK_MAP` en [data/mappings/block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)
- thresholds embebidos en:
  - [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [src/decision/actions.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)
  - [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)

## Principios

- No usar tickers manuales para decidir perfil de riesgo.
- No mezclar política de inversión con código.
- Mantener una ruta de fallback explícita durante la transición.
- Validar cada fase con snapshot real.

## Fase A. Inventario y aislamiento

- Estado: `Hecho`
- Objetivo: identificar todos los hardcodes que alteran la decisión final o el sizing.

### Tareas

- listar condiciones por archivo y función
- distinguir:
  - hardcode de estrategia
  - hardcode de integración
  - hardcode de presentación
- marcar cuáles cambian:
  - acción sugerida
  - acción operativa
  - bucket de prudencia
  - monto asignado

### Criterio de cierre

- existe un inventario completo con impacto por regla

### Cierre

- Se relevó el inventario de hardcodes que afectan estrategia en:
  - [src/config.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
  - [src/decision/scoring.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [src/decision/actions.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)
  - [src/decision/sizing.py](C:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
  - [data/mappings/block_map.json](C:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings\block_map.json)
- Se documentó el impacto de cada hardcode sobre:
  - acción sugerida
  - acción operativa
  - bucket de prudencia
  - monto asignado
- Se separaron explícitamente los hardcodes de:
  - estrategia
  - integración
  - presentación
- Quedó creado el inventario base en [docs/strategy-hardcode-inventory.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\strategy-hardcode-inventory.md).

## Fase B. Parametrización externa

- Estado: `Pendiente`
- Objetivo: mover thresholds y pesos de estrategia a configuración externa.

### Tareas

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

- cambiar thresholds no requiere tocar código Python

## Fase C. Eliminación de listas de tickers

- Estado: `Pendiente`
- Objetivo: reemplazar `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS`.

### Tareas

- derivar bucket de prudencia desde features:
  - `Beta`
  - tipo de activo
  - volatilidad o proxy equivalente
  - concentración o peso en cartera
- dejar listas manuales solo como fallback transitorio

### Criterio de cierre

- el bucket de prudencia no depende de ticker hardcodeado

## Fase D. Desacople de `BLOCK_MAP` en scoring

- Estado: `Pendiente`
- Objetivo: que el scoring no dependa de etiquetas fijas de bloque para premiar o castigar activos.

### Tareas

- auditar usos de `Bloque` dentro de scoring
- reemplazar sesgos por señales derivadas:
  - diversificación
  - peso relativo
  - exposición sectorial o geográfica si está disponible
- conservar `Bloque` solo para reporting

### Criterio de cierre

- `BLOCK_MAP` deja de influir materialmente en `Refuerzo` o `Reducir`

## Fase E. Política de liquidez explícita

- Estado: `En progreso`
- Objetivo: separar decisión de mercado de política de fondeo.

### Tareas

- usar `usar_liquidez_iol` y `aporte_externo_ars` como inputs obligatorios del sizing real
- impedir que el reporte sugiera desplegar liquidez cuando la política la bloquea
- documentar reglas de fondeo en reporte y snapshots

### Criterio de cierre

- la estrategia operativa respeta siempre la política de fondeo elegida

### Avance actual

- ya se incorporó la política de fondeo al runner real
- ya se bloquea la liquidez IOL cuando el usuario decide no usarla

## Fase F. Validación y cierre

- Estado: `Pendiente`
- Objetivo: confirmar que la estrategia sigue siendo útil después del deshardcodeo.

### Tareas

- comparar decisiones antes/después con snapshot real
- revisar cambios en:
  - top refuerzos
  - top reducciones
  - fuente de fondeo
  - sizing
- ajustar solo parámetros externos, no código

### Criterio de cierre

- la estrategia queda explicable, auditable y sin sesgos por ticker manual

## Registro de avances

### 2026-04-03

- Se cerró la Fase A con el relevamiento completo de hardcodes que afectan la estrategia.
- Se creó [docs/strategy-hardcode-inventory.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\strategy-hardcode-inventory.md) como documento base de inventario.
- Se confirmó que las prioridades de remoción son:
  - listas de tickers defensivos/agresivos
  - thresholds de acción
  - pesos y castigos del scoring
  - sesgo por bloque y buckets de prudencia
