from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import OrchestrationError


def assert_rejected(service, state, reply, code, *, owner="alice"):
    before = service.get(state.session_id, owner="alice").model_dump_json()
    with pytest.raises(OrchestrationError) as captured:
        service.respond(state.session_id, reply, owner=owner)
    assert captured.value.code == code
    assert service.get(state.session_id, owner="alice").model_dump_json() == before


def reply_for(state, action=None):
    q = state.questions[0]
    return dict(expected_revision=state.revision, request_id="request_1", question_id=q.question_id,
                item_id=q.item_id, action=action or {"kind": "measured_grams", "grams": "100"})


@pytest.mark.parametrize("field,value,code", [
    ("expected_revision", 0, "stale_revision"),
    ("question_id", "unknown", "stale_question"),
    ("item_id", "unknown", "cross_item_response"),
    ("extra", "forbidden", "invalid_request"),
    ("request_id", "bad id", "invalid_request"),
    ("expected_revision", True, "invalid_request"),
])
def test_invalid_reply_is_atomic(make_service, raw, field, value, code):
    service, state, provider, calls = make_service([raw("banana", "banana")])
    reply = reply_for(state)
    reply[field] = value
    assert_rejected(service, state, reply, code)
    assert provider.gets == [173944] and len(calls) == 1


@pytest.mark.parametrize("grams", [True, False, "0", "-1", "NaN", "Infinity", "1e999999", "1e-999999", "no", "0.1234567891234", "9" * 65])
def test_invalid_grams_never_call_tools(make_service, raw, grams):
    service, state, provider, _ = make_service([raw("banana", "banana")])
    assert_rejected(service, state, reply_for(state, {"kind": "measured_grams", "grams": grams}), "invalid_request")
    assert provider.gets == [173944]


@pytest.mark.parametrize("action,code", [
    ({"kind": "select_food", "fdc_id": 123}, "action_not_allowed"),
    ({"kind": "select_portion", "portion_id": "93515"}, "action_not_allowed"),
    ({"kind": "quantity", "quantity": "-2", "unit": "cup"}, "invalid_request"),
    ({"kind": "quantity", "quantity": "2", "unit": "bucket"}, "invalid_request"),
    ({"kind": "unknown"}, "invalid_request"),
    ({"kind": "measured_grams", "grams": "100", "fdc_id": 173944}, "invalid_request"),
])
def test_inapplicable_action_is_rejected(make_service, raw, action, code):
    service, state, _, _ = make_service([raw("banana", "banana")])
    assert_rejected(service, state, reply_for(state, action), code)


