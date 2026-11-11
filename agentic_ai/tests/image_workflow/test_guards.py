from copy import deepcopy

import pytest
from pydantic import ValidationError

from agentic_ai.image_workflow import ImageNutritionWorkflow
from agentic_ai.image_workflow_config import ImageWorkflowSettings
from agentic_ai.image_workflow_demo import demo_confirmation, raw_food
from agentic_ai.image_workflow_errors import ImageWorkflowError
from agentic_ai.nutrition_errors import USDAConnectionError
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.providers.usda import SnapshotProvider
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.tools.image_input import ImageInputError
from agentic_ai.vision_runtime_errors import VisionRuntimeError
from .conftest import OWNER


@pytest.mark.parametrize("operation", ["get", "confirm", "respond", "retry", "recommend", "close"])
def test_foreign_owner_cannot_access_or_operate_session(start_flow, operation):
    workflow, state, _, extraction, _ = start_flow()
    before = state.session.model_dump_json()
    method = getattr(workflow, operation)
    with pytest.raises(ImageWorkflowError) as error:
        if operation in {"confirm", "respond", "retry"}: method(state.workflow_id, {}, owner="owner-b")
        elif operation == "recommend": method(state.workflow_id, expected_revision=1, owner="owner-b")
        else: method(state.workflow_id, owner="owner-b")
    assert error.value.code == "workflow_not_found"
    assert workflow.get(state.workflow_id, owner=OWNER).session.model_dump_json() == before
    assert len(extraction.calls) == 1


@pytest.mark.parametrize("owner", [None, "", 1, True, "x"*257, "\ud800"])
def test_invalid_owner_is_rejected_before_image_processing(make_flow, owner):
    workflow, state, vision, _, _ = make_flow()
    with pytest.raises(ImageWorkflowError) as error: workflow.begin("not-a-private-file.png", owner=owner)
    assert error.value.code == "invalid_owner" and vision.calls == 1


@pytest.mark.parametrize("identifier", [None, False, 1, [], "", "missing", "x"*101])
def test_invalid_or_unknown_workflow_ids_are_safe(make_flow, identifier):
    workflow, _, _, _, _ = make_flow()
    with pytest.raises(ImageWorkflowError) as error: workflow.get(identifier, owner=OWNER)
    assert error.value.code == "workflow_not_found"


@pytest.mark.parametrize("operation", ["respond", "retry", "recommend"])
def test_no_nutrition_or_recommendation_before_confirmation(make_flow, operation):
    workflow, state, _, extraction, _ = make_flow()
    with pytest.raises(ImageWorkflowError) as error:
        if operation == "recommend": workflow.recommend(state.workflow_id, expected_revision=0, owner=OWNER)
        else: getattr(workflow, operation)(state.workflow_id, {}, owner=OWNER)
    assert error.value.code == "confirmation_required" and not extraction.calls


@pytest.mark.parametrize("field,value", [
    ("max_workflows", 0), ("max_workflows", 101), ("max_workflows", True),
    ("ttl_seconds", 0), ("ttl_seconds", 86401), ("ttl_seconds", "100"),
    ("max_metadata_bytes", 262145), ("max_store_bytes", 16777217), ("max_output_bytes", 8388609),
])
def test_workflow_configuration_cannot_exceed_bounds(field, value):
    with pytest.raises(ValidationError): ImageWorkflowSettings(**{field: value})


def test_forged_settings_are_revalidated(make_flow):
    workflow, _, _, _, _ = make_flow()
    with pytest.raises(ImageWorkflowError) as error:
        ImageNutritionWorkflow(vision_agent=workflow.vision_agent, orchestrator=workflow.orchestrator,
                               settings=ImageWorkflowSettings.model_construct(max_workflows=999))
    assert error.value.code == "invalid_configuration"


@pytest.mark.parametrize("field,code", [("max_metadata_bytes", "metadata_limit"), ("max_store_bytes", "metadata_limit"),
                                      ("max_output_bytes", "output_limit")])
def test_limit_failure_never_creates_m3_session(make_flow, field, code):
    with pytest.raises(ImageWorkflowError) as error: make_flow(workflow_settings=ImageWorkflowSettings(**{field: 1024}))
    assert error.value.code == code


