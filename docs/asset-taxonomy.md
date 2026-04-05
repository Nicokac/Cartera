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

Hoy el proyecto ya distingue parcialmente:
- `Bono`
- `Liquidez`
- `CEDEAR`
- `Acción Local`
- ETFs vía `instrument_profile_map.json`

Pero todavía no existe una taxonomía funcional completa usada de extremo a extremo en:
- scoring
- acción
- sizing
- reporte HTML

## Próxima implementación sugerida

### Etapa 1. Clasificación canónica

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

Mantener una base común, pero con ajustes explícitos por familia:
- `stock`: modelo completo actual
- `etf_core`: reducción más suave
- `etf_sector`: momentum/técnico con quality secundaria
- `etf_country_region`: momentum/técnico/macrorégimen
- `bond`: lógica propia
- `liquidity`: lógica propia

### Etapa 3. Presentación

Exponer en reporte:
- `asset_family`
- `asset_subfamily`

Esto debería permitir leer rápido por qué dos ETFs no reciben el mismo tratamiento.

## Caso abierto inmediato

El próximo caso a auditar bajo esta taxonomía es:
- `EWZ`

Hipótesis actual:
- hoy `EWZ` entra como `Refuerzo` por momentum + técnico + beta + peso bajo
- antes de cambiarlo, conviene decidir si debe tratarse como:
  - `etf_country_region` táctico válido
  - o como una exposición que requiere umbral de refuerzo más exigente que un `stock`
