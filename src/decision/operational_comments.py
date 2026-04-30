from __future__ import annotations

import pandas as pd

from common.numeric import to_float_or_none
from decision.action_constants import (
    ACTION_DESPLEGAR_LIQUIDEZ,
    ACTION_MANTENER_LIQUIDEZ,
    ACTION_MANTENER_LIQUIDEZ_BLOQUEADA,
    ACTION_MANTENER_MONITOREAR,
    ACTION_REBALANCEAR,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
)


def _fmt_pct_short(value: object) -> str | None:
    number = to_float_or_none(value)
    if pd.isna(number):
        return None
    return f"{float(number):.1f}%"


def _join_with_y(parts: list[str]) -> str:
    clean = [part for part in parts if part]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + " y " + clean[-1]


def build_operational_comment(row: pd.Series) -> str:
    accion = row["accion_operativa"]
    tech = row.get("Tech_Trend")
    beta = row.get("Beta")
    asset_subfamily = row.get("asset_subfamily")
    local_subfamily = row.get("bonistas_local_subfamily")
    parity = _fmt_pct_short(row.get("bonistas_paridad_pct"))
    tir = _fmt_pct_short(row.get("bonistas_tir_pct"))
    tir_gap = _fmt_pct_short(row.get("bonistas_tir_vs_avg_365d_pct"))
    md = to_float_or_none(row.get("bonistas_md"))
    riesgo_pais = to_float_or_none(row.get("bonistas_riesgo_pais_bps"))
    reservas_bcra = to_float_or_none(row.get("bonistas_reservas_bcra_musd"))
    a3500_value = to_float_or_none(row.get("bonistas_a3500_mayorista"))
    a3500_txt = f"{float(a3500_value):.2f}" if pd.notna(a3500_value) else None
    rem_inflacion = _fmt_pct_short(row.get("bonistas_rem_inflacion_mensual_pct"))
    rem_inflacion_12m = _fmt_pct_short(row.get("bonistas_rem_inflacion_12m_pct"))
    ust_10y = _fmt_pct_short(row.get("bonistas_ust_10y_pct"))
    ust_spread = _fmt_pct_short(row.get("bonistas_spread_vs_ust_pct"))
    put_flag = bool(row.get("bonistas_put_flag")) if pd.notna(row.get("bonistas_put_flag")) else False

    if accion == ACTION_DESPLEGAR_LIQUIDEZ:
        return "Liquidez disponible para fondear refuerzos sin vender posiciones de riesgo."
    if accion == ACTION_MANTENER_LIQUIDEZ:
        return "Liquidez conservada como reserva tactica."
    if accion == ACTION_MANTENER_LIQUIDEZ_BLOQUEADA:
        return "Liquidez excluida del fondeo por politica explicita del analisis."
    if accion == ACTION_REBALANCEAR:
        if local_subfamily == "bond_hard_dollar":
            if parity and tir:
                details: list[str] = []
                if pd.notna(riesgo_pais):
                    details.append(f"riesgo pais {int(riesgo_pais)} bps")
                if ust_spread:
                    details.append(f"spread {ust_spread} sobre UST")
                if pd.notna(reservas_bcra):
                    details.append(f"reservas {int(reservas_bcra)} MUSD")
                if a3500_txt:
                    details.append(f"A3500 {a3500_txt}")
                tail = ""
                if details:
                    tail = " con " + _join_with_y(details)
                return (
                    f"Hard-dollar soberano con paridad {parity} y TIR {tir}{tail}; "
                    "priorizar rebalanceo o toma parcial de ganancia."
                )
            return "Hard-dollar soberano con ganancia extendida; priorizar rebalanceo o toma parcial de ganancia."
        if local_subfamily == "bond_bopreal":
            if parity and put_flag:
                details: list[str] = []
                if pd.notna(riesgo_pais):
                    details.append(f"riesgo pais {int(riesgo_pais)} bps")
                if ust_spread:
                    details.append(f"spread {ust_spread} sobre UST")
                if pd.notna(reservas_bcra):
                    details.append(f"reservas {int(reservas_bcra)} MUSD")
                if a3500_txt:
                    details.append(f"A3500 {a3500_txt}")
                tail = ""
                if details:
                    tail = " con " + _join_with_y(details)
                return (
                    f"Bopreal con paridad {parity} y opcionalidad PUT{tail}; "
                    "priorizar rebalanceo o toma parcial de ganancia."
                )
            return "Bopreal con senal parcial de salida; priorizar rebalanceo o toma parcial de ganancia."
        if asset_subfamily == "bond_sov_ar":
            return "Soberano AR con ganancia extendida; priorizar rebalanceo o toma parcial de ganancia."
        return "Bono con senal parcial de salida; priorizar rebalanceo o toma parcial de ganancia."
    if accion == ACTION_REFUERZO:
        if local_subfamily == "bond_cer":
            details: list[str] = []
            if tir:
                details.append(f"TIR real {tir}")
            if parity:
                details.append(f"paridad {parity}")
            if rem_inflacion_12m:
                details.append(f"REM 12m {rem_inflacion_12m}")
            if rem_inflacion:
                details.append(f"REM mensual {rem_inflacion}")
            if details:
                return "Refuerzo CER por " + _join_with_y(details) + "; privilegiar carry real e inflacion esperada."
            return "Refuerzo prudente en bono CER por mejora relativa de carry real."
        if local_subfamily == "bond_bopreal":
            details: list[str] = []
            if parity:
                details.append(f"paridad {parity}")
            if tir:
                details.append(f"TIR {tir}")
            if put_flag:
                details.append("PUT disponible")
            if ust_spread:
                details.append(f"spread {ust_spread} sobre UST")
            if details:
                return "Refuerzo Bopreal por " + _join_with_y(details) + "; privilegiar carry y opcionalidad."
            return "Refuerzo prudente en Bopreal por carry y opcionalidad."
        if asset_subfamily == "bond_other":
            details: list[str] = []
            if tir:
                details.append(f"TIR {tir}")
            if parity:
                details.append(f"paridad {parity}")
            if pd.notna(md):
                details.append(f"MD {float(md):.2f}")
            if details:
                return "Refuerzo prudente en bono local por " + _join_with_y(details) + "."
            return "Refuerzo prudente en bono local por score compuesto favorable."
        if tech == "Alcista fuerte":
            return "Refuerzo favorecido por score alto y soporte tecnico alcista."
        if pd.notna(beta) and beta < 0.8:
            return "Refuerzo defensivo con beta controlada."
        return "Refuerzo razonable por score compuesto favorable."
    if accion == ACTION_REDUCIR:
        if tech == "Bajista":
            return "Reduccion favorecida por score debil y tecnico bajista."
        if pd.notna(beta) and beta > 1.5:
            return "Reducir por beta alta y deterioro relativo."
        return "Reduccion o rebalanceo sugerido por score compuesto debil."
    if accion == ACTION_MANTENER_MONITOREAR:
        if local_subfamily == "bond_hard_dollar":
            details: list[str] = []
            if parity:
                details.append(f"paridad {parity}")
            if tir:
                details.append(f"TIR {tir}")
            if pd.notna(riesgo_pais):
                details.append(f"riesgo pais {int(riesgo_pais)} bps")
            if ust_spread:
                details.append(f"spread {ust_spread} sobre UST")
            elif ust_10y:
                details.append(f"UST 10y {ust_10y}")
            if pd.notna(reservas_bcra):
                details.append(f"reservas {int(reservas_bcra)} MUSD")
            if a3500_txt:
                details.append(f"A3500 {a3500_txt}")
            if details:
                return (
                    "Hard-dollar soberano en monitoreo por "
                    + _join_with_y(details)
                    + "; seguir riesgo soberano y compresion de spread."
                )
            return "Hard-dollar soberano en monitoreo; seguir riesgo soberano y compresion de spread."
        if local_subfamily == "bond_cer":
            if tir and parity and rem_inflacion_12m and rem_inflacion:
                return (
                    f"Bono CER en monitoreo con TIR real {tir}, paridad {parity}, "
                    f"REM 12m {rem_inflacion_12m} y REM mensual {rem_inflacion}; "
                    "seguir inflacion esperada y carry."
                )
            if tir and parity and rem_inflacion_12m:
                return (
                    f"Bono CER en monitoreo con TIR real {tir}, paridad {parity} y REM 12m {rem_inflacion_12m}; "
                    "seguir inflacion esperada y carry."
                )
            if tir and parity and rem_inflacion:
                return (
                    f"Bono CER en monitoreo con TIR real {tir}, paridad {parity} y REM {rem_inflacion}; "
                    "seguir inflacion esperada y carry."
                )
            if tir and parity:
                return (
                    f"Bono CER en monitoreo con TIR real {tir} y paridad {parity}; "
                    "seguir inflacion esperada y carry."
                )
            return "Bono CER en zona neutral; mantener y monitorear carry e inflacion."
        if local_subfamily == "bond_bopreal":
            if parity and put_flag:
                details: list[str] = [f"paridad {parity}", "PUT disponible"]
                if pd.notna(riesgo_pais):
                    details.append(f"riesgo pais {int(riesgo_pais)} bps")
                if ust_spread:
                    details.append(f"spread {ust_spread} sobre UST")
                if pd.notna(reservas_bcra):
                    details.append(f"reservas {int(reservas_bcra)} MUSD")
                if a3500_txt:
                    details.append(f"A3500 {a3500_txt}")
                return (
                    "Bopreal en monitoreo con "
                    + _join_with_y(details)
                    + "; "
                    "seguir compresion y liquidez."
                )
            if tir_gap:
                riesgo_txt = f" y riesgo pais {int(riesgo_pais)} bps" if pd.notna(riesgo_pais) else ""
                return (
                    f"Bopreal en monitoreo con TIR relativa {tir_gap}{riesgo_txt}; "
                    "seguir compresion y liquidez."
                )
            return "Bopreal en zona prudente; mantener y monitorear compresion y liquidez."
        if asset_subfamily == "bond_cer":
            return "Bono CER en zona neutral; mantener y monitorear carry e inflacion."
        if asset_subfamily == "bond_bopreal":
            return "Bopreal en zona prudente; mantener y monitorear compresion y liquidez."
        if asset_subfamily == "bond_other":
            return "Bono sin clasificar en zona prudente; mantener y revisar clasificacion si suma relevancia."
        if asset_subfamily == "bond_sov_ar":
            return "Soberano AR sin senal extrema; mantener y monitorear riesgo y ganancias acumuladas."
    return "Mantener y monitorear evolucion."
