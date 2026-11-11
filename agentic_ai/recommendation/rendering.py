"""Only these controlled templates can become recommendation prose.

Untrusted food descriptions, preferences, goals, source notes and error strings
are never template parameters. Attribution metadata is returned separately.
"""
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.schemas.recommendation import InterpretationMessage

LABELS = {"calories":"Calories", "protein":"Protein", "carbs":"Carbohydrates", "fats":"Fats", "fiber":"Fiber"}
STATIC = {
    "record_scope": "Checks establish consistency with the supplied records, not an independent USDA verification or a health assessment.",
    "coverage_scope": "Coverage counts food items, not food weight, accuracy or dietary adequacy.",
    "source_recipe": "Database reference composition does not establish the composition of every homemade recipe.",
    "no_targets": "No comparison target was supplied. No goal or target has been inferred.",
    "preferences": "Supplied preferences are retained as context. No specific-food substitutions or allergy-safety claims are made.",
    "declared_measurement": "Measured grams are declared upstream user input; M4 did not independently measure the food.",
    "backend_attribution": "Backend USDA attribution is retained. Underlying USDA details were not independently fetched by M4.",
    "source_notes": "One or more source records include data-quality notes; inspect their upstream evidence before interpretation.",
    "partial": "Some nutrient contributions are unknown. Known subtotals are not complete meal totals.",
    "review_evidence": "Review the per-item composition and source evidence when interpreting this meal; no new foods or serving amounts are prescribed.",
    "complete_evidence": "Confirm unresolved foods and portions, or obtain documented missing nutrient data, before interpreting incomplete nutrients as complete totals.",
    "supply_target": "For a benchmark comparison, supply your own meal-scoped target and matching unit; the agent does not calculate a target.",
    "review_target": "Review the supplied meal benchmark and contributing items before deciding whether any change is appropriate. The benchmark is not a clinical recommendation.",
    "retry": "A stage is waiting for retry. Use the existing orchestrator retry operation; M4 does not rerun tools.",
    "terminal": "This session is terminal. Retained evidence can be inspected, but no further session replies or retries are proposed.",
    "expired": "This session has expired. Obtain a current analysis before using recommendations; M4 has not retrieved a replacement session.",
    "no_food": "No foods were identified. No consumption amount or zero-nutrient meal has been inferred.",
    "no_values": "No usable nutrient amounts are available. Resolve the upstream analysis before interpreting nutrition.",
    "new_analysis": "If complete interpretation is needed, supply clarified details in a new analysis; no current actionable question is available.",
}
RULE_IDS = set(STATIC) | {"complete_fact", "subtotal_fact", "unknown_fact", "target_comparison", "target_scope", "target_incomplete", "target_unavailable", "clarify"}


def message(code, refs=(), *, fact=None, target=None, relation=None, question=None):
    # Parameter types come only from validated evidence and fixed enums, never prose.
    if code in STATIC:
        text = STATIC[code]
    elif code in {"complete_fact", "subtotal_fact", "unknown_fact"}:
        label = LABELS[fact.nutrient]
        coverage = f"{fact.coverage.known_items}/{fact.coverage.total_items} food items"
        if code == "unknown_fact":
            text = f"{label}: unavailable; {coverage} have known values. Unknown is not zero."
        else:
            basis = "complete meal total" if code == "complete_fact" else "known subtotal only"
            text = f"{label}: {fact.amount} {fact.unit} ({basis}; {coverage})."
    elif code == "target_comparison":
        text = f"{LABELS[fact.nutrient]}: {fact.amount} {fact.unit} is {relation} the explicitly supplied meal benchmark of {target.value} {target.unit}. This is an arithmetic comparison, not a health judgment."
    elif code == "target_scope":
        text = f"{LABELS[fact.nutrient]}: the supplied daily target is not compared with a single meal; daily intake and remaining allowance are unknown."
    elif code == "target_incomplete":
        text = f"{LABELS[fact.nutrient]}: no target comparison is made because this nutrient has incomplete coverage."
    elif code == "target_unavailable":
        text = f"{LABELS[fact.nutrient]}: no target comparison is made for this unavailable or terminal session."
    elif code == "clarify":
        text = f"Item {question.item_index + 1}: answer the existing clarification question using one of its allowed actions. No portion or food choice is assumed."
    else:
        raise RecommendationError("invalid_rules")
    if relation is not None and relation not in {"below", "equal", "above"}:
        raise RecommendationError("invalid_rules")
    return InterpretationMessage(code=code, text=text, rule_id=code, evidence_refs=tuple(refs),
        question_id=question.question_id if question else None,
        item_id=question.item_id if question else None,
        item_index=question.item_index if question else None,
        allowed_actions=tuple(question.allowed_actions) if question else ())