def test_workflow_capacity_is_reserved_before_vision(make_flow, tmp_path):
    workflow, state, vision, _, _ = make_flow(workflow_settings=ImageWorkflowSettings(max_workflows=1))
    with pytest.raises(ImageWorkflowError) as error: workflow.begin("absent.png", owner=OWNER)
    assert error.value.code == "workflow_limit" and vision.calls == 1
    workflow.close(state.workflow_id, owner=OWNER)
    next_state = workflow.begin(next(tmp_path.glob("synthetic-*.png")), owner=OWNER)
    assert next_state.workflow_id != state.workflow_id and vision.calls == 2


def test_pending_workflow_expires_without_starting_session(make_flow):
    now = [1000.0]
    workflow, state, _, extraction, _ = make_flow(clock=lambda: now[0], workflow_settings=ImageWorkflowSettings(ttl_seconds=1))
    confirmation = demo_confirmation(state.recognition, "100 g banana")
    now[0] += 1
    with pytest.raises(ImageWorkflowError) as error: workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert error.value.code == "workflow_not_found" and not extraction.calls


def test_workflow_respects_existing_m3_expiry(start_flow):
    now = [1000.0]
    workflow, state, _, _, _ = start_flow(clock=lambda: now[0], orchestration_settings=OrchestrationSettings(ttl_seconds=1))
    assert state.expires_at == state.session.expires_at
    now[0] += 1
    with pytest.raises(ImageWorkflowError): workflow.recommend(state.workflow_id, expected_revision=1, owner=OWNER)
    with pytest.raises(OrchestrationError): workflow.orchestrator.get(state.session.session_id, owner=OWNER)


def test_slow_get_cannot_return_expired_workflow(start_flow, monkeypatch):
    now = [1000.0]
    workflow, state, _, _, _ = start_flow(clock=lambda: now[0], workflow_settings=ImageWorkflowSettings(ttl_seconds=1))
    original = workflow.orchestrator.get
    def slow(*args, **kwargs):
        value = original(*args, **kwargs)
        now[0] += 1
        return value
    monkeypatch.setattr(workflow.orchestrator, "get", slow)
    with pytest.raises(ImageWorkflowError) as error: workflow.get(state.workflow_id, owner=OWNER)
    assert error.value.code == "workflow_not_found"


@pytest.mark.parametrize("confirmed", [False, True])
def test_close_removes_owned_workflow_and_session(make_flow, confirmed):
    workflow, state, _, _, _ = make_flow()
    if confirmed: state = workflow.confirm(state.workflow_id, demo_confirmation(state.recognition, "100 g banana"), owner=OWNER)
    sid = state.session.session_id if state.session else None
    workflow.close(state.workflow_id, owner=OWNER)
    with pytest.raises(ImageWorkflowError): workflow.get(state.workflow_id, owner=OWNER)
    if sid:
        with pytest.raises(OrchestrationError): workflow.orchestrator.get(sid, owner=OWNER)


@pytest.mark.parametrize("kind", ["known", "unexpected"])
def test_start_failure_consumes_confirmation_and_sanitizes_error(make_flow, monkeypatch, kind):
    workflow, state, _, _, _ = make_flow()
    calls = []
    def broken(*args, **kwargs):
        calls.append(True)
        if kind == "known": raise OrchestrationError("active_session_limit", "PRIVATE ERROR")
        raise RuntimeError("PRIVATE ERROR")
    monkeypatch.setattr(workflow.orchestrator, "start", broken)
    confirmation = demo_confirmation(state.recognition, "100 g banana")
    with pytest.raises((ImageWorkflowError, OrchestrationError)) as error:
        workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert "PRIVATE" not in str(error.value)
    failed = workflow.get(state.workflow_id, owner=OWNER)
    assert failed.phase == "start_failed" and failed.handoff is not None and failed.session is None
    with pytest.raises(ImageWorkflowError) as error: workflow.confirm(state.workflow_id, confirmation, owner=OWNER)
    assert error.value.code == "confirmation_consumed" and len(calls) == 1


def test_provider_failure_and_retry_use_existing_m3_revision_guards(start_flow):
    class Once(SnapshotProvider):
        failed = False
        def get(self, fdc_id):
            if not self.failed:
                self.failed = True
                raise USDAConnectionError("SIMULATED outage; no network")
            return super().get(fdc_id)
    workflow, state, vision, extraction, _ = start_flow(provider=Once())
    assert state.session.status == "waiting_for_retry"
    result = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=OWNER)
    assert result.recommendations.status != "ready"
    retry = {"expected_revision": state.session.revision, "request_id": "retry-a"}
    state = workflow.retry(state.workflow_id, retry, owner=OWNER)
    assert state.session.status == "completed" and state.recommendations is None
    assert vision.calls == 1 and len(extraction.calls) == 1
    with pytest.raises(OrchestrationError) as error: workflow.retry(state.workflow_id, retry, owner=OWNER)
    assert error.value.code == "duplicate_request"


