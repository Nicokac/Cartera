# Trazabilidad de Funcionalidades del Notebook

## Objetivo

Registrar, celda por celda de [Cartera.ipynb](c:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb), si la funcionalidad:
- `Se usa`
- `Se usa parcialmente`
- `No se usa`

La referencia de verdad para el proyecto actual es `src/` y los runners de `scripts/`.

## Criterio

- `Se usa`: la funcionalidad sigue viva en el flujo actual y tiene ruta canónica en `src/` o `scripts/`.
- `Se usa parcialmente`: la intención funcional sigue existiendo, pero la implementación de la celda quedó reemplazada, reducida o solo sirve de transición.
- `No se usa`: la celda quedó como legado del notebook y no forma parte del flujo actual.

## Relevamiento

### Celda 1. Instalación de dependencias

- Estado: `No se usa`
- Motivo:
  - solo prepara el entorno interactivo del notebook
  - no forma parte del core ni del pipeline
- Observación:
  - la app actual corre desde `src/` y `scripts/`; la instalación de paquetes no debe vivir en el flujo funcional

### Celda 2. Imports base y configuración visual de pandas

- Estado: `Se usa parcialmente`
- Motivo:
  - las librerías base (`requests`, `pandas`) sí son parte del proyecto actual
  - pero esta celda como bloque de imports/config visual no es la ruta canónica de ejecución
  - la parte de `matplotlib`, `seaborn`, `pd.set_option(...)` y `warnings.filterwarnings(...)` no influye en el pipeline real actual
- Ruta canónica actual:
  - imports distribuidos en [src](c:\Users\kachu\Python user\Colab\Cartera de Activos\src)
  - runners en [scripts](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts)

### Celda 3. Bootstrap del notebook e imports desde `src/`

- Estado: `Se usa parcialmente`
- Motivo:
  - el notebook importa la ruta canónica actual del proyecto desde `src/`
  - los módulos importados sí se usan hoy
  - pero el ajuste de `sys.path`, el `input(...)` del notebook y los wrappers transicionales definidos dentro de la celda no son la forma principal de ejecución del proyecto
- Ruta canónica actual:
  - configuración: [src/config.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\config.py)
  - clientes: [src/clients](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\clients)
  - pipeline: [src/pipeline.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\pipeline.py)
  - runner real: [scripts/generate_real_report.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)
- Observación:
  - esta celda mezcla código vigente con bootstrap específico de notebook

### Celda 4. Fetch de IOL, mappings y clasificación inicial

- Estado: `Se usa parcialmente`
- Motivo:
  - la funcionalidad de traer portafolio/estado de cuenta y clasificar activos sí se usa hoy
  - los mappings también se usan, pero desde archivos externos y `src/config.py`
  - la parte hardcodeada original de `FINVIZ_MAP`, `BLOCK_MAP`, `RATIOS`, `VN_FACTOR_MAP` ya no es canónica
  - el loop manual de clasificación quedó reemplazado por la llamada final a `classify_iol_portfolio(...)`
- Ruta canónica actual:
  - clientes IOL: [src/clients/iol.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\clients\iol.py)
  - mappings: [data/mappings](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\mappings)
  - clasificación: [src/portfolio/classify.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\classify.py)
- Importante:
  - el bloque manual intermedio de clasificación no debe considerarse fuente de verdad
  - la fuente de verdad es la reclasificación final con `classify_iol_portfolio(...)`

### Celda 5. Debug de tipos reales devueltos por IOL

- Estado: `No se usa`
- Motivo:
  - es una celda puramente exploratoria para inspeccionar la estructura real del payload de IOL
  - no impacta score, acción, sizing ni valuación
- Observación:
  - fue útil durante el diseño de clasificación y liquidez, pero hoy no forma parte del flujo funcional

### Celda 6. Reconstrucción de liquidez

- Estado: `Se usa parcialmente`
- Motivo:
  - la funcionalidad sí sigue siendo central en el proyecto actual
  - pero la implementación manual extensa de la celda fue reemplazada por la ruta canónica al final de la misma celda:
    - `rebuild_liquidity(...)`
- Ruta canónica actual:
  - [liquidity.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\liquidity.py)
- Qué sí sobrevive conceptualmente:
  - normalización de moneda de cuenta
  - separación entre cash inmediato y pendiente
  - detección de caución
  - identificación de FCI cash management
  - construcción de `df_liquidez`
  - armado de `liquidity_contract`
