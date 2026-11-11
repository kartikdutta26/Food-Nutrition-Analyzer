"""Evidence-driven interpretation rules; no clinical thresholds or diet planning."""
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict

from agentic_ai.recommendation.rendering import RULE_IDS, message
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.schemas.recommendation import TargetComparison


class _Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: str
    ruleset_version: str
    scope: str
    rule_ids: list[str]


def load_catalog():
    path = Path(__file__).resolve().parents[1] / "data/recommendation_rules.json"
    try:
        with path.open("rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            raise ValueError()
        catalog = _Catalog.model_validate_json(raw)
        if catalog.schema_version != "1.0" or catalog.ruleset_version != "1.0" or catalog.scope != "composition_interpretation_only" or set(catalog.rule_ids) != RULE_IDS or len(catalog.rule_ids) != len(RULE_IDS):
            raise ValueError()
        return catalog
    except (OSError, ValueError, TypeError):
        raise RecommendationError("invalid_rules") from None


def apply_rules(nutrition, session, context, facts, citations, *, expired):
    load_catalog()
    observations, suggestions, next_steps = [], [], []
    limitations = [message("record_scope", ("input",)), message("coverage_scope", ("input",)), message("source_recipe", ("input",))]
    meal_facts = [fact for fact in facts if fact.item_index is None]
    available = any(fact.amount is not None for fact in meal_facts)
    terminal = bool(session and session.status in {"failed", "limit_reached"})
    usable = available and not expired and not terminal
    limited = bool(nutrition and nutrition.status != "complete") or bool(session and session.status != "completed")
    if not context.targets:
        limitations.append(message("no_targets", ("context",)))
        if usable:
            suggestions.append(message("supply_target", ("context",)))
    if context.preferences:
        limitations.append(message("preferences", ("context",)))
    if any(citation.portion and citation.portion.method == "user_measured" for citation in citations):
        limitations.append(message("declared_measurement", tuple(c.id for c in citations if c.portion and c.portion.method == "user_measured")))
    if any(citation.attribution == "delegated_backend_record" for citation in citations):
        limitations.append(message("backend_attribution", tuple(c.id for c in citations if c.attribution == "delegated_backend_record")))
    if nutrition and any(item.record and item.record.issues for item in nutrition.items):
        limited = True
        limitations.append(message("source_notes", tuple(c.id for c in citations)))
    if expired:
        limitations.append(message("expired", ("input",)))
        next_steps.append(message("expired", ("input",)))
    elif terminal:
        limitations.append(message("terminal", ("input",)))
        next_steps.append(message("terminal", ("input",)))
    elif session and session.status == "waiting_for_retry":
        limitations.append(message("retry", ("input",)))
        next_steps.append(message("retry", ("input",)))
    if nutrition and nutrition.total_items == 0:
        limitations.append(message("no_food", ("input",)))
    elif not available:
        limitations.append(message("no_values", ("input",)))
    if nutrition and nutrition.total_items and not all(f.coverage.complete for f in meal_facts):
        limitations.append(message("partial", tuple(f.id for f in meal_facts if not f.coverage.complete)))
        if not expired and not terminal:
            suggestions.append(message("complete_evidence", tuple(f.id for f in meal_facts if not f.coverage.complete)))
    if not expired:
        for fact in meal_facts:
            code = "unknown_fact" if fact.amount is None else "complete_fact" if fact.coverage.complete else "subtotal_fact"
            observations.append(message(code, (fact.id,), fact=fact))
    if usable:
        suggestions.append(message("review_evidence", tuple(f.id for f in meal_facts)))
    if session and not expired and not terminal:
        for question in session.questions:
            refs = tuple(f"item-{question.item_index}-{name}" for name in nutrition.coverage)
            next_steps.append(message("clarify", refs, question=question))
    elif nutrition and any(item.status == "needs_clarification" for item in nutrition.items) and not expired and not terminal:
        next_steps.append(message("new_analysis", ("input",)))
    comparisons = []
    by_name = {fact.nutrient:fact for fact in meal_facts}
    for target in context.targets:
        fact = by_name.get(target.nutrient)
        # A stable unknown fact reference exists even when extraction has failed.
        fact_ref = fact.id if fact else "input"
        if not usable:
            relation, reason, code = "not_compared", "session_unavailable", "target_unavailable"
        elif target.scope != "meal":
            relation, reason, code = "not_compared", "scope_mismatch", "target_scope"
        elif not fact.coverage.complete:
            relation, reason, code = "not_compared", "incomplete_nutrient", "target_incomplete"
        else:
            relation = "equal" if fact.amount == target.value else "below" if fact.amount < target.value else "above"
            reason, code = "user_supplied_meal_benchmark", "target_comparison"
        comparisons.append(TargetComparison(nutrient=target.nutrient, target=target.model_copy(deep=True), relation=relation, reason=reason, fact_ref=fact_ref))
        if fact:
            entry = message(code, (fact_ref, "context"), fact=fact, target=target, relation=relation if relation != "not_compared" else None)
            if relation == "not_compared":
                limitations.append(entry)
            else:
                observations.append(entry)
        if relation == "not_compared":
            limited = True
    if any(c.relation != "not_compared" for c in comparisons):
        suggestions.append(message("review_target", ("context",)))
    status = "unavailable" if not available or expired else "limited" if limited or terminal else "ready"
    return status, tuple(observations), tuple(suggestions), tuple(next_steps), tuple(limitations), tuple(comparisons)
