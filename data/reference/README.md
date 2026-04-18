# Referencias externas

Este directorio guarda catalogos y artefactos de referencia extraidos desde fuentes externas.

## BYMA CEDEARs

Para extraer un PDF oficial de BYMA a una tabla reusable:

```powershell
pip install pypdf
python scripts\extract_byma_cedears_pdf.py "C:\ruta\al\archivo.pdf"
```

Alternativa si instalas el proyecto desde `pyproject.toml`:

```powershell
pip install .[byma]
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
- `finviz_candidates/manual_review_status.json`: backlog manual restante y casos rescatados
- `data/mappings/unsupported_byma_tickers.json`: exclusion formal del remanente fuera del circuito automatico

Para validar que el remanente manual esta consistente con la auditoria:

```powershell
python scripts\validate_byma_manual_backlog.py
```

## Estado actual

Este directorio documenta el circuito de auditoria y actualizacion de referencias externas. Los numeros de cobertura pueden cambiar a medida que se regeneran artefactos; la fuente de verdad es siempre la salida mas reciente de los scripts de auditoria y comparacion.

## Criterio actual

- solo mercados compatibles o razonables para Finviz
- solo tickers simples sin mapeo especial
- no se pisa `data/mappings/finviz_map.json` automaticamente
