import pytest
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.schemas.nutrition import SearchResults
from agentic_ai.schemas.orchestration import ReplyRequest


@pytest.mark.parametrize("bad", [None, [], "bad", {"text": ""}, {"text": "   "},
    {"text": 12}, {"text": "banana", "provider": "unknown"}, {"text": "banana", "owner": "alice"},
    {"text": "banana\x00"}, {"text": "x" * 4001}])
def test_invalid_start_never_infers(make_service, bad):
    service, _, _, calls = make_service([])
    with pytest.raises(OrchestrationError) as error:
        service.start(bad, owner="alice")
    assert error.value.code == "invalid_request" and len(calls) == 1


@pytest.mark.parametrize("owner", [None, "", 12, "x" * 257])
def test_invalid_owner_context(make_service, owner):
    service, state, _, calls = make_service([])
    with pytest.raises(OrchestrationError) as error:
        service.get(state.session_id, owner=owner)
    assert error.value.code == "invalid_owner_context" and len(calls) == 1


def test_global_store_limit_is_enforced_before_extra_tools(make_service):
    service, _, _, calls = make_service([], settings=OrchestrationSettings(max_store_bytes=4096))
    for _ in range(10):
        try:
            service.start({"text": "Nothing to eat"}, owner="alice")
        except OrchestrationError as error:
            assert error.code == "store_memory_limit"
            break
    else:
        pytest.fail("Global store quota never enforced")
    assert sum(entry[2] for entry in service.store._entries.values()) <= 4096
    assert len(calls) <= 3


def test_real_record_exceeding_tiny_session_quota_returns_terminal_session(raw):
    from agentic_ai.orchestration_demo import scripted_orchestrator
    from agentic_ai.orchestration import AgentOrchestrator
    from agentic_ai.agents.food_agent import FoodUnderstandingAgent
    from agentic_ai.config import Settings
    from agentic_ai.orchestration_demo import ScriptedChat
    service = AgentOrchestrator(OrchestrationSettings(max_session_bytes=4096),
        food_factory=lambda observer: FoodUnderstandingAgent(Settings(), ScriptedChat([raw("banana", "banana")])))
    state = service.start({"text": "banana"}, owner="alice")
    assert state.status == "limit_reached" and state.error.code == "session_memory_limit"
    assert state.usage.tool_calls == 3
    assert service.get(state.session_id, owner="alice") == state
    assert len(service.store._entries[state.session_id][1]) <= 4096


def test_session_expires_while_tool_is_running(raw):
    from agentic_ai.orchestration import AgentOrchestrator
    from agentic_ai.agents.food_agent import FoodUnderstandingAgent
    from agentic_ai.config import Settings
    from agentic_ai.orchestration_demo import ScriptedChat
    now = [0]
    class Slow:
        def analyze(self, text):
            now[0] = 2
            return FoodUnderstandingAgent(Settings(), ScriptedChat([raw("banana", "banana")])).analyze(text)
    provider_calls = []
    def provider(*args):
        provider_calls.append(1)
        raise AssertionError("Expired workflow must not call further tools")
    service = AgentOrchestrator(OrchestrationSettings(ttl_seconds=1), clock=lambda: now[0],
        food_factory=lambda observer: Slow(), provider_factory=provider)
    with pytest.raises(OrchestrationError) as error:
        service.start({"text": "banana"}, owner="alice")
    assert error.value.code == "session_not_found"
    assert not service.store._entries and not provider_calls


