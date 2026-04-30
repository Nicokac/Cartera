from __future__ import annotations

import html

import pandas as pd

from report_primitives import (
    badge_class,
    build_driver_chips,
    build_focus_list,
    esc_text,
    fmt_delta_score,
    fmt_label,
    fmt_pct,
    fmt_score,
    humanize_dimension_value,
    render_metric,
    truncate_text,
)

from decision.action_constants import (
    ACTION_MANTENER_NEUTRAL,
    ACTION_REDUCIR,
    ACTION_REFUERZO,
    NEUTRAL_ACTIONS,
)


def build_decision_table(
    df: pd.DataFrame,
    *,
    action_col: str,
    motive_col: str,
) -> str:
    if df.empty:
        return '<div class="empty">Sin decisiones para mostrar.</div>'

    def _racha_badge(n: int) -> str:
        if n <= 0:
            return "-"
        css = "metric metric-positive" if n >= 7 else ("metric metric-warn" if n >= 4 else "metric metric-neutral")
        return f'<span class="{css}">{n}</span>'

    score_notes: list[str] = []
    rows = []
    ordered = df.sort_values("score_unificado", ascending=False)
    for _, row in ordered.iterrows():
        ticker = esc_text(row["Ticker_IOL"])
        tipo = esc_text(row["Tipo"])
        accion = str(row.get(action_col, ""))
        motivo = esc_text(row.get(motive_col, ""))
        motivo_score = esc_text(row.get("motivo_score", ""))
        accion_previa = row.get("accion_previa")
        delta_score = row.get("score_delta_vs_dia_anterior")
        racha_refuerzo = int(row.get("dias_consecutivos_refuerzo", 0) or 0)
        racha_reduccion = int(row.get("dias_consecutivos_reduccion", 0) or 0)
        racha_mantener = int(row.get("dias_consecutivos_mantener", 0) or 0)
        racha = max(racha_refuerzo, racha_reduccion, racha_mantener)
        if racha <= 0 and accion.strip():
            racha = 1
        driver_html = build_driver_chips(row)
        if motivo_score not in {"", "-"} and motivo_score not in score_notes:
            score_notes.append(motivo_score)
        score_val = float(row["score_unificado"]) if pd.notna(row.get("score_unificado")) else -999
        peso_val = float(row["Peso_%"]) if pd.notna(row.get("Peso_%")) else 0
        rows.append(
            "<tr "
            f"data-ticker=\"{ticker}\" "
            f"data-action=\"{html.escape(accion)}\" "
            f"data-type=\"{tipo}\" "
            f"data-score=\"{score_val:.6f}\" "
            f"data-racha=\"{racha}\" "
            f"data-peso=\"{peso_val:.6f}\">"
            f"<td><strong>{ticker}</strong></td>"
            f"<td>{tipo}</td>"
            f"<td>{render_metric('asset_family', humanize_dimension_value('asset_family', row.get('asset_family')), fmt_label)}</td>"
            f"<td>{render_metric('asset_subfamily', humanize_dimension_value('asset_subfamily', row.get('asset_subfamily')), fmt_label)}</td>"
            f"<td>{render_metric('Peso_%', row.get('Peso_%'), fmt_pct)}</td>"
            f"<td class=\"score\">{render_metric('score_unificado', row['score_unificado'], fmt_score)}</td>"
            f"<td><span class=\"{badge_class(accion)}\">{html.escape(accion)}</span></td>"
            f"<td>{esc_text(accion_previa)}</td>"
            f"<td>{render_metric('score_delta_vs_dia_anterior', delta_score, fmt_delta_score)}</td>"
            f"<td>{_racha_badge(racha)}</td>"
            f"<td>{esc_text(row.get('quality_label', '-'))}</td>"
            f"<td><div class=\"driver-stack\">{driver_html}</div></td>"
            f"<td><div>{motivo}</div></td>"
            "</tr>"
        )

    score_notes_html = ""
    if score_notes:
        items = "".join(f"<li>{note}</li>" for note in score_notes)
        score_notes_html = (
            '<details class="score-notes">'
            "<summary>Ver criterios generales de score</summary>"
            f"<div class=\"muted-inline\"><ul>{items}</ul></div>"
            "</details>"
        )

    return (
        f'{score_notes_html}<div class="table-wrap"><table id="decision-table">'
        '<thead><tr><th scope="col">Ticker</th><th scope="col">Tipo</th><th scope="col">Familia</th><th scope="col">Subfamilia</th>'
        '<th scope="col" class="sortable" data-sort="peso">Peso %</th>'
        '<th scope="col" class="sortable" data-sort="score">Score</th>'
        '<th scope="col">Acción</th><th scope="col">Acción previa</th><th scope="col">\u0394 Score</th>'
        '<th scope="col" class="sortable" data-sort="racha">Racha</th>'
        '<th scope="col">Calidad historia</th>'
        '<th scope="col">Drivers</th><th scope="col">Motivo</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def describe_action_shift(previous_action: object, current_action: object) -> str:
    previous = str(previous_action or "").strip()
    current = str(current_action or "").strip()
    neutral_actions = {ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"}

    if current == ACTION_REFUERZO and previous in neutral_actions:
        return "Sube de convicciÃ³n"
    if current == ACTION_REFUERZO and previous == ACTION_REDUCIR:
        return "Giro desde reducciÃ³n a refuerzo"
    if current == ACTION_REDUCIR and previous in neutral_actions:
        return "Pasa de monitoreo a reducciÃ³n"
    if current == ACTION_REDUCIR and previous == ACTION_REFUERZO:
        return "Giro desde refuerzo a reducciÃ³n"
    if current in neutral_actions and previous == ACTION_REFUERZO:
        return "Vuelve a monitoreo desde refuerzo"
    if current in neutral_actions and previous == ACTION_REDUCIR:
        return "Vuelve a monitoreo desde reducciÃ³n"
    return f"{previous} -> {current}"


def build_decision_priority_board(
    df: pd.DataFrame,
    *,
    action_col: str,
    motive_col: str,
) -> str:
    if df.empty:
        return '<div class="empty">Sin decisiones para priorizar.</div>'

    work = df.copy()
    work["_accion_actual"] = work[action_col].fillna("").astype(str)
    work["_accion_previa"] = work.get("accion_previa", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)
    work["_asset_family"] = work.get("asset_family", pd.Series(index=work.index, dtype=object)).fillna("").astype(str)

    def _build_items(source: pd.DataFrame, *, ascending: bool = False, limit: int = 3, badge_from_action: bool = True) -> list[dict[str, str]]:
        if source.empty:
            return []
        ordered = source.sort_values("score_unificado", ascending=ascending).head(limit)
        items: list[dict[str, str]] = []
        for _, row in ordered.iterrows():
            racha = max(
                int(row.get("dias_consecutivos_refuerzo", 0) or 0),
                int(row.get("dias_consecutivos_reduccion", 0) or 0),
                int(row.get("dias_consecutivos_mantener", 0) or 0),
                1,
            )
            accion = str(row.get(action_col, ""))
            accion_previa = str(row.get("accion_previa", ""))
            shift = describe_action_shift(accion_previa, accion) if accion_previa.strip() and accion_previa.strip() != accion.strip() else ""
            driver_html = build_driver_chips(row)
            detail_parts: list[str] = []
            if shift:
                detail_parts.append(f'<div class="muted-inline">{html.escape(shift)}</div>')
            if driver_html and driver_html != '<span class="muted-inline">-</span>':
                detail_parts.append(f'<div class="driver-stack">{driver_html}</div>')
            elif row.get(motive_col):
                detail_parts.append(f'<div>{html.escape(truncate_text(row.get(motive_col, ""), 96))}</div>')
            items.append(
                {
                    "kicker": str(row.get("Ticker_IOL", "-")),
                    "title": f"{fmt_score(row.get('score_unificado'))} | Racha {racha}",
                    "detail_html": "".join(detail_parts) or '<div class="muted-inline">Sin drivers destacados.</div>',
                    "badge": accion if badge_from_action else None,
                }
            )
        return items

    top_scores = work[work["_accion_actual"] == ACTION_REFUERZO].sort_values("score_unificado", ascending=False)
    bottom_scores = work[
        (pd.to_numeric(work.get("score_unificado"), errors="coerce") < 0)
        & (work["_asset_family"].str.lower() != "liquidity")
        & (~work["_accion_actual"].str.lower().str.contains("liquidez", na=False))
    ].sort_values("score_unificado", ascending=True)
    neutrales = work[work["_accion_actual"].isin(NEUTRAL_ACTIONS)]
    streak_view = work.copy()
    streak_view["_racha"] = streak_view.apply(
        lambda row: max(
            int(row.get("dias_consecutivos_refuerzo", 0) or 0),
            int(row.get("dias_consecutivos_reduccion", 0) or 0),
            int(row.get("dias_consecutivos_mantener", 0) or 0),
            1,
        ),
        axis=1,
    )
    if "Tipo" in streak_view.columns:
        streak_view = streak_view.loc[streak_view["Tipo"].astype(str) != "Liquidez"].copy()
    streak_view = streak_view.loc[streak_view["_racha"] >= 2].sort_values(["_racha", "score_unificado"], ascending=[False, False])
    streak_items: list[dict[str, str]] = []
    for _, row in streak_view.head(5).iterrows():
        accion = str(row.get(action_col, "")).strip()
        calidad = str(row.get("quality_label", "-")).strip() or "-"
        streak_items.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"Racha {int(row.get('_racha', 0) or 0)}",
                "detail": f"Accion {accion} | Calidad {calidad}",
                "badge": accion if accion else None,
            }
        )

    return f"""
    <section class="decision-priority">
      <div class="focus-columns focus-columns-wide">
        <div>
          <h3>Convicciones alcistas</h3>
          {build_focus_list(_build_items(top_scores, ascending=False), empty_message='Sin convicciones alcistas destacadas.', tone='buy')}
        </div>
        <div>
          <h3>Riesgos a recortar</h3>
          {build_focus_list(_build_items(bottom_scores, ascending=True), empty_message='Sin riesgos destacados para recorte.', tone='sell')}
        </div>
        <div>
          <h3>Monitoreo destacado</h3>
          {build_focus_list(_build_items(neutrales, ascending=False, badge_from_action=True), empty_message='Sin monitoreo destacado.', tone='neutral')}
        </div>
        <div>
          <h3>Evolución de racha</h3>
          {build_focus_list(streak_items, empty_message='Sin rachas suficientes para destacar.', tone='neutral')}
        </div>
      </div>
    </section>
    """


