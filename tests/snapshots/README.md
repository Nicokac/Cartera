# Snapshots

Usar esta carpeta para guardar snapshots chicos y auditables de corridas de referencia.

Convencion sugerida:
- `YYYY-MM-DD_portfolio_master.json`
- `YYYY-MM-DD_decision_table.csv`
- `YYYY-MM-DD_liquidity_contract.json`
- `YYYY-MM-DD_real_portfolio_master.csv`
- `YYYY-MM-DD_real_decision_table.csv`
- `YYYY-MM-DD_real_technical_overlay.csv`
- `YYYY-MM-DD_real_kpis.json`

Objetivo:
- comparar salidas entre fases del refactor
- detectar regresiones sin depender de APIs vivas

Notas:
- Los snapshots `real_*` salen desde `scripts/generate_real_report.py`.
- Guardan datos ya normalizados; no deben incluir credenciales ni payloads crudos sensibles.
- Baseline funcional estable vigente:
  - `2026-04-04_real_decision_table.csv`
  - `2026-04-04_real_portfolio_master.csv`
  - `2026-04-04_real_technical_overlay.csv`
  - `2026-04-04_real_kpis.json`
- Esa baseline corresponde al primer estado completo del modelo con:
  - overlay técnico activo
  - Finviz fundamentals activos
  - ratings activos en cobertura parcial real
  - ajuste fino de reducción para ETFs/core
- Baseline efectiva posterior dentro del mismo ciclo:
  - mantener la referencia `2026-04-04_*`
  - pero interpretar como estado vigente la corrida donde:
    - `SPY` quedó neutral por ajuste `etf_core`
    - `EWZ` quedó neutral por ajuste `etf_country_region`
    - refuerzos efectivos: `VIST`, `XLU`, `KO`
