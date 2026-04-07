# Línea Base Actual

## Nota de vigencia

Este documento conserva la línea base histórica previa al cierre del refactor inicial.

La baseline operativa vigente del pipeline real ya no es esta, sino la documentada en:

- [refactor-roadmap.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\refactor-roadmap.md)
- [tests/snapshots/README.md](C:\Users\kachu\Python user\Colab\Cartera de Activos\tests\snapshots\README.md)

Estado real vigente al `2026-04-07`:

- overlay técnico `24/24`
- Finviz fundamentals `24/24`
- Finviz ratings `17/24`
- `4` refuerzos: `VIST`, `KO`, `XLU`, `XLV`
- `1` reducción: `MELI`
- scoring absoluto conservador activo
- monitoreo de bonos con volumen spot y contexto macro ampliado

## Fecha

- `2026-03-31`

## Archivo base

- Notebook principal: [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb)

## Estructura detectada

- Total de celdas: `47`
- Celdas de código: `35`
- Celdas markdown: `12`

## Flujo principal vigente

El notebook actual opera como un pipeline lineal con estas etapas:

1. Setup de entorno e imports.
2. Configuración de credenciales y acceso a IOL.
3. Descarga de portafolio y estado de cuenta.
4. Clasificación de activos en CEDEARs, acciones locales, bonos y liquidez.
5. Reconstrucción de liquidez desde portafolio y cuenta.
6. Descarga de precios y MEP.
7. Construcción de tablas de valuación.
8. Dashboard ejecutivo y vistas analíticas.
9. Scoring operativo.
10. Propuesta final de fondeo y asignación.

## Tablas canónicas actuales

Estas estructuras aparecen como referencia central del flujo actual y deben preservarse conceptualmente durante el refactor:

- `df`
- `df_local`
- `df_bonos`
- `df_liquidez`
- `df_total`
- `final_decision`
- `propuesta`
- `asignacion_final`

## Fuentes externas activas

- `IOL`
- `ArgentinaDatos`
- `Finviz`
- `yfinance`

## Configuración y reglas hardcodeadas detectadas

Las siguientes reglas están embebidas en el notebook y son candidatas directas de extracción:

- `IOL_BASE_URL`
- `MARKET`
- `FINVIZ_MAP`
- `BLOCK_MAP`
- `RATIOS`
- `VN_FACTOR_MAP`
- `ARGENTINADATOS_URL`
- `MEP_CASA`
- `ALERTA_MEP_DESVIO_PCT`
- `ALERTA_PERDIDA_MINIMA`
- listas y reglas de buckets prudenciales
- umbrales de scoring y fondeo

## Outputs de referencia actuales

Resumen ejecutivo observado en outputs guardados:

- Valorizado total: `ARS 26,541,068.20`
- Valor estimado total: `USD 18,503.25`
- Ganancia total: `ARS 3,625,388.29`
- MEP real usado: `ARS 1,434.40`
- Invertido: `ARS 13,897,916.18`
- Liquidez: `ARS 12,643,152.02`
- Instrumentos totales: `38`

Distribución por tipo observada:

- `Liquidez`: `47.64%`
- `CEDEAR`: `37.57%`
- `Bono`: `12.58%`
- `Acción Local`: `2.21%`

## Señales operativas finales guardadas

En los outputs persistidos del notebook, la propuesta final vigente quedó así:

- Refuerzos sugeridos: `VIST`, `T`
- Reducciones sugeridas: `NVDA`, `GOOGL`, `MELI`
- Bono a rebalancear: `GD30`
- Fuente principal de fondeo: `CASH_ARS`
- Fondeo sugerido: `20%`
- Monto sugerido: `ARS 1,909,091`
- Equivalente estimado: `USD 1,330.93`
- Distribución final: `T 65%`, `VIST 35%`

## Riesgos operativos actuales de la línea base

- Dependencia fuerte del orden de ejecución de celdas.
- Variables globales compartidas entre módulos.
- Lógica de negocio duplicada en varias celdas.
- Múltiples versiones de scoring y propuesta operativa.
- Dependencia directa de APIs vivas y datos no reproducibles.

## Criterio de comparación para el refactor

Durante las próximas fases, cualquier cambio estructural debería preservar, salvo decisión explícita en contrario:

- la capacidad de reconstruir `df_total`;
- la clasificación correcta de instrumentos;
- la valuación total y por tipo;
- la distinción entre liquidez contable y liquidez operativa;
- la trazabilidad de la propuesta final.
