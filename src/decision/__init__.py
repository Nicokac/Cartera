"""Motor de decision: scoring, acciones y sizing."""

from .actions import assign_action_v2, assign_base_action, enrich_decision_explanations
from .scoring import (
    apply_base_scores,
    apply_technical_overlay_scores,
    build_decision_base,
    consensus_to_score,
    finalize_unified_score,
    rank_score,
)
from .sizing import build_dynamic_allocation, build_operational_proposal, build_prudent_allocation

__all__ = [
    "apply_base_scores",
    "apply_technical_overlay_scores",
    "assign_action_v2",
    "assign_base_action",
    "build_decision_base",
    "build_dynamic_allocation",
    "build_operational_proposal",
    "build_prudent_allocation",
    "consensus_to_score",
    "enrich_decision_explanations",
    "finalize_unified_score",
    "rank_score",
]
