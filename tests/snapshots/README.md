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
  - overlay tecnico activo
  - Finviz fundamentals activos
  - ratings activos en cobertura parcial real
  - ajuste fino de reduccion para ETFs/core
- Baseline efectiva posterior dentro del mismo ciclo:
  - mantener la referencia `2026-04-04_*`
  - pero interpretar como estado vigente la corrida donde:
    - `SPY` quedo neutral por ajuste `etf_core`
    - `EWZ` quedo neutral por ajuste `etf_country_region`
    - `GD30` quedo en `Rebalancear / tomar ganancia` por ajuste `bond_sov_ar`
    - `TZXM7` y `TZXD6` quedaron en `Mantener / monitorear` por endurecimiento de `bond_other`
    - refuerzos efectivos: `VIST`, `XLU`, `KO`
    - taxonomia visible en reporte:
      - `etf_core`
      - `etf_sector`
      - `etf_country_region`
      - `bond_sov_ar`
      - `bond_cer`
      - `bond_bopreal`
      - `bond_other`
