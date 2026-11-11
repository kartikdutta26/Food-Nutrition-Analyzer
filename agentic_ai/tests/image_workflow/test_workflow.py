from decimal import Decimal

import pytest

from agentic_ai.image_workflow_demo import raw_food
from agentic_ai.image_workflow_errors import ImageWorkflowError
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.providers.usda import SnapshotProvider
from agentic_ai.recommendation_errors import RecommendationError
from .conftest import OWNER


def test_complete_meal_retains_real_values_and_provenance(start_flow):
    workflow, state, vision, extraction, provider = start_flow()
    before = state.session.model_dump_json()
    result = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    assert result.session.status == "completed" and result.session.nutrition.status == "complete"
    assert result.session.nutrition.complete_totals.calories == Decimal("89")
    assert result.recommendations.status == "ready"
    assert result.recommendations.known_subtotals == result.session.nutrition.known_subtotals
    citation = result.recommendations.citations[0]
    assert citation.provenance == provider.get(173944).provenance
    assert citation.provenance.provider == "usda_snapshot" and citation.provenance.snapshot_sha256
    assert citation.provenance.source_url.endswith("/173944/nutrients")
    assert result.session.model_dump_json() == before
    assert workflow.get(state.workflow_id, owner=OWNER).session.model_dump_json() == before
    assert not result.recommendations.context.targets and not result.recommendations.comparisons
    assert vision.calls == 1 and extraction.calls == ["100 g banana"]


def test_multi_food_quantity_preparation_and_portion_clarifications(start_flow, send):
    text = "banana and eggs"
    hypotheses = {"status": "uncertain", "groups": [
        {"location": "left", "labels": ["banana", "plantain"], "uncertainty_reasons": ["ambiguous_identity"]},
        {"location": "right", "labels": ["eggs"], "uncertainty_reasons": []}],
        "uncertainty_reasons": ["ambiguous_identity"]}
    workflow, state, vision, extraction, _ = start_flow(text=text,
        foods=[raw_food("banana", "banana"), raw_food("egg", "eggs")], hypotheses=hypotheses)
    assert state.session.status == "awaiting_clarification"
    initial_extraction = state.session.extraction.model_dump_json()
    state = send(workflow, state, 0, {"kind": "quantity", "quantity": "1", "unit": "piece"}, "banana-count")
    assert any(q.reason == "ambiguous_portion" for q in state.session.questions)
    state = send(workflow, state, 0, {"kind": "select_portion", "portion_id": "93515"}, "banana-medium")
    assert state.session.nutrition.items[0].portion.requested_grams == Decimal("118")
    state = send(workflow, state, 1, {"kind": "preparation", "preparation": "boiled"}, "egg-preparation")
    state = send(workflow, state, 1, {"kind": "measured_grams", "grams": "80.123456789"}, "egg-measure")
    result = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    assert result.session.status == "completed" and result.recommendations.status == "ready"
    assert result.session.extraction.model_dump_json() == initial_extraction
    assert result.session.extraction.foods[1].preparation is None
    assert result.session.nutrition.items[1].food.preparation == "boiled"
    assert result.recommendations.session_evidence == tuple(result.session.evidence)
    assert len(result.session.evidence) == 4 and vision.calls == 1 and extraction.calls == [text]


def test_partial_meal_keeps_unknown_complete_totals(start_flow, send):
    text = "100 g banana and paneer curry"
    workflow, state, _, _, _ = start_flow(text=text, foods=[raw_food("banana", "100 g banana", "100", "g"),
                                                              raw_food("paneer curry", "paneer curry")])
    limited = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    assert limited.recommendations.status == "limited" and limited.recommendations.next_steps
    state = send(workflow, state, 1, {"kind": "leave_unresolved"})
    result = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    n, r = result.session.nutrition, result.recommendations
    assert result.session.status == "completed" and n.status == "partial" and r.status == "limited"
    assert n.complete_totals.calories is None and r.complete_totals.calories is None
    assert r.known_subtotals.calories == Decimal("89")
    assert r.coverage["calories"].known_items == 1 and r.coverage["calories"].total_items == 2
    assert n.items[1].record is None and len(r.citations) == 1
    assert not any(step.code == "clarify" for step in r.next_steps)