def test_typed_reply_contract_is_supported(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    q = state.questions[0]
    request = ReplyRequest.model_validate(dict(expected_revision=state.revision, request_id="typed",
        question_id=q.question_id, item_id=q.item_id, action={"kind": "measured_grams", "grams": "90"}))
    result = service.respond(state.session_id, request, owner="alice")
    assert result.status == "completed"


def test_response_from_another_session_is_rejected(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    other = service.start({"text": "banana"}, owner="alice")
    q = other.questions[0]
    before = state.model_dump_json()
    with pytest.raises(OrchestrationError) as error:
        service.respond(state.session_id, dict(expected_revision=state.revision, request_id="other_session",
            question_id=q.question_id, item_id=q.item_id, action={"kind": "measured_grams", "grams": "90"}), owner="alice")
    assert error.value.code == "stale_question"
    assert service.get(state.session_id, owner="alice").model_dump_json() == before


def test_source_identity_conflict_cannot_confirm_wrong_description(make_service, raw, send):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    class Inconsistent:
        def search(self, query):
            return provider.search(query)
        def get(self, fdc_id):
            record = provider.get(fdc_id)
            record.provenance.description = "Apples, raw, without skin"
            return record
    service, state, _, _ = make_service([raw("apple", "100 g apples", "100", "g")], provider=Inconsistent())
    state = send(service, state, 0, {"kind": "select_food", "fdc_id": 171688})
    assert state.status == "waiting_for_retry"
    assert state.nutrition.items[0].record is None
    assert state.nutrition.items[0].issues[0].code == "invalid_usda_response"
    assert state.nutrition.complete_totals.calories is None


def test_truncated_search_requires_confirmation(make_service, raw, send):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    class Truncated:
        def search(self, query):
            search = provider.search(query)
            search.exhaustive = False
            return search
        def get(self, fdc_id):
            return provider.get(fdc_id)
    service, state, _, _ = make_service([raw("banana", "100 g banana", "100", "g")], provider=Truncated())
    assert state.questions[0].reason == "search_incomplete" and provider.gets == []
    state = send(service, state, 0, {"kind": "select_food", "fdc_id": 173944})
    assert state.status == "completed"


def test_portion_selection_cannot_contradict_size(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "1 small banana", "1", "piece")])
    # This exact source size resolves automatically; a reply is not permitted.
    assert state.status == "completed"
    assert state.nutrition.items[0].portion.portion.qualifiers == ["small"]


def test_unknown_bowl_weight_not_invented(make_service, raw, send):
    service, state, _, _ = make_service([raw("white rice", "one bowl cooked white rice", "one", "bowl", "cooked")])
    assert state.nutrition.items[0].portion is None and state.nutrition.complete_totals.calories is None
    assert "select_portion" not in state.questions[0].allowed_actions
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "175"})
    assert state.status == "completed"
    assert state.nutrition.items[0].portion.method == "user_measured"


def test_excessive_candidate_result_is_safe_error(make_service, raw):
    from conftest import RecordingProvider
    from agentic_ai.schemas.nutrition import FoodCandidate
    provider = RecordingProvider()
    class Excessive:
        def search(self, query):
            return SearchResults(candidates=[FoodCandidate(fdc_id=i+1, description="Bananas, raw", data_type="SR Legacy") for i in range(51)], exhaustive=True, scope="synthetic excessive metadata")
    _, state, _, _ = make_service([raw("banana", "banana")], provider=Excessive())
    assert state.status == "waiting_for_retry"
    assert state.nutrition.items[0].issues[0].code == "invalid_usda_response"


def test_close_releases_capacity(make_service, raw):
    service, state, _, calls = make_service([raw("banana", "banana")], settings=OrchestrationSettings(max_sessions=1))
    service.close(state.session_id, owner="alice")
    state = service.start({"text": "banana"}, owner="alice")
    assert state.status == "awaiting_clarification" and len(calls) == 2


def test_trace_limit_on_clarification_preserves_exact_previous_totals(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "banana"), raw("banana", "100 g banana", "100", "g")],
        settings=OrchestrationSettings(max_trace_events=8))
    before = state.nutrition.items[1].model_dump_json()
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "50"})
    assert state.status == "limit_reached" and state.error.code == "trace_limit"
    assert state.nutrition.items[1].model_dump_json() == before
    assert len(state.trace) == 8 and state.trace[-1].event == "limit_reached"
