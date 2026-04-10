# Referencias externas

Este directorio guarda catalogos y artefactos de referencia extraidos desde fuentes externas.

## BYMA CEDEARs

Para extraer un PDF oficial de BYMA a una tabla reusable:

```powershell
python scripts\extract_byma_cedears_pdf.py "C:\ruta\al\archivo.pdf"
```

Salida:

- `*.csv`: catalogo raw fila por fila
- `*.metadata.json`: metadatos de extraccion
- `*.conflicts.json`: tickers duplicados o ambiguos en el PDF
- `*.ratios.unique.json`: ratios unicos listos para auditar
- `*.comparison.json`: comparacion contra `data/mappings/ratios.json`

Notas:

- `*.ratios.unique.json` no pisa `data/mappings/ratios.json` automaticamente
- si BYMA trae conflictos o duplicados, conviene revisarlos antes de actualizar mappings

Para auditar cobertura de mappings contra el catalogo extraido:

```powershell
python scripts\audit_byma_mapping_coverage.py
```

Salida:

- `byma_mapping_coverage.json`: gaps entre `ratios`, `finviz_map` e `instrument_profile_map`

Para preparar tandas candidatas de expansion de `finviz_map`:

```powershell
python scripts\build_byma_finviz_candidates.py
```

Salida:

- `finviz_candidates/byma_finviz_candidates_batch_*.json`: tandas de candidatos directos `ticker BYMA -> ticker Finviz`
- `finviz_candidates/excluded.json`: casos a revisar manualmente
- `finviz_candidates/summary.json`: resumen de la generacion inicial
- `finviz_candidates/final_status.json`: estado final despues de integrar todas las tandas automaticas

## Estado actual

- `340` candidatos directos ya fueron integrados en `finviz_map.json` e `instrument_profile_map.json`
- `44` casos restantes coinciden exactamente con `excluded.json`
- `363 / 407` tickers tienen cobertura completa contra el catalogo BYMA
- el remanente ya no corresponde a batches automaticos; requiere revision manual

## Criterio actual

- solo mercados compatibles o razonables para Finviz
- solo tickers simples sin mapeo especial
- no se pisa `data/mappings/finviz_map.json` automaticamente