- Qué no debe considerarse fuente de verdad:
  - la construcción manual de `LIQUIDEZ`
  - el agregado manual de `CASH_ARS`, `CASH_USD`, `PEND_ARS`, `PEND_USD`
  - la visualización y prints del notebook
- Importante:
  - esta celda fue una de las que más divergió entre notebook original y código actual
- además, la versión manual original llegó a duplicar liquidez, algo que ya fue corregido en la implementación canónica de [liquidity.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\liquidity.py)

### Celda 7. MEP, precios, valuación y enriquecimiento Finviz

- Estado: `Se usa parcialmente`
- Motivo:
  - esta celda mezcla varias funcionalidades distintas
  - una parte sí sigue viva en el flujo actual
  - otra parte quedó reemplazada o directamente no está conectada hoy al reporte real
- Qué sí se usa hoy:
  - MEP desde ArgentinaDatos
  - fetch de precios IOL
  - construcción de `df`, `df_local`, `df_bonos`
  - conversión a USD
  - estructura base para `df_ratings_res`
- Ruta canónica actual:
  - MEP: [argentinadatos.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\clients\argentinadatos.py)
  - precios IOL: [iol.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\clients\iol.py)
  - valuación: [valuation.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\valuation.py)
  - pipeline: [pipeline.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\pipeline.py)
- Qué no debe considerarse fuente de verdad:
  - los helpers manuales definidos al principio de la celda
  - el loop manual de fetch cuando luego se reemplaza por funciones canónicas
  - el fetch directo de Finviz dentro del notebook como implementación principal
- Punto importante para estrategia:
  - esta celda confirma que el notebook original sí incorporaba fundamentals, ratings, news e insiders desde Finviz
  - si hoy alguna de esas señales no está llegando al score final en `src/`, eso no se resuelve tocando JSONs: primero hay que verificar la trazabilidad funcional de esas señales

### Celda 8. Resumen ejecutivo robusto

- Estado: `Se usa parcialmente`
- Motivo:
  - la construcción de `df_total` y los checks sí se usan hoy
  - gran parte del resto es reporting del notebook
- Qué sí se usa hoy:
  - `build_portfolio_master(...)`
  - `build_integrity_report(...)`
  - `build_executive_dashboard_data(...)`
- Ruta canónica actual:
  - [valuation.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\valuation.py)
  - [checks.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\checks.py)
  - [dashboard.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\analytics\dashboard.py)
- Qué no se usa como fuente principal:
  - los `print(...)`
  - los `display(...)` manuales del notebook
  - el recálculo manual de varios KPIs ya resueltos por `dashboard.py`

### Celda 9. Auditoría rápida de bonos

- Estado: `No se usa`
- Motivo:
  - es una celda de auditoría y validación manual
  - no impacta la estrategia ni el pipeline
- Observación:
  - fue útil para validar valuación de bonos durante el desarrollo
  - no forma parte de la app actual

### Celda 10. Distribución por bloque estratégico

- Estado: `Se usa parcialmente`
- Motivo:
  - la dimensión `Bloque` sigue existiendo y se usa en reporting
  - pero esta celda en sí es visualización del notebook
  - además, `Bloque` ya no sesga scoring ni sizing
- Qué sí se usa hoy:
  - `Bloque` como taxonomía descriptiva/reporting
- Qué no se usa hoy:
  - los gráficos y tabla estilo notebook como parte del flujo funcional
  - cualquier inferencia de estrategia basada en `Bloque`
- Importante:
  - esta celda es útil para confirmar que `Bloque` sobrevivió solo como capa analítica/descriptiva, no como driver de decisión

### Celda 11. Top 5 ganadoras y perdedoras

- Estado: `Se usa parcialmente`
- Motivo:
  - la idea analítica de top ganadoras/perdedoras sigue viva en el dashboard actual
  - pero esta celda es reporting del notebook, no la ruta funcional principal
- Ruta canónica actual:
  - [dashboard.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\analytics\dashboard.py)
- Qué no se usa:
  - el gráfico y `display(...)` del notebook como fuente principal
- Impacto en estrategia:
  - no directo
  - sirve como lectura descriptiva, no como score operativo

### Celda 12. Consenso de analistas por posición

- Estado: `Se usa parcialmente`
- Motivo:
  - el consenso sí impacta la estrategia actual
  - pero esta celda como tabla visual es solo reporting
