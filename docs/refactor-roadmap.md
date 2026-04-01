# Roadmap de Refactorización

## Objetivo

Ordenar el proyecto para separar ingestión de datos, normalización, reglas de negocio, scoring y presentación, sin romper el flujo actual del notebook [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb).

## Principios de trabajo

- Mantener el notebook funcionando durante toda la transición.
- Aplicar cambios por fases cortas y verificables.
- Evitar reescrituras completas sin validación intermedia.
- Dejar una única versión canónica de cada regla de negocio.
- Actualizar este archivo cada vez que una fase cambie de estado.

## Estados

- `Pendiente`: todavía no iniciado.
- `En progreso`: trabajo empezado pero no cerrado.
- `Hecho`: implementado y validado.
- `Bloqueado`: no puede avanzar hasta resolver una dependencia.

## Estado actual

- Fecha base del roadmap: `2026-03-31`
- Estado global: `Fase 5 cerrada`
- Última actualización: `2026-04-01`

## Fase 0. Línea base y resguardo

- Estado: `Hecho`
- Objetivo: congelar el comportamiento actual antes de mover lógica.

### Tareas

- Identificar las celdas fuente del flujo principal.
- Registrar outputs actuales clave del notebook.
- Definir cuáles son las tablas canónicas actuales:
  `df`, `df_local`, `df_bonos`, `df_liquidez`, `df_total`, `final_decision`, `propuesta`.
- Listar dependencias externas activas:
  IOL, ArgentinaDatos, Finviz, yfinance.
- Documentar variables de configuración y reglas hardcodeadas.

### Criterio de cierre

- Existe una referencia clara del comportamiento actual.
- Sabemos qué resultados no deben cambiar al refactorizar.

### Cierre

- Se documentó la línea base actual en [`baseline-actual.md`](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\baseline-actual.md).
- Se registraron estructura, tablas canónicas, fuentes externas, reglas hardcodeadas y outputs de referencia.
- Quedó explicitado qué comportamiento debe preservarse durante el refactor.

## Fase 1. Configuración y mappings externos

- Estado: `Hecho`
- Objetivo: sacar del notebook la configuración mutable y los mapas de negocio.

### Tareas

- Crear `data/mappings/`.
- Extraer:
  - `FINVIZ_MAP`
  - `BLOCK_MAP`
  - `RATIOS`
  - `VN_FACTOR_MAP`
- Extraer umbrales operativos y parámetros generales a `src/config.py`.
- Implementar un loader único de configuración.
- Ajustar el notebook para leer desde la nueva fuente de configuración.

### Criterio de cierre

- El notebook ya no depende de mappings hardcodeados en celdas.
- Los parámetros de negocio se cambian sin editar lógica central.

### Cierre

- Se creó `src/config.py` como fuente canónica de configuración del proyecto.
- Se creó `data/mappings/` con:
  - `finviz_map.json`
  - `block_map.json`
  - `ratios.json`
  - `vn_factor_map.json`
- Se externalizaron también parámetros generales y listas prudenciales:
  - base URL de IOL
  - mercado
  - URL de ArgentinaDatos
  - casa MEP
  - umbrales de alertas
  - FCI cash management
  - tickers defensivos/agresivos
  - pesos por bucket
- Se adaptó [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb) para cargar la configuración desde `src/config.py`.
- Los hardcodes históricos siguen visibles en el notebook como referencia de transición, pero la fuente efectiva pasó a ser la configuración externa.

## Fase 2. Clientes de datos

- Estado: `Hecho`
- Objetivo: encapsular las integraciones externas.

### Tareas

- Crear `src/clients/iol.py`.
- Crear `src/clients/argentinadatos.py`.
- Crear `src/clients/finviz_client.py`.
- Crear `src/clients/market_data.py` si hace falta centralizar precios técnicos.
- Mover login, fetch de portfolio, estado de cuenta y cotizaciones a clientes dedicados.
- Unificar manejo de errores y timeouts.

### Criterio de cierre

- El notebook llama funciones cliente en vez de hacer requests directos.
- Los errores de fuente quedan aislados y son más auditables.

### Cierre

- Se creó `src/clients/` con:
  - `iol.py`
  - `argentinadatos.py`
  - `finviz_client.py`
  - `market_data.py`
- Se encapsularon en clientes dedicados:
  - login IOL
  - portfolio IOL
  - estado de cuenta IOL
  - cotización IOL
  - cotización IOL con re-login
  - consulta de MEP desde ArgentinaDatos
