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
  - `2026-04-07_real_decision_table.csv`
  - `2026-04-07_real_portfolio_master.csv`
  - `2026-04-07_real_technical_overlay.csv`
  - `2026-04-07_real_kpis.json`
- Esa baseline corresponde al estado real estable posterior a:
  - reintegracion y hardening del overlay tecnico
  - recuperacion de Finviz real
  - activacion conservadora de scoring absoluto (`0.9 / 0.1`)
  - incorporacion de una capa conservadora de regimen de mercado
  - alineacion de narrativa con thresholds configurables
  - refuerzo conservador para bonos sin disparos espurios en la corrida vigente
- Lectura operativa de esa baseline:
  - overlay tecnico activo `24/24`
  - Finviz fundamentals `24/24`
  - Finviz ratings `17/24`
  - regimen de mercado configurado pero sin flags activos en la macro vigente
  - memoria temporal diaria habilitada con historial en `data/runtime/decision_history.csv`
  - refuerzos efectivos: `VIST`, `KO`, `XLU`, `XLV`
  - reduccion efectiva: `MELI`
  - `SPY` y `AAPL` quedan en `Mantener / Neutral`
  - `GD30` sigue en `Rebalancear / tomar ganancia`
  - ningun bono dispara `Refuerzo`

- Contrato de memoria temporal:
  - una sola observacion canonica por `ticker + fecha`
  - si hay reruns del mismo dia, se reemplaza el snapshot diario
  - la primera version es observacional y no altera score ni accion

- Baseline vigente Bonistas v1 para monitoreo de bonos locales:
  - bloque `Bonos Locales` visible en el HTML real
  - `bond_sov_ar` con paridades operativas coherentes:
    - `GD30`: `87.24%`
    - `AL30`: `85.11%`
    - `GD35`: `75.64%`
  - `bond_bopreal` estabilizado:
    - `BPOC7`: `102.00%`
  - `bond_cer` visible y coherente:
    - `TZX26`: `102.00%`
  - `bond_other` neutralizado y auditable:
    - `TZXD6`: `100.30%`
    - `TZXM7`: `99.30%`
  - volumen spot visible:
    - `GD30`: `4,068,012`
    - `BPOC7`: `580,634`
    - `AL30`: `234,824,216`
  - referencias macro visibles:
    - `CER`: `740.0696`
    - `TAMAR`: `26.25`
    - `BADLAR`: `25.1875`
    - `Reservas BCRA`: `42052.0`
    - `A3500`: `1391.69`
- Taxonomia local ampliada disponible para siguiente iteracion de Bonistas:
  - `bond_hard_dollar`
  - `bond_dual`
  - `bond_dollar_linked`
  - `bond_fixed_rate`
  - `bond_tamar`
  - `bond_badlar`
  - `letter_fixed_rate`

- Baseline vigente de explicabilidad pre-scoring en bonos:
  - `Riesgo pais` visible en `Bonos Locales`
  - `REM inflacion` visible en `Bonos Locales`
  - `REM 12m` visible en `Bonos Locales` cuando el Excel del BCRA esta disponible
  - `Reservas BCRA` visibles en `Bonos Locales` cuando responde la API oficial
  - `A3500` visible en `Bonos Locales` cuando responde la API oficial
  - `BADLAR` y `TAMAR` oficiales visibles cuando responde la API oficial del BCRA
  - `UST 5y` y `UST 10y` visibles en `Bonos Locales` cuando FRED esta disponible
  - `GD30` y `AL30` se explican como `bond_hard_dollar` con:
    - `paridad`
    - `TIR`
    - `riesgo pais`
    - `spread_vs_ust`
    - `reservas_bcra_musd`
    - `a3500_mayorista`
  - `BPOC7` se explica como `bond_bopreal` con:
    - `paridad`
    - `PUT`
    - `riesgo pais`
    - `spread_vs_ust`
    - `reservas_bcra_musd`
    - `a3500_mayorista`
  - `TZX26`, `TZXD6` y `TZXM7` se explican como lectura `CER` con:
    - `TIR real`
    - `paridad`
    - `REM 12m`
    - `REM inflacion`
  - `bonistas_volume_avg_20d` y `bonistas_volume_ratio` siguen pendientes de una fuente historica mas robusta