def select_decision_view(
    final_decision: pd.DataFrame,
    propuesta: pd.DataFrame,
) -> tuple[pd.DataFrame, str, str]:
    if not propuesta.empty and "accion_operativa" in propuesta.columns:
        motive_col = "comentario_operativo" if "comentario_operativo" in propuesta.columns else "motivo_accion"
        return propuesta, "accion_operativa", motive_col
    return final_decision, "accion_sugerida_v2", "motivo_accion"


def build_family_summary(decision_view: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(decision_view, pd.DataFrame) or decision_view.empty:
        return pd.DataFrame()

    family_base = decision_view.copy()
    if "asset_family" not in family_base.columns:
        family_base["asset_family"] = None
    if "asset_subfamily" not in family_base.columns:
        family_base["asset_subfamily"] = None
    return (
        family_base.groupby(["asset_family", "asset_subfamily"], dropna=False)
        .agg(
            Instrumentos=("Ticker_IOL", "count"),
            Score_Promedio=("score_unificado", "mean"),
        )
        .reset_index()
        .sort_values(["asset_family", "asset_subfamily"], na_position="last")
    )


def build_change_highlights(
    decision_view: pd.DataFrame,
    *,
    action_col: str,
    motive_col: str,
) -> tuple[list[dict[str, str]], str, list[dict[str, str]], list[dict[str, str]]]:
    changed_actions: list[dict[str, str]] = []
    changes_direction_summary = ""
    buy_focus: list[dict[str, str]] = []
    sell_focus: list[dict[str, str]] = []
    if not isinstance(decision_view, pd.DataFrame) or decision_view.empty:
        return changed_actions, changes_direction_summary, buy_focus, sell_focus

    changed_view = decision_view.copy()
    changed_view["_accion_actual"] = changed_view[action_col].fillna("").astype(str)
    changed_view["_accion_previa"] = changed_view.get("accion_previa", pd.Series(index=changed_view.index, dtype=object)).fillna("").astype(str)
    changed_view = changed_view[
        (changed_view["_accion_previa"].str.strip() != "")
        & (changed_view["_accion_actual"].str.strip() != "")
        & (changed_view["_accion_previa"] != changed_view["_accion_actual"])
    ]
    changed_view = changed_view[
        changed_view["_accion_previa"].isin(
            {ACTION_REFUERZO, ACTION_REDUCIR, ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"}
        )
        & changed_view["_accion_actual"].isin(
            {ACTION_REFUERZO, ACTION_REDUCIR, ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"}
        )
        & ~(
            changed_view["_accion_previa"].isin({ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"})
            & changed_view["_accion_actual"].isin({ACTION_MANTENER_NEUTRAL, "Mantener / monitorear"})
        )
    ]
    changed_view["_score_delta_abs"] = pd.to_numeric(
        changed_view.get("score_delta_vs_dia_anterior", pd.Series(index=changed_view.index, dtype=float)),
        errors="coerce",
    ).abs()
    changed_view = changed_view.sort_values(
        ["_score_delta_abs", "score_unificado"],
        ascending=[False, False],
        na_position="last",
    )

    cambios_hacia_refuerzo = int((changed_view["_accion_actual"] == ACTION_REFUERZO).sum())
    cambios_hacia_reduccion = int((changed_view["_accion_actual"] == ACTION_REDUCIR).sum())
    cambios_hacia_neutral = int(changed_view["_accion_actual"].isin(NEUTRAL_ACTIONS).sum())
    changes_direction_summary = f"""
      <div class="meta change-direction-meta">
        <span>Suben de convicciÃ³n: <strong>{cambios_hacia_refuerzo}</strong></span>
        <span>Bajan a reducciÃ³n: <strong>{cambios_hacia_reduccion}</strong></span>
        <span>Vuelven a monitoreo: <strong>{cambios_hacia_neutral}</strong></span>
      </div>
    """

    for _, row in changed_view.head(6).iterrows():
        previous_action = str(row["_accion_previa"])
        current_action = str(row["_accion_actual"])
        score_delta = row.get("score_delta_vs_dia_anterior")
        score_delta_label = fmt_delta_score(score_delta)
        delta_fragment = f" Î” score {score_delta_label}." if score_delta_label != "-" else ""
        changed_actions.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": describe_action_shift(previous_action, current_action),
                "detail": truncate_text(
                    f"Antes: {previous_action}. Ahora: {current_action}.{delta_fragment} {fmt_label(row.get(motive_col, ''))}",
                    180,
                ),
                "badge": current_action,
            }
        )

    refuerzo_view = decision_view[decision_view[action_col].astype(str) == ACTION_REFUERZO].sort_values(
        "score_unificado", ascending=False
    )
    reducir_view = decision_view[decision_view[action_col].astype(str) == ACTION_REDUCIR].sort_values(
        "score_unificado", ascending=True
    )
    for _, row in refuerzo_view.head(3).iterrows():
        buy_focus.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"Score {fmt_score(row.get('score_unificado'))}",
                "detail": truncate_text(row.get(motive_col, ""), 140),
                "badge": ACTION_REFUERZO,
            }
        )
    for _, row in reducir_view.head(3).iterrows():
        sell_focus.append(
            {
                "kicker": str(row.get("Ticker_IOL", "-")),
                "title": f"Score {fmt_score(row.get('score_unificado'))}",
                "detail": truncate_text(row.get(motive_col, ""), 140),
                "badge": ACTION_REDUCIR,
            }
        )

    return changed_actions, changes_direction_summary, buy_focus, sell_focus

