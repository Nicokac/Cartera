# Roadmap de Mejoras

## Criterio

Priorizacion combinando:

- impacto funcional en corridas reales
- complejidad de implementacion
- riesgo de regresion

## Resuelto

- documentacion y `.json.example` para clones limpios
- script de bootstrap para configuracion de ejemplo
- `pyproject.toml` minimo del proyecto
- CI minima con GitHub Actions ampliada a suites estables del pipeline y clientes
- CI ampliada a la bateria local completa del repo:
  - `bond_analytics`
  - `bonistas_client`
  - `classify`
  - `dashboard`
  - `liquidity`
  - `numeric_utils`
  - `valuation_and_checks`
- gate absoluto suave para limitar `Refuerzo` en setups no alcistas con momentum corto negativo
- curva propia de RSI para reduccion tecnica en casos `oversold` y `overbought`
- fallback visible de `FRED UST` en bundle real y reporte HTML
- narrativa alineada con scoring relativo sin perder brevedad
- hardening del CLI real para respuestas invalidas y montos negativos
- guardas de `Peso_%` en valuacion
- CEDEARs sin `finviz_map`
- contrato explicito de `mep_real`
- lazy loading de `config.py`
- cache acotado en Bonistas
- hardening de render HTML con escape consistente
- constantes canonicas para acciones
- helpers numericos comunes para scoring, liquidez, valuacion y sizing
- exclusion de liquidez en el resumen agregado de memoria temporal
- continuidad temporal compartida entre `CASH_ARS` y `CAUCION` para liquidez operativa diaria
- warnings de pandas en `tests/test_sizing.py`
- cobertura base de clientes externos:
  - `iol`
  - `argentinadatos`
  - `market_data`
  - `finviz_client`
- cobertura reforzada en integraciones secundarias:
  - `bcra`
  - `fred_client`
  - `pyobd_client`
- cobertura expandida del universo BYMA:
  - `364 / 407` tickers con cobertura completa
  - `340` candidatos automaticos integrados
  - `1` rescate manual razonable (`VRSN`)
  - `43` casos restantes formalizados como exclusion versionada en `unsupported_byma_tickers.json`
- enriquecimiento real de CEDEARs con Finviz paralelizado por ticker:
  - fetch concurrente acotado
  - errores aislados por activo
  - sin mutacion concurrente de DataFrame
- renderer HTML desacoplado de los runners:
  - `report_renderer.py` como capa comun
  - `generate_smoke_report.py` y `generate_real_report.py` quedan como runners finos
- taxonomia local de bonos externalizada:
  - reglas de `bonistas_local_subfamily` movidas a `bond_local_subfamily_rules.json`
  - override configurable sin editar codigo
- cliente Finviz endurecido:
  - retry con backoff corto por seccion
  - mismo contrato de salida del bundle
  - tolerancia mejor a fallas transitorias
- concurrencia Finviz endurecida en corrida real:
  - `FINVIZ_MAX_WORKERS` y `FINVIZ_WORKER_TIMEOUT_SECONDS` expuestos desde `config.py`
  - timeout explicito de futures
  - errores por timeout aislados por ticker
- bootstrap de clones limpios alineado con la taxonomia local de bonos:
  - `bond_local_subfamily_rules.json.example` agregado a `data/examples/mappings/`
- `pypdf` movido fuera de dependencias base:
  - extra opcional `byma`
  - el extractor BYMA informa como instalarlo si falta
- limpieza de `analytics` no usado:
  - removidos `fundamentals.py`, `ratings.py`, `news.py` e `insiders.py`
  - el pipeline queda alineado con la superficie activa real
- logging estructurado minimo en flujo real y clientes sensibles:
  - `logging.getLogger(__name__)`
  - warnings en fallas de Finviz y Bonistas
  - sin perder los mensajes de UX en terminal
- limpieza de config no usada:
  - removidos `ALERTA_MEP_DESVIO_PCT` y `ALERTA_PERDIDA_MINIMA`
  - `load_runtime_config()` queda alineado con consumidores reales
- memoria temporal optimizada:
  - lookup previo por ticker
  - sin filtrado repetido de toda la historia por cada fila
  - rachas calculadas sobre buckets ya normalizados
- overlay tecnico enriquecido con Yahoo:
  - `SMA_200`
  - `Dist_SMA200_%`
  - `High_52w` / `Low_52w`
  - `Dist_52w_High_%` / `Dist_52w_Low_%`
  - `Avg_Volume_20d`
- ventana tecnica ampliada a `18mo`:
  - `SMA200` ya puede poblarse en corridas reales normales

## Reproducibilidad

### Configuracion de clone limpio

- estado: `Resuelto`
- complejidad: `Baja`
- impacto: `Alto`

Trabajo hecho:

- documentacion formal de JSON no versionados
- ejemplos `.json.example` para mappings y strategy
- bootstrap minimo desde clone limpio
- metadata base del proyecto en `pyproject.toml`
- workflow de CI con `unittest` para rutas estables

## Proximo foco

Si seguimos mejorando, el trabajo ya pasa de hardening a evolucion de producto:

1. ajustar scoring o persistencia con evidencia de nuevas corridas reales
2. revisar calibraciones futuras por subfamilia si aparecen nuevas corridas borderline
3. seguir monitoreando rotacion de refuerzos con evidencia real:
   - `EWZ` afirmado
   - `VIST` fuera de refuerzo
   - `KO`, `EWZ`, `EEM` como sizing defensivo vigente al `2026-04-09 23:33`
4. observar la variabilidad de cobertura Finviz en corridas reales aun con retry y paralelizacion
5. si alguna vez se quiere ampliar el remanente de `43`, hacerlo como frente nuevo con fuente alternativa o revision ticker por ticker
6. limpiar deuda menor solo si aparece evidencia real