def test_returned_session_is_not_a_reference_to_store(start_flow):
    workflow, state, _, _, _ = start_flow()
    before = workflow.get(state.workflow_id, owner=OWNER).session.model_dump_json()
    state.session.nutrition.complete_totals.calories = 12345
    assert workflow.get(state.workflow_id, owner=OWNER).session.model_dump_json() == before


def test_m4_detects_inconsistent_session_evidence(start_flow, monkeypatch):
    workflow, state, _, _, _ = start_flow()
    original = workflow.orchestrator.get
    def altered(*args, **kwargs):
        session = original(*args, **kwargs)
        session.nutrition.complete_totals.calories += 1
        return session
    monkeypatch.setattr(workflow.orchestrator, "get", altered)
    with pytest.raises(RecommendationError) as error: workflow.recommend(state.workflow_id, expected_revision=1, owner=OWNER)
    assert error.value.code == "inconsistent_nutrition"
    assert original(state.session.session_id, owner=OWNER).nutrition.complete_totals.calories == 89


def test_recommendation_dependency_cannot_mutate_session_copy(start_flow):
    workflow, state, _, _, _ = start_flow()
    delegate = workflow.recommendation_agent
    class Mutating:
        def recommend_session(self, session, **kwargs):
            result = delegate.recommend_session(session, **kwargs)
            session.revision += 1
            return result
    workflow.recommendation_agent = Mutating()
    with pytest.raises(ImageWorkflowError) as error: workflow.recommend(state.workflow_id, expected_revision=1, owner=OWNER)
    assert error.value.code == "dependency_mutation"
    assert workflow.get(state.workflow_id, owner=OWNER).session == state.session


def test_changed_session_during_recommendation_returns_no_stale_guidance(start_flow):
    workflow, state, _, _, _ = start_flow(text="banana", foods=[raw_food("banana", "banana")])
    delegate = workflow.recommendation_agent
    class ConcurrentChange:
        def recommend_session(self, session, **kwargs):
            result = delegate.recommend_session(session, **kwargs)
            q = session.questions[0]
            workflow.orchestrator.respond(session.session_id, {"expected_revision": session.revision,
                "request_id": "external-reply", "question_id": q.question_id, "item_id": q.item_id,
                "action": {"kind": "quantity", "quantity": "100", "unit": "g"}}, owner=OWNER)
            return result
    workflow.recommendation_agent = ConcurrentChange()
    with pytest.raises(ImageWorkflowError) as error: workflow.recommend(state.workflow_id, expected_revision=1, owner=OWNER)
    assert error.value.code == "stale_revision"
    current = workflow.get(state.workflow_id, owner=OWNER)
    assert current.session.revision == 2 and current.recommendations is None


def test_m4_failure_leaves_source_session_unchanged(start_flow, caplog, capsys):
    workflow, state, _, _, _ = start_flow()
    class Broken:
        def recommend_session(self, *args, **kwargs): raise RuntimeError("PRIVATE model text and path")
    workflow.recommendation_agent = Broken()
    with pytest.raises(ImageWorkflowError) as error: workflow.recommend(state.workflow_id, expected_revision=1, owner=OWNER)
    assert error.value.code == "operation_failed" and "PRIVATE" not in str(error.value)
    assert workflow.get(state.workflow_id, owner=OWNER).session == state.session
    assert not caplog.records and capsys.readouterr() == ("", "")


def test_bad_image_and_bad_vision_never_start_m3(make_flow, tmp_path):
    workflow, _, vision, extraction, _ = make_flow()
    path = tmp_path / "broken.png"; path.write_bytes(b"bad")
    with pytest.raises(ImageInputError): workflow.begin(path, owner=OWNER)
    vision.content = '{"nutrition":{"calories":500}}'
    with pytest.raises(VisionRuntimeError): workflow.begin(next(tmp_path.glob("synthetic-*.png")), owner=OWNER)
    assert not extraction.calls and not workflow.orchestrator.store._entries
