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

Subfamilias efectivas actuales:
- `bond_sov_ar`
- `bond_cer`
- `bond_bopreal`
- `bond_other`

Lectura operativa actual:
- `bond_sov_ar` ya tiene una lógica más sensible de rebalanceo cuando la ganancia acumulada queda muy extendida
- `bond_cer` hoy queda en una lógica prudencial más neutra
- `bond_bopreal` hoy queda en monitoreo prudente
- `bond_other` ya fue endurecida para evitar falsos positivos de refuerzo en bonos sin clasificar
- la explicabilidad operativa ya distingue comentarios por subfamilia de bono en el reporte final

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

Subfamilias stock efectivas actuales:
- `stock_growth`
- `stock_defensive_dividend`
- `stock_commodity`
- `stock_argentina`
- `stock_other`

Subfamilias bond efectivas actuales:
- `bond_sov_ar`
- `bond_cer`
- `bond_bopreal`
- `bond_other`

Además:
- la taxonomía ya llega a `decision`
- la taxonomía ya se expone en el reporte HTML
- ya existe un primer ajuste real por subfamilia en scoring
- `etf_country_region` hoy exige más soporte para quedar en `Refuerzo` que un `etf_sector`
- `stock_growth` hoy es más exigente para quedar en `Refuerzo`
- `stock_defensive_dividend` y `stock_commodity` hoy tienen un sesgo algo más favorable si el resto de las señales acompaña

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
- `stock_growth`
- `stock_defensive_dividend`
- `stock_commodity`
- `stock_argentina`
- `stock_other`

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

Estado: `Hecho`

Exponer en reporte:
- `asset_family`
- `asset_subfamily`

Esto debería permitir leer rápido por qué dos ETFs no reciben el mismo tratamiento.

Avance actual:
- `Decisión final` ya muestra `Familia` y `Subfamilia`
- el resumen ejecutivo ya muestra `Taxonomía operativa`
- la taxonomía de bonos también quedó visible en la lectura real

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

Caso cerrado posterior:
- `bond_other`

Resultado:
- `TZXM7` y `TZXD6` bajaron a una zona más neutral
- ambos quedaron en `Mantener / monitorear`
- la subfamilia dejó de verse artificialmente fuerte solo por peso bajo y ausencia de datos

Caso cerrado adicional:
- explicabilidad de bonos por subfamilia

Resultado:
- `bond_sov_ar`, `bond_cer`, `bond_bopreal` y `bond_other` ya muestran comentarios operativos distintos
- el reporte final ahora permite distinguir mejor entre rebalanceo por ganancia extendida y monitoreo prudente por subtipo de bono

Caso cerrado adicional:
- subtaxonomía operativa de `stock`

Resultado:
- `stock_growth` quedó diferenciado de `stock_defensive_dividend`
- `stock_commodity` y `stock_argentina` ya se muestran explícitamente en el reporte
- el scoring ya no trata igual a:
  - `KO`
  - `VIST`
  - `MELI`
  - `AAPL`
  aunque todos sean CEDEARs o acciones individuales

Lectura real actual:
- `stock_growth` quedó con score promedio más exigente y levemente negativo
- `stock_defensive_dividend` quedó con sesgo más favorable
- `stock_commodity` quedó con sesgo de refuerzo moderado cuando hay soporte adicional

Caso borderline vigente:
- `NEM`

Lectura:
- había quedado como `Refuerzo` dentro de `stock_commodity`
- el caso no era un falso positivo obvio, porque combinaba:
  - beta baja
  - valuación razonable
  - calidad alta
  - consenso favorable
  - MEP muy favorable
- pero convivían señales que justificaban prudencia:
  - técnico mixto
  - volatilidad relativamente alta
  - ganancia acumulada extendida
- la corrección posterior fue deliberada y acotada:
  - `2026-04-04`: `+0.183`, `Mantener / Neutral`
  - `2026-04-05`: `+0.190`, `Refuerzo`
  - baseline actual: `+0.160`, `Mantener / Neutral`

Interpretación operativa:
- `NEM` volvió a neutral por un filtro prudente de `stock_commodity`
- el filtro actúa cuando coinciden técnico mixto y ganancia extendida
- `NEM` queda como caso testigo ya resuelto de esa lógica

## Próximo foco

Los siguientes frentes lógicos de calibración ya no están en ETFs ni en bonos, sino en CEDEARs:
- evaluar si `stock_argentina` merece una calibración propia más explícita o si la prudencia actual alcanza
- si se profundiza esta capa, el siguiente salto ya sería de calibración por subfamilia de `stock`, no de nuevas reglas genéricas

