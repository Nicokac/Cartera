# Referencias externas

Este directorio guarda catálogos y artefactos de referencia extraídos desde fuentes externas.

## BYMA CEDEARs

Para extraer un PDF oficial de BYMA a una tabla reusable:

```powershell
python scripts\extract_byma_cedears_pdf.py "C:\ruta\al\archivo.pdf"
```

Salida esperada:

- `*.csv`: catálogo raw fila por fila
- `*.metadata.json`: metadatos de extracción
- `*.conflicts.json`: tickers duplicados o ambiguos en el PDF
- `*.ratios.unique.json`: ratios únicos listos para auditar
- `*.comparison.json`: comparación contra `data/mappings/ratios.json`

Nota:
- `*.ratios.unique.json` no pisa `data/mappings/ratios.json` automáticamente
- si BYMA trae conflictos o duplicados, primero conviene revisarlos

Para auditar cobertura de mappings contra el catálogo extraído:

```powershell
python scripts\audit_byma_mapping_coverage.py
```

Salida esperada:

- `byma_mapping_coverage.json`: gaps entre `ratios`, `finviz_map` e `instrument_profile_map`

Para preparar tandas candidatas de expansión de `finviz_map`:

```powershell
python scripts\build_byma_finviz_candidates.py
```

Salida esperada:

- `finviz_candidates/byma_finviz_candidates_batch_*.json`: tandas de candidatos directos `ticker BYMA -> ticker Finviz`
- `finviz_candidates/excluded.json`: casos a revisar manualmente
- `finviz_candidates/summary.json`: resumen de la tanda generada

Criterio actual:

- sólo mercados compatibles o razonables para Finviz
- sólo tickers simples sin mapeo especial
- no pisa `data/mappings/finviz_map.json` automáticamente
