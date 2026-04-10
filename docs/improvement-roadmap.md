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
3. si alguna vez se quiere ampliar el remanente de `43`, hacerlo como frente nuevo con fuente alternativa o revision ticker por ticker
4. limpiar deuda menor solo si aparece evidencia real