- Qué sí se usa hoy:
  - `consenso`
  - `consenso_n`
  - `total_ratings`
  - su traducción a `Consensus_Score` y `Consensus_Final`
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [scoring_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
- Importante:
  - esta es una celda directamente relevante para la decisión actual, porque confirma que la señal de ratings sí sobrevivió al core

### Celda 13. Alertas automáticas

- Estado: `Se usa parcialmente`
- Motivo:
  - varias de las métricas que aparecen en alertas sí existen hoy en el core
  - pero esta celda de alertas no es la fuente canónica de decisión actual
- Qué sí sobrevive conceptualmente:
  - umbrales sobre MEP implícito
  - pérdidas relevantes
  - beta alta
  - concentración de cartera
- Qué no se usa hoy como fuente principal:
  - el armado manual de `df_alertas`
  - la salida tipo reporte del notebook
- Ruta canónica parcial actual:
  - checks: [checks.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\checks.py)
  - scoring: [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - reglas: [scoring_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
- Punto importante:
  - esta celda es una candidata fuerte a revisión posterior, porque parte de su lógica puede haberse simplificado al pasar a `src/`
  - especialmente concentración, beta y desvíos de MEP

### Celda 14. Tablas resumen por familia

- Estado: `No se usa`
- Motivo:
  - es presentación detallada del notebook
  - no es parte del pipeline actual ni de la lógica de decisión
- Observación:
  - usa DataFrames que sí existen hoy, pero la celda en sí no influye score, acción ni sizing

### Celda 15. Gráfico peso % por posición

- Estado: `No se usa`
- Motivo:
  - es visualización descriptiva del notebook
  - no impacta la lógica operativa

### Celda 16. MEP implícito por ticker

- Estado: `Se usa parcialmente`
- Motivo:
  - `MEP_Implicito` y su desvío respecto de `mep_real` sí sobreviven en el core actual
  - pero esta celda es visualización analítica del notebook
- Qué sí se usa hoy:
  - `MEP_Implicito`
  - `MEP_Premium_%`
  - su efecto en scoring
- Ruta canónica actual:
  - [valuation.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\valuation.py)
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Qué no se usa:
  - el gráfico y tabla del notebook
  - la señal textual `Prima / Descuento / En línea` como objeto funcional
- Importante:
  - esta es una señal vigente en la estrategia actual

### Celda 17. Ganancia/Pérdida en ARS por posición

- Estado: `Se usa parcialmente`
- Motivo:
  - `Ganancia_ARS` sí forma parte del core y del scoring actual
  - pero la celda es reporting del notebook
- Qué sí se usa hoy:
  - `Ganancia_ARS`
  - `Ganancia_%`
  - clipping y ranking de ganancia para score
- Ruta canónica actual:
  - [valuation.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\valuation.py)
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Qué no se usa:
  - el gráfico horizontal y tabla del notebook

### Celda 18. Tabla comparativa de fundamentals Finviz

- Estado: `Se usa parcialmente`
- Motivo:
  - varios fundamentals mostrados en la celda sí sobreviven al core actual
  - especialmente `P/E`, `Fwd P/E`, `Beta`, `Perf Week`, `Perf Month`, `Perf YTD`
  - la tabla comparativa como tal no es parte del pipeline
- Qué sí se usa hoy:
  - `Beta`
  - `P/E`
  - `Perf Week`
  - `Perf Month`
  - `Perf YTD`
- Ruta canónica actual:
  - enriquecimiento / fetch en flujo refactorizado
  - scoring en [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Qué no se usa:
  - la tabla renderizada del notebook
- Importante:
  - esta celda confirma que la estrategia original sí estaba apoyada en metrics de Finviz que hoy siguen siendo críticas

### Celda 19. Heatmap de performance del subyacente

- Estado: `Se usa parcialmente`
- Motivo:
  - las métricas de performance (`Perf Week`, `Perf Month`, `Perf YTD`) sí se usan hoy
  - el heatmap es solo visualización
- Qué sí se usa hoy:
  - momentum semanal
  - momentum mensual
  - momentum YTD
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Qué no se usa:
  - el heatmap ni la tabla estilo notebook
- Importante:
  - esta celda es evidencia directa de que el score actual sí debería respetar la idea de momentum del notebook original

### Celda 20. P/E ratio del subyacente

- Estado: `Se usa parcialmente`
- Motivo:
  - `P/E` sí se usa actualmente en el score
  - la clasificación visual `P/E alto / medio / bajo` del notebook no se usa como tal
- Qué sí se usa hoy:
  - `P/E`
  - ranking relativo de valuación cara/barata
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Qué no se usa:
  - el gráfico del notebook
  - la señal textual derivada de umbrales fijos de esta celda
- Punto importante:
  - esta es otra señal que hoy sí está externalizada vía reglas y ranking, no vía umbrales visuales del notebook

### Celda 21. Beta

- Estado: `Se usa parcialmente`
- Motivo:
  - `Beta` sí sigue influyendo en el core actual
  - la celda es una visualización analítica del notebook
- Qué sí se usa hoy:
  - `Beta`
  - su efecto sobre `score_refuerzo`, `score_reduccion` y bucket de sizing
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [sizing.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
  - [sizing_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\sizing_rules.json)
- Qué no se usa:
  - el gráfico de la celda
  - la señal textual `Defensivo / Moderado / Alta volatilidad` como lógica principal

### Celda 22. Ratings de analistas

- Estado: `Se usa parcialmente`
- Motivo:
  - la tabla y visualización no se usan
  - pero la señal subyacente de ratings sí influye en el core
- Qué sí se usa hoy:
  - resumen de ratings por ticker
  - consenso dominante
  - cantidad relativa de ratings del consenso
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
- Qué no se usa:
  - la distribución visual del notebook
  - el detalle tabular reciente como parte del score

### Celda 23. Noticias recientes

- Estado: `No se usa`
- Motivo:
  - hoy las noticias no alimentan el score, la acción ni el sizing
  - quedan como contexto cualitativo del notebook
- Observación:
  - si se quisiera reincorporar esta señal, habría que diseñar una regla explícita; hoy no existe en el core

### Celda 24. Insiders

- Estado: `No se usa`
- Motivo:
  - hoy la información de insiders no impacta la estrategia operativa
  - es contexto exploratorio del notebook
- Observación:
  - al igual que noticias, sería una señal nueva a diseñar si se quisiera usar de verdad

### Celda 25. Checks de integridad

- Estado: `Se usa parcialmente`
- Motivo:
  - los checks de integridad sí siguen existiendo en el proyecto actual
  - pero esta implementación manual del notebook no es la fuente canónica
- Ruta canónica actual:
  - [checks.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\portfolio\checks.py)
- Qué sí se usa hoy:
  - disponibilidad de valuaciones
  - pesos consistentes
  - completitud mínima de datos
- Qué no se usa:
  - este armado manual puntual de `df_checks`

### Celda 26. Exposición cruzada por tipo y bloque

- Estado: `No se usa`
- Motivo:
  - es reporting descriptivo del notebook
  - no influye score, acción ni sizing

### Celda 27. Dashboard final condensado

- Estado: `Se usa parcialmente`
- Motivo:
  - la idea de dashboard final sí sigue viva en el reporte HTML actual
  - pero esta celda puntual no es la implementación canónica
- Ruta canónica actual:
  - [dashboard.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\analytics\dashboard.py)
  - [generate_smoke_report.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_smoke_report.py)
  - [generate_real_report.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)

### Celda 28. Score base de refuerzo / reducción

- Estado: `Se usa parcialmente`
- Motivo:
  - esta celda es el antecedente directo del scoring actual
  - gran parte de su lógica sí sobrevive hoy en el core
  - pero no sobrevive idéntica
- Qué sí se usa hoy:
  - `rank_score(...)`
  - base unificada `decision`
  - `Consensus_Score`
  - `Consensus_Final`
  - `Ganancia_%_Cap`
  - scores parciales de momentum, beta, P/E, MEP, peso, ganancia
  - `score_refuerzo`
  - `score_reduccion`
  - `score_despliegue_liquidez`
  - asignación de acción base
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [actions.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)
  - [scoring_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
  - [action_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\action_rules.json)
- Diferencias relevantes contra el notebook:
  - `Es_Core` ya no influye en scoring
  - la taxonomía de consenso ya no está hardcodeada en código
  - thresholds y pesos viven en JSON externo
- Importante:
  - el score base sí sobrevivió al refactor y hoy está operativo

### Celda 29. Overlay técnico ampliado para CEDEARs

- Estado: `Se usa parcialmente`
- Motivo:
  - el runner real sí construye hoy el overlay técnico
  - pero no usa la implementación manual de la celda
  - la lógica quedó refactorizada en módulos y runners canónicos
- Qué sí se usa hoy:
  - `RSI_14`
  - distancias a `SMA` y `EMA`
  - `Momentum_20d_%`
  - `Momentum_60d_%`
  - `Vol_20d_Anual_%`
  - `Drawdown_desde_Max3m_%`
  - `Tech_Trend`
- Ruta canónica actual:
  - [technical.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\analytics\technical.py)
  - [generate_real_report.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)
  - [generate_smoke_report.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_smoke_report.py)
- Observación:
  - el cálculo sigue requiriendo `yfinance` en el entorno donde corre el runner real
  - el HTML ahora expone `Overlay técnico: Sí/No` y `Cobertura técnica: X/Y`

### Celda 30. Integración del overlay técnico al score final

- Estado: `Se usa parcialmente`
- Motivo:
  - el blend técnico sí está conectado hoy al flujo real
  - pero no a través del código manual de la celda
  - el scoring actual usa una versión refactorizada y parametrizada del blend
- Qué sí se usa hoy:
  - `tech_refuerzo`
  - `tech_reduccion`
  - `score_refuerzo_v2`
  - `score_reduccion_v2`
  - `score_unificado_v2`
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [pipeline.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\pipeline.py)
  - [generate_real_report.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\scripts\generate_real_report.py)
  - [scoring_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\scoring_rules.json)
- Importante:
  - esta brecha ya quedó cerrada
  - una corrida real con cobertura técnica `24/24` mostró cambios materiales en refuerzos y reducciones frente al score base puro

### Celda 31. Lista final resumida

- Estado: `No se usa`
- Motivo:
  - esta celda depende de `decision_tech` y de `accion_sugerida_v2` alimentadas por el overlay técnico del notebook
  - como hoy ese overlay no está conectado al runner real, esta salida resumida del notebook tampoco es la fuente funcional actual
- Observación:
  - conceptualmente es una vista de presentación de la decisión, no una pieza de lógica independiente

### Celda 32. Score unificado y acción operativa

- Estado: `Se usa parcialmente`
- Motivo:
  - parte de esta celda sí sobrevivió al core actual
  - otra parte dependía del overlay técnico y de heurísticas luego reemplazadas
- Qué sí se usa hoy:
  - `finalize_unified_score(...)`
  - explicación automática enriquecida
  - idea de top refuerzo / reducción / rebalanceo
- Ruta canónica actual:
  - [scoring.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\scoring.py)
  - [actions.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\actions.py)
  - [sizing.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
- Qué no se usa hoy:
  - la lógica manual de `conviccion_operativa(...)`
  - la lógica manual de `comentario_automatico(...)`
  - la heurística manual de búsqueda prioritaria de `CAUCION`
  - la lógica manual de `pct_despliegue`
- Importante:
  - esta celda fue ampliamente reemplazada por `build_operational_proposal(...)`

### Celda 32 bis. Propuesta operativa final corregida

- Estado: `Se usa parcialmente`
- Motivo:
  - esta celda ya muestra una transición explícita hacia la ruta canónica
  - varias salidas efectivamente sobreviven hoy, pero no a través del código manual de la celda
- Qué sí se usa hoy:
  - `build_operational_proposal(...)`
  - `propuesta`
  - `top_reforzar_final`
  - `top_reducir_final`
  - `top_bonos_rebalancear`
  - `top_fondeo`
  - `fuente_fondeo`
  - `pct_fondeo`
  - `monto_fondeo_ars`
  - `monto_fondeo_usd`
- Ruta canónica actual:
  - [sizing.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
- Qué no se usa hoy:
  - el bloque manual de reetiquetado previo
  - la lógica manual de comentario ejecutivo
  - la reasignación manual posterior de fuente de fondeo
  - la distribución simple manual si difiere de la salida canónica
- Importante:
  - esta celda confirma que el notebook ya había empezado a delegar en la implementación refactorizada

### Celda 33. Asignación prudente del fondeo

- Estado: `Se usa parcialmente`
- Motivo:
  - la funcionalidad sí sobrevive
  - pero la implementación manual original con `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS` ya no es vigente
- Qué sí se usa hoy:
  - `build_prudent_allocation(...)`
- Ruta canónica actual:
  - [sizing.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
  - [sizing_rules.json](c:\Users\kachu\Python user\Colab\Cartera de Activos\data\strategy\sizing_rules.json)
- Qué no se usa hoy:
  - bucket manual por ticker
  - dependencias a `DEFENSIVE_TICKERS` y `AGGRESSIVE_TICKERS`
  - comentarios manuales de sizing
- Importante:
  - esta celda muestra explícitamente una versión vieja de sizing que ya fue reemplazada por la ruta desacoplada actual

### Celda 34. Asignación operativa final dinámica

- Estado: `Se usa parcialmente`
- Motivo:
  - la funcionalidad sí sigue existiendo
  - pero el bloque manual de la celda ya no es la fuente de verdad
- Qué sí se usa hoy:
  - `build_dynamic_allocation(...)`
- Ruta canónica actual:
  - [sizing.py](c:\Users\kachu\Python user\Colab\Cartera de Activos\src\decision\sizing.py)
- Qué no se usa hoy:
  - bucket manual por ticker
  - `DEFENSIVE_TICKERS` / `AGGRESSIVE_TICKERS`
  - redistribución manual posterior al llamado canónico
- Importante:
  - al igual que la celda 33, esta celda conserva bastante código histórico que ya no representa la lógica real del proyecto

## Conclusión parcial

Con las primeras 34 celdas relevadas:
- el notebook todavía contiene bastante código legado o transicional
- la funcionalidad real vive en `src/`
- la lógica manual hardcodeada que aparece en algunas celdas no necesariamente es la que hoy decide la estrategia
- ya aparece una señal fuerte de revisión pendiente:
  - el notebook original integraba señales de Finviz que pueden no estar completamente trazadas hasta la decisión actual
- además, las celdas 12 y 13 muestran que el notebook original sí conectaba ratings y alertas analíticas con criterios que podrían haberse simplificado en el refactor
- las celdas 16 a 20 confirman que el núcleo cuantitativo original usaba:
  - MEP implícito
  - ganancias/pérdidas
  - momentum
  - beta
  - P/E
  y esas señales sí están, al menos en parte, presentes en el core actual
- las celdas 23 y 24 confirman que noticias e insiders hoy no forman parte de la estrategia actual
- las celdas 29 y 30 eran la principal brecha funcional detectada y ya fueron reintegradas:
  - el overlay técnico ampliado del notebook original vuelve a estar conectado al runner real y al score operativo final
- las celdas 31 a 34 muestran que la capa final de propuesta y sizing sí sobrevivió, pero hoy ya vive en `src/decision/sizing.py` y no en la lógica manual del notebook

## Próximo paso

Con la brecha principal ya cerrada, el siguiente frente abierto ya no es de trazabilidad sino de evolución del motor:
- régimen de mercado
- memoria temporal
- mejoras adicionales de bonos solo si aparece evidencia en corridas reales

## Estado posterior al relevamiento

Desde este relevamiento ya se cerró la brecha funcional principal detectada:
- el overlay técnico ampliado de las celdas 29 y 30 fue reincorporado al runner real
- la cobertura técnica pasó a verse explícitamente en el reporte HTML
- luego también se recuperó la capa real de Finviz en el runner:
  - fundamentals `24/24`
  - ratings `17/24`

La corrida real del `2026-04-04` quedó como primer baseline completo posterior al cierre de la brecha de trazabilidad, con:
- `4` refuerzos
- `1` reducción
- `0` despliegues
- ajuste fino adicional para no sobrepenalizar ETFs/core amplios como `SPY`

La baseline operativa vigente ya no es esa, sino la del `2026-04-07`, documentada en:
- [refactor-roadmap.md](c:\Users\kachu\Python user\Colab\Cartera de Activos\docs\archive\refactor-roadmap.md)
- [README.md](c:\Users\kachu\Python user\Colab\Cartera de Activos\tests\snapshots\README.md)

El próximo punto abierto ya no es de trazabilidad, sino de evolución de producto:
- incorporar sensibilidad a régimen de mercado;
- evaluar memoria temporal de decisiones;
- seguir endureciendo bonos solo si el histórico real lo justifica.

## Actualización posterior

Desde esta evaluación ya se implementó una primera capa de memoria temporal diaria:
- persiste historial en `data/runtime/decision_history.csv`
- usa una sola observación canónica por `ticker + fecha`
- reemplaza reruns del mismo día en lugar de sumar persistencia artificial
- expone contexto temporal en el runner real:
  - `accion_previa`
  - `score_delta_vs_dia_anterior`
  - rachas consecutivas por estado
- la versión actual sigue siendo observacional y no altera score ni acción

Actualización posterior:
- el reporte HTML ya muestra:
  - `Corrida`
  - bloque `Regimen de mercado`
  - `Accion previa`
  - `Δ Score`
  - `Racha`
- la calibración reciente endureció levemente `stock_growth`
- `stock_commodity` recibió un freno suave adicional cuando `Tech_Trend = Mixta`
- efecto visible en corrida real vigente:
  - `GOOGL` dejó de salir como `Refuerzo`
  - `NEM` siguió en `Refuerzo`, pero con menor score