- Se prepararon wrappers para:
  - bundle Finviz
  - histórico técnico con yfinance
- Se adaptó [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb) para usar los clientes de IOL por alias/rebind en el flujo efectivo y para revalidar el MEP con el cliente de ArgentinaDatos antes de la valuación.
- Se dejó import diferido en los clientes de Finviz y yfinance para no romper el entorno cuando esas dependencias todavía no están instaladas.
- Las requests históricas siguen visibles en algunas celdas del notebook como parte de la transición, pero la ruta efectiva de ejecución para IOL y MEP ya quedó desacoplada en `src/clients/`.

## Fase 3. Construcción de cartera maestra

- Estado: `Hecho`
- Objetivo: consolidar la lógica de clasificación, liquidez y valuación.

### Tareas

- Crear `src/portfolio/classify.py`.
- Crear `src/portfolio/liquidity.py`.
- Crear `src/portfolio/valuation.py`.
- Crear una función canónica tipo `build_portfolio_master(...)`.
- Estandarizar columnas mínimas de salida.
- Unificar reconstrucción de liquidez y valuación en USD.

### Criterio de cierre

- `df_total` sale de una sola ruta de construcción.
- La lógica de cartera puede correrse fuera del notebook.

### Cierre

- Se creó `src/portfolio/` con:
  - `classify.py`
  - `liquidity.py`
  - `valuation.py`
- Se encapsularon en módulos canónicos:
  - clasificación de activos IOL
  - normalización de moneda de cuenta
  - extracción de componentes de `estadocuenta`
  - reconstrucción de liquidez
  - construcción de `df`, `df_local`, `df_bonos`
  - construcción de `df_total` mediante `build_portfolio_master(...)`
- Se adaptó [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb) para enlazarse con la ruta canónica de `src/portfolio/` en clasificación, liquidez, valuación base y tabla maestra.
- Se agregó [`.gitignore`](C:\Users\kachu\Python user\Colab\Cartera de Activos\.gitignore) para excluir `__pycache__/`, `*.pyc` e `.ipynb_checkpoints/`.
- Se limpió el `__pycache__` local de `src/clients/` para no seguir arrastrando artefactos generados.

## Fase 4. Checks y validaciones

- Estado: `Hecho`
- Objetivo: volver explícitas las validaciones del pipeline.

### Tareas

- Crear `src/portfolio/checks.py`.
- Validar columnas requeridas antes de cada etapa.
- Validar suma de pesos, precios faltantes y conversiones USD/ARS.
- Hacer visibles los warnings cuando falten datos de una fuente.

### Criterio de cierre

- El pipeline detecta inconsistencias antes del scoring.
- Los errores de datos no quedan ocultos en celdas posteriores.

### Cierre

- Se creó `src/portfolio/checks.py`.
- Se agregaron validaciones canónicas para:
  - columnas requeridas
  - precios faltantes en instrumentos invertidos
  - valores USD faltantes
  - valorizados faltantes
  - suma total de pesos
- Se integró `build_integrity_report(...)` en [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb) como ruta efectiva del resumen de checks de integridad.
- Se limpió el `__pycache__` local de `src/portfolio/`.
- La presentación del notebook todavía conserva parte del formato histórico, pero la lógica de validación ya quedó centralizada en `src/portfolio/checks.py`.

## Fase 5. Analytics y presentación

- Estado: `Hecho`
- Objetivo: separar análisis descriptivo de lógica operativa.

### Tareas

- Crear `src/analytics/dashboard.py`.
- Crear `src/analytics/fundamentals.py`.
- Crear `src/analytics/ratings.py`.
- Crear `src/analytics/news.py`.
- Crear `src/analytics/insiders.py`.
- Crear `src/analytics/technical.py`.
- Mover generación de tablas y gráficos a funciones reutilizables.

### Criterio de cierre

- El notebook renderiza resultados llamando funciones analíticas.
- La capa visual deja de ser el lugar donde vive la lógica.

### Cierre

- Se creó `src/analytics/` con:
  - `dashboard.py`
  - `fundamentals.py`
  - `ratings.py`
  - `news.py`
  - `insiders.py`
  - `technical.py`
- Se extrajeron funciones reutilizables para:
  - KPIs ejecutivos
  - resumen por tipo
  - top posiciones / ganadoras / perdedoras
  - tablas de fundamentals
  - resumen de ratings
  - últimas noticias por ticker
  - resumen de insiders
  - normalización base del overlay técnico
