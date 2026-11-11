from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from agentic_ai.image_workflow_demo import demo_confirmation, raw_food
from agentic_ai.image_workflow_errors import ImageWorkflowError
from agentic_ai.vision_errors import VisionContractError
from .conftest import OWNER


def test_begin_performs_preprocessing_and_vision_only(make_flow):
    workflow, state, vision, extraction, provider = make_flow()
    assert state.phase == "awaiting_confirmation" and state.session is None
    assert state.handoff is None and state.recommendations is None
    assert vision.calls == 1 and not extraction.calls
    assert not workflow.orchestrator.store._entries
    assert state.recognition.preprocessing.metadata_removed
    assert state.recognition.preprocessing.media_type == "image/png"
    assert all(c.edible_grams is None for g in state.recognition.groups for c in g.candidates)


@pytest.mark.parametrize("field,value", [
    ("user_confirmed", False), ("user_confirmed", 1), ("expected_result_id", "wrong"),
    ("expected_revision", 2), ("expected_image_sha256", "b"*64),
    ("expected_result_sha256", "b"*64), ("acknowledged_question_ids", []),
    ("confirmed_meal_text", ""), ("decisions", []), ("owner", "attacker"),
    ("nutrition", {"calories": 500}),
])
def test_confirmation_rejection_is_atomic(make_flow, field, value):
    workflow, state, _, extraction, _ = make_flow()
    confirmation = demo_confirmation(state.recognition, "100 g banana")
    confirmation[field] = value
    with pytest.raises(VisionContractError):
        workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert workflow.get(state.workflow_id, owner=OWNER).phase == "awaiting_confirmation"
    assert not extraction.calls and not workflow.orchestrator.store._entries


@pytest.mark.parametrize("field", ["confirmed_meal_text", "user_confirmed", "expected_result_sha256"])
def test_missing_confirmation_fields_cannot_be_filled_from_caption(make_flow, field):
    workflow, state, _, extraction, _ = make_flow()
    confirmation = demo_confirmation(state.recognition, "100 g banana")
    del confirmation[field]
    with pytest.raises(VisionContractError): workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert not extraction.calls


def test_mutated_caller_recognition_cannot_replace_server_copy(make_flow):
    workflow, state, _, extraction, _ = make_flow()
    object.__setattr__(state.recognition.groups[0].candidates[0], "label", "apple")
    confirmation = demo_confirmation(state.recognition, "100 g apple")
    with pytest.raises(VisionContractError): workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert workflow.get(state.workflow_id, owner=OWNER).recognition.groups[0].candidates[0].label == "banana"
    assert not extraction.calls


def test_hypotheses_are_retained_separately_from_user_correction(make_flow):
    text = "100 g banana"
    hypotheses = {"status": "needs_confirmation", "groups": [
        {"location": "unknown", "labels": ["apple"], "uncertainty_reasons": []}],
        "uncertainty_reasons": ["identity_unconfirmed"]}
    workflow, state, _, extraction, _ = make_flow(hypotheses=hypotheses)
    confirmation = demo_confirmation(state.recognition, "apple")
    confirmation.update(confirmed_meal_text=text, decisions=[{"group_id": "group-1", "action": "correct_identity",
                        "corrected_label": "banana", "text_span": {"start": 6, "end": 12}}])
    result = workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert result.recognition.groups[0].candidates[0].label == "apple"
    assert result.handoff.confirmation.confirmed_meal_text == text
    assert extraction.calls == [text]
    assert result.session.nutrition.items[0].record.provenance.fdc_id == 173944


def test_confirmation_is_single_use_even_with_identical_valid_payload(start_flow):
    workflow, state, _, extraction, _ = start_flow()
    confirmation = state.handoff.confirmation
    with pytest.raises(ImageWorkflowError) as error: workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert error.value.code == "confirmation_consumed"
    assert len(workflow.orchestrator.store._entries) == 1 and len(extraction.calls) == 1


def test_concurrent_confirmation_starts_only_once(make_flow):
    workflow, state, _, extraction, _ = make_flow()
    confirmation = demo_confirmation(state.recognition, "100 g banana")
    def attempt(_):
        try: return workflow.confirm(state.workflow_id, confirmation, owner=OWNER).phase
        except ImageWorkflowError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == ["confirmation_consumed", "session_started"]
    assert len(extraction.calls) == 1 and len(workflow.orchestrator.store._entries) == 1


@pytest.mark.parametrize("status,reasons", [("uncertain", ["unrecognized_content"]), ("no_food_detected", ["no_food_identified"])])
def test_empty_or_uncertain_vision_can_only_proceed_with_explicit_manual_text(make_flow, status, reasons):
    workflow, state, _, extraction, _ = make_flow(hypotheses={"status": status, "groups": [], "uncertainty_reasons": reasons})
    assert not extraction.calls
    confirmation = demo_confirmation(state.recognition, "100 g banana")
    result = workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert result.recognition.status == status and not result.recognition.groups
    assert result.session.status == "completed" and extraction.calls == ["100 g banana"]


def test_same_image_fresh_results_reject_cross_workflow_confirmation(make_flow, tmp_path):
    workflow, first, _, extraction, _ = make_flow()
    from PIL import Image
    path = tmp_path / "same.png"
    with Image.new("RGBA", (19, 13), (40, 90, 30, 150)) as image: image.save(path)
    second = workflow.begin(path, owner=OWNER)
    assert first.recognition.image.original_sha256 == second.recognition.image.original_sha256
    assert first.recognition.result_id != second.recognition.result_id
    with pytest.raises(VisionContractError):
        workflow.confirm(second.workflow_id, demo_confirmation(first.recognition, "100 g banana"), owner=OWNER)
    assert not extraction.calls
