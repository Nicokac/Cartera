# Taxonomía de Activos

## Objetivo

Definir una taxonomía canónica de familias de activo para que el scoring, la acción y el sizing no traten igual instrumentos con naturalezas distintas.

El problema actual no es de cálculo puntual, sino de modelo:
- un CEDEAR de acción individual no debería competir con la misma lógica que un ETF
- un ETF `core` no debería tratarse igual que un ETF país o sectorial
- un bono y una posición de liquidez requieren lógica separada

## Criterio

La taxonomía debe ser:
- explícita
- desacoplada en mappings/configuración
- auditable en snapshots y reportes
- utilizable tanto por scoring como por sizing

## Familias propuestas

### 1. `stock`

CEDEAR o acción individual.

Ejemplos actuales:
- `AAPL`
- `MELI`
- `VIST`
- `KO`
- `AMD`

Señales relevantes:
- quality
- valuación
- consenso de analistas
- momentum
- técnico
- concentración

### 2. `etf_core`

ETF amplio de mercado core, normalmente usado como exposición base.

Ejemplos actuales:
- `SPY`
- `DIA`

Señales relevantes:
- régimen de mercado
- momentum
- técnico
- rol en cartera
- concentración, pero con castigo más suave

Señales menos relevantes:
- `ROE`
- `Profit Margin`
- `P/E` como castigo fuerte

### 3. `etf_sector`

ETF sectorial o temático con sesgo defensivo/cíclico.

Ejemplos actuales:
- `XLU`
- `XLV`

Señales relevantes:
- momentum
- técnico
- beta
- MEP
- concentración

Señales secundarias:
- quality agregada, si existe, con menor peso

### 4. `etf_country_region`

ETF de país o región. Suele ser una exposición táctica o macro.

Ejemplos actuales:
- `EWZ`
- `EEM`
- `IEUR`

Posibles equivalentes futuros:
- `EWW`
- `EWJ`
- `EWG`
- `INDA`
- `MCHI`

Señales relevantes:
- momentum
- técnico
- beta
- concentración
- rol táctico en cartera

Señales secundarias:
- quality y valuación agregadas, solo si la fuente las entrega y con menor peso

### 5. `bond`

Bono soberano/corporativo.

Ejemplos actuales:
- `GD30`
- `AL30`
- `GD35`
- `BPOC7`

Señales relevantes:
- ganancia acumulada
- peso de cartera
- rebalanceo
- carry / compresión / duración si se agregan a futuro

### 6. `liquidity`

Caja, caución, FCI cash management u otras posiciones de liquidez.

Ejemplos actuales:
- `CAUCION`
- `ADBAICA`
- `IOLPORA`
- `PRPEDOB`

Señales relevantes:
- fondeo
- liquidez desplegable
- restricciones operativas

## Estado actual del proyecto

Hoy el proyecto ya distingue y propaga en el pipeline:
- `asset_family`
- `asset_subfamily`

Familias efectivas actuales:
- `stock`
- `etf`
- `bond`
- `liquidity`

Subfamilias ETF efectivas actuales:
- `etf_core`
- `etf_sector`
- `etf_country_region`

Además:
- la taxonomía ya llega a `decision`
- ya existe un primer ajuste real por subfamilia en scoring
- `etf_country_region` hoy exige más soporte para quedar en `Refuerzo` que un `etf_sector`

## Próxima implementación sugerida

### Etapa 1. Clasificación canónica

- Estado: `Hecho`

- agregar `asset_family`
- agregar `asset_subfamily`
- propagar ambas columnas desde portfolio hasta decision

Propuesta inicial:
- `stock`
- `etf`
- `bond`
- `liquidity`

Subfamilias:
- `etf_core`
- `etf_sector`
- `etf_country_region`

### Etapa 2. Score con overlays por familia

- Estado: `En progreso`

Mantener una base común, pero con ajustes explícitos por familia:
- `stock`: modelo completo actual
- `etf_core`: reducción más suave
- `etf_sector`: momentum/técnico con quality secundaria
- `etf_country_region`: momentum/técnico/macrorégimen
- `bond`: lógica propia
- `liquidity`: lógica propia

Avance actual:
- `etf_core` ya tiene alivio específico en reducción
- `etf_country_region` ya tiene una penalización leve de refuerzo cuando no trae soporte fundamental/rating
- esto ya movió `EWZ` de `Refuerzo` a `Mantener / Neutral`

### Etapa 3. Presentación

Exponer en reporte:
- `asset_family`
- `asset_subfamily`

Esto debería permitir leer rápido por qué dos ETFs no reciben el mismo tratamiento.

## Caso cerrado inmediato

Primer caso auditado bajo esta taxonomía:
- `EWZ`

Resultado:
- dejó de ser `Refuerzo`
- pasó a `Mantener / Neutral`
- se mantuvieron como `Refuerzo` los ETFs sectoriales/defensivos mejor sostenidos (`XLU`)

Interpretación:
- el modelo dejó de tratar igual a un ETF país/región y a un ETF sectorial
- la taxonomía ya empezó a impactar la decisión operativa real

## Próximo foco

Los siguientes frentes lógicos de calibración son:
- revisar si `IEUR` y `EEM` deben compartir exactamente la misma lógica que `EWZ`
- decidir si `etf_sector` necesita una penalización propia cuando no trae soporte fundamental
- exponer `asset_family` y `asset_subfamily` en el reporte HTML