- Se adaptó [`Cartera.ipynb`](C:\Users\kachu\Python user\Colab\Cartera de Activos\Cartera.ipynb) para importar y usar `build_executive_dashboard_data(...)` como ruta canónica del dashboard descriptivo.
- Se limpió el `__pycache__` local generado en `src/analytics/` y `src/`.
- La migración visual todavía es parcial: el notebook conserva formateo y rendering histórico, pero la capa descriptiva principal ya empezó a salir desde `src/analytics/`.

## Fase 6. Scoring y decisión operativa

- Estado: `Pendiente`
- Objetivo: dejar una única implementación auditada del motor de decisión.

### Tareas

- Crear `src/decision/scoring.py`.
- Crear `src/decision/actions.py`.
- Centralizar `score_refuerzo`, `score_reduccion`, `score_unificado`.
- Centralizar `accion_sugerida` y `accion_operativa`.
- Incorporar columnas explicativas:
  - `motivo_score`
  - `motivo_accion`
  - `driver_1`
  - `driver_2`
  - `driver_3`

### Criterio de cierre

- Existe una sola ruta para llegar a la decisión final.
- Cada recomendación puede explicarse sin inspeccionar varias celdas.

## Fase 7. Fondeo y sizing

- Estado: `Pendiente`
- Objetivo: estabilizar la propuesta de despliegue de liquidez.

### Tareas

- Crear `src/decision/sizing.py`.
- Mover buckets prudenciales y reglas de topes.
- Separar claramente:
  - liquidez contable
  - liquidez operativa desplegable
- Unificar la lógica de `propuesta`, `asignacion` y `asignacion_final`.

### Criterio de cierre

- Hay una sola propuesta de fondeo y asignación.
- El sizing no depende de múltiples variantes en el notebook.

## Fase 8. Tests y snapshots

- Estado: `Pendiente`
- Objetivo: mejorar reproducibilidad y confianza.

### Tareas

- Crear `tests/`.
- Cubrir clasificación, liquidez, valuación y scoring.
- Definir snapshots mínimos de datos crudos o resultados intermedios.
- Guardar corridas de referencia para comparar salidas.

### Criterio de cierre

- Las piezas críticas tienen tests automatizados.
- Podemos detectar regresiones antes de tocar producción analítica.

## Fase 9. Limpieza final del notebook

- Estado: `Pendiente`
- Objetivo: dejar `Cartera.ipynb` como interfaz liviana de uso.

### Tareas

- Eliminar lógica duplicada u obsoleta.
- Dejar solo importación, orquestación y visualización final.
- Revisar nombres de celdas y flujo de ejecución.
- Confirmar que el notebook siga siendo usable en Colab.

### Criterio de cierre

- El notebook deja de ser el backend del proyecto.
- La lógica principal vive en `src/`.

## Registro de avances

### 2026-03-31

- Se creó este roadmap inicial.
- Se definieron fases, criterios de cierre y política de actualización.
- Se cerró la Fase 0 con una línea base documentada del notebook actual.
- Se agregó [`baseline-actual.md`](C:\Users\kachu\Python user\Colab\Cartera de Activos\docs\baseline-actual.md) como referencia de comparación para el refactor.
- Se cerró la Fase 1 con la extracción de configuración y mappings a `src/` y `data/mappings/`.
- El notebook quedó apuntando a la configuración externa como fuente canónica.
- Se cerró la Fase 2 con la creación de clientes de datos en `src/clients/`.
- El flujo efectivo del notebook quedó enlazado a los clientes de IOL y ArgentinaDatos.
- Se cerró la Fase 3 con la extracción de clasificación, liquidez y valuación a `src/portfolio/`.
- `df_total` quedó con una ruta canónica de construcción vía `build_portfolio_master(...)`.

### 2026-04-01

- Se cerró la Fase 4 con la extracción de checks y validaciones a `src/portfolio/checks.py`.
- El notebook pasó a usar `build_integrity_report(...)` como fuente canónica del chequeo de integridad.
- Se cerró la Fase 5 con la creación de `src/analytics/` y la extracción inicial del dashboard descriptivo.
- El notebook quedó enlazado a `build_executive_dashboard_data(...)` como entrada canónica del dashboard ejecutivo.

## Política de actualización

Cada vez que avancemos una fase, este archivo debe actualizarse con:

- cambio de estado de la fase;
- fecha de actualización;
- tareas completadas;
- desvíos respecto del plan;
- próximos pasos concretos.