def test_missing_fiber_is_unknown_not_zero(start_flow):
    class SyntheticMissingFiber(SnapshotProvider):
        # Explicit synthetic FAULT ONLY. Real fixture bytes and values are unchanged.
        def get(self, fdc_id):
            record = super().get(fdc_id)
            record.nutrients.fiber = None
            record.nutrient_evidence.pop("fiber", None)
            record.issues.append("synthetic_missing_fiber_test_fault")
            return record
    provider = SyntheticMissingFiber()
    workflow, state, _, _, _ = start_flow(provider=provider)
    result = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    assert result.session.nutrition.status == "partial" and result.recommendations.status == "limited"
    assert result.recommendations.complete_totals.fiber is None
    assert result.recommendations.known_subtotals.fiber is None
    assert result.recommendations.coverage["fiber"].known_items == 0
    assert provider.records[173944].nutrients.fiber == Decimal("2.6")


def test_recommendation_is_revision_aware_and_not_cached(start_flow, send):
    workflow, state, _, _, _ = start_flow(text="banana", foods=[raw_food("banana", "banana")])
    old_revision = state.session.revision
    result = workflow.recommend(state.workflow_id, expected_revision=old_revision, owner=OWNER)
    assert result.recommendations.status == "unavailable"
    assert result.recommendations.next_steps[0:]
    state = send(workflow, state, 0, {"kind": "quantity", "quantity": "100", "unit": "g"})
    assert state.recommendations is None
    assert workflow.get(state.workflow_id, owner=OWNER).recommendations is None
    with pytest.raises(ImageWorkflowError) as error:
        workflow.recommend(state.workflow_id, expected_revision=old_revision, owner=OWNER)
    assert error.value.code == "stale_revision"
    current = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    assert current.recommendations.status == "ready"
    assert current.recommendations.input_ref.session_id == state.session.session_id
    assert current.recommendations.input_ref.revision == state.session.revision


@pytest.mark.parametrize("revision", [True, "1", -1, None, 1.0])
def test_invalid_recommendation_revision_is_rejected(start_flow, revision):
    workflow, state, _, _, _ = start_flow()
    with pytest.raises(ImageWorkflowError) as error:
        workflow.recommend(state.workflow_id, expected_revision=revision, owner=OWNER)
    assert error.value.code == "invalid_revision"


def test_m3_rejects_duplicate_and_stale_replies_without_mutation(start_flow):
    workflow, state, _, _, _ = start_flow(text="banana", foods=[raw_food("banana", "banana")])
    q = state.session.questions[0]
    reply = {"expected_revision": state.session.revision, "request_id": "unique-reply", "question_id": q.question_id,
             "item_id": q.item_id, "action": {"kind": "quantity", "quantity": "1", "unit": "piece"}}
    current = workflow.respond(state.workflow_id, reply, owner=OWNER)
    before = current.session.model_dump_json()
    with pytest.raises(OrchestrationError) as error: workflow.respond(state.workflow_id, reply, owner=OWNER)
    assert error.value.code == "duplicate_request"
    reply["request_id"] = "different-reply"
    with pytest.raises(OrchestrationError) as error: workflow.respond(state.workflow_id, reply, owner=OWNER)
    assert error.value.code == "stale_revision"
    assert workflow.get(state.workflow_id, owner=OWNER).session.model_dump_json() == before


def test_only_explicit_target_context_is_forwarded(start_flow):
    workflow, state, _, _, _ = start_flow()
    result = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER,
             context={"targets": [{"nutrient": "calories", "value": "2000", "unit": "kcal", "scope": "daily"}]})
    assert result.recommendations.comparisons[0].relation == "not_compared"
    assert result.recommendations.comparisons[0].reason == "scope_mismatch"
    assert result.session == state.session
