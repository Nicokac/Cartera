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
- CI minima con GitHub Actions para suites estables
- gate absoluto suave para limitar `Refuerzo` en setups no alcistas con momentum corto negativo
- guardas de `Peso_%` en valuacion
- CEDEARs sin `finviz_map`
- contrato explicito de `mep_real`
- lazy loading de `config.py`
- cache acotado en Bonistas
- hardening de render HTML con escape consistente
- constantes canonicas para acciones
- helpers numericos comunes para scoring, liquidez, valuacion y sizing
- exclusion de liquidez en el resumen agregado de memoria temporal
- warnings de pandas en `tests/test_sizing.py`
- cobertura base de clientes externos:
  - `iol`
  - `argentinadatos`
  - `market_data`
  - `finviz_client`

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
2. ampliar cobertura en integraciones secundarias o de borde
3. revisar si el gate absoluto suave necesita calibracion adicional por subfamilia