def test_cross_item_response_with_valid_other_item_id(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana"), raw("banana", "banana")])
    reply = reply_for(state)
    reply["item_id"] = state.questions[1].item_id
    assert_rejected(service, state, reply, "cross_item_response")


def test_invalid_food_and_portion_selection_atomic(make_service, raw, send):
    service, state, provider, _ = make_service([raw("apple", "100 g apples", "100", "g")])
    assert_rejected(service, state, reply_for(state, {"kind": "select_food", "fdc_id": 173944}), "invalid_food_selection")
    assert provider.gets == []
    service, state, provider, _ = make_service([raw("roti", "2 rotis", "2", "piece")])
    assert_rejected(service, state, reply_for(state, {"kind": "select_portion", "portion_id": "93515"}), "invalid_portion_selection")
    assert provider.gets == [2707713]


def test_duplicate_request_rejected_without_replay(make_service, raw, send):
    service, state, provider, calls = make_service([raw("banana", "banana"), raw("banana", "banana")])
    reply = reply_for(state)
    state = service.respond(state.session_id, reply, owner="alice")
    reply["expected_revision"] = state.revision
    assert_rejected(service, state, reply, "duplicate_request")
    assert len(calls) == 1 and provider.gets == [173944, 173944]


def test_concurrent_replies_only_one_commits(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    request = reply_for(state)
    def apply(number):
        try:
            return service.respond(state.session_id, {**request, "request_id": f"parallel_{number}"}, owner="alice").status
        except OrchestrationError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(apply, range(2)))
    assert sorted(results) == ["completed", "stale_revision"]
    assert service.get(state.session_id, owner="alice").usage.turns == 1


@pytest.mark.parametrize("method", ["get", "respond", "retry", "close"])
def test_owner_is_required_out_of_band(make_service, raw, method):
    service, state, _, _ = make_service([raw("banana", "banana")])
    before = state.model_dump_json()
    with pytest.raises(OrchestrationError) as error:
        if method == "respond":
            service.respond(state.session_id, reply_for(state), owner="bob")
        elif method == "retry":
            service.retry(state.session_id, {"expected_revision": state.revision, "request_id": "r"}, owner="bob")
        else:
            getattr(service, method)(state.session_id, owner="bob")
    assert error.value.code == "session_not_found"
    assert service.get(state.session_id, owner="alice").model_dump_json() == before


def test_secure_session_ids_and_close(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    other = service.start({"text": "banana"}, owner="alice")
    assert len(state.session_id) >= 43 and state.session_id != other.session_id
    assert not state.session_id.isdigit()
    service.close(state.session_id, owner="alice")
    with pytest.raises(OrchestrationError, match="Session not found"):
        service.get(state.session_id, owner="alice")


def test_ttl_does_not_extend_on_access(make_service, raw):
    now = [1000.0]
    service, state, _, _ = make_service([raw("banana", "banana")],
        settings=OrchestrationSettings(ttl_seconds=10), clock=lambda: now[0])
    now[0] = 1009
    assert service.get(state.session_id, owner="alice").expires_at == 1010
    now[0] = 1010
    with pytest.raises(OrchestrationError):
        service.get(state.session_id, owner="alice")
    assert not service.store._entries


def test_capacity_checked_before_model_and_expiry_reclaims_slot(make_service, raw):
    now = [0]
    service, state, _, calls = make_service([raw("banana", "banana")],
        settings=OrchestrationSettings(max_sessions=1, ttl_seconds=2), clock=lambda: now[0])
    with pytest.raises(OrchestrationError) as error:
        service.start({"text": "banana"}, owner="alice")
    assert error.value.code == "active_session_limit" and len(calls) == 1
    now[0] = 2
    other = service.start({"text": "banana"}, owner="alice")
    assert other.session_id != state.session_id and len(calls) == 2


@pytest.mark.parametrize("setting,limit,reason", [
    ("max_steps", 1, "steps_limit"), ("max_tool_calls", 1, "tool_calls_limit"),
    ("max_trace_events", 4, "trace_limit"),
])
def test_execution_limits_preserve_item_coverage(make_service, raw, setting, limit, reason):
    _, state, _, _ = make_service([raw("banana", "banana"), raw("banana", "banana")],
        settings=OrchestrationSettings(**{setting: limit}))
    assert state.status == "limit_reached" and state.error.code == reason
    assert state.nutrition.total_items == 2
    assert len(state.trace) <= getattr(OrchestrationSettings(**{setting: limit}), "max_trace_events")
    assert state.trace[-1].event == "limit_reached"


def test_turn_limit_stops_without_dropping_completed_item(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "banana"), raw("banana", "banana")],
        settings=OrchestrationSettings(max_turns=1))
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "100"})
    before = state.nutrition.items[0].model_dump_json()
    state = send(service, state, 1, {"kind": "measured_grams", "grams": "100"})
    assert state.status == "limit_reached" and state.error.code == "turns_limit"
    assert state.nutrition.items[0].model_dump_json() == before
    assert state.nutrition.items[1].portion is None
    assert state.usage.turns == 1


def test_request_size_rejected_before_tools(make_service, raw):
    service, state, _, calls = make_service([raw("banana", "banana")],
        settings=OrchestrationSettings(max_request_bytes=256, max_reply_bytes=256))
    with pytest.raises(OrchestrationError) as error:
        service.start({"text": "x" * 1000}, owner="alice")
    assert error.value.code == "request_size_limit" and len(calls) == 1
    assert_rejected(service, state, reply_for(state, {"kind": "refine_food", "description": "x" * 1000}), "request_size_limit")


def test_initial_memory_limit_rejected_before_tools(make_service):
    service, state, _, calls = make_service([], settings=OrchestrationSettings(max_session_bytes=4096))
    with pytest.raises(OrchestrationError) as error:
        service.start({"text": "x" * 4000}, owner="alice")
    assert error.value.code == "session_memory_limit"
    assert len(calls) == 1 and len(service.store._entries) == 1


def test_store_oversize_transaction_keeps_prior_results(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    before = state.nutrition.model_dump_json()
    with pytest.raises(OrchestrationError) as error:
        with service.store.transaction(state.session_id, "alice") as draft:
            draft.original_text = "x" * (service.settings.max_session_bytes + 1)
    assert error.value.code == "session_memory_limit"
    current = service.get(state.session_id, owner="alice")
    assert current.status == "limit_reached"
    assert current.nutrition.model_dump_json() == before
    assert sum(len(x[1]) for x in service.store._entries.values()) <= service.settings.max_store_bytes
    assert all(len(x[1]) <= service.settings.max_session_bytes for x in service.store._entries.values())


def test_unknown_session_and_injected_owner_field(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    reply = reply_for(state)
    reply["owner"] = "alice"
    assert_rejected(service, state, reply, "invalid_request")
    with pytest.raises(OrchestrationError) as error:
        service.get("unknown", owner="alice")
    assert error.value.code == "session_not_found"
