import io
import json
from urllib.error import HTTPError, URLError
import pytest
from pydantic import SecretStr
from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.clients.ollama_client import OllamaClient
from agentic_ai.clients.usda_client import USDAClient
from agentic_ai.config import Settings
from agentic_ai.errors import OllamaConnectionError, OllamaResponseError, OllamaTimeoutError
from agentic_ai.nutrition_config import NutritionSettings
from agentic_ai.nutrition_errors import (MissingCredentialsError, USDAAuthenticationError,
    USDAConnectionError, USDARateLimitError, USDAResponseError, USDATimeoutError)
from agentic_ai.orchestration import AgentOrchestrator
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.orchestration_demo import ScriptedChat
from agentic_ai.providers.usda import LiveUSDAProvider, SnapshotProvider


def retry(service, state, **changes):
    request = {"expected_revision": state.revision, "request_id": "retry_1", **changes}
    return service.retry(state.session_id, request, owner="alice")


@pytest.mark.parametrize("failure", [USDAConnectionError("private_key_123"), USDATimeoutError("private_key_123"),
    USDARateLimitError("private_key_123"), MissingCredentialsError("private_key_123"),
    USDAAuthenticationError("private_key_123"), USDAResponseError("private_key_123"), RuntimeError("private_key_123")])
def test_failed_details_retry_reuses_search_and_completed_items(make_service, raw, failure):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    provider.failures[173424] = failure
    service, state, _, calls = make_service([
        raw("banana", "100 g banana", "100", "g"), raw("egg", "100 g boiled eggs", "100", "g", "boiled")], provider=provider)
    assert state.status == "waiting_for_retry"
    assert "private_key_123" not in state.model_dump_json()
    banana = state.nutrition.items[0].model_dump_json()
    state = retry(service, state)
    assert state.status == "completed"
    assert state.nutrition.items[0].model_dump_json() == banana
    assert len(calls) == 1 and len(provider.searches) == 2
    assert provider.gets == [173944, 173424, 173424]


def test_search_outage_can_retry_without_repeating_extraction(make_service, raw):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    provider.failures["search"] = USDAConnectionError("private service detail")
    service, state, _, calls = make_service([raw("banana", "100 g banana", "100", "g")], provider=provider)
    assert state.status == "waiting_for_retry"
    state = retry(service, state)
    assert state.status == "completed" and len(calls) == 1
    assert len(provider.searches) == 2


@pytest.mark.parametrize("failure", [OllamaConnectionError("private"), OllamaTimeoutError("private"),
    OllamaResponseError("private"), RuntimeError("private")])
def test_ollama_recovery_retains_session_and_safe_errors(raw, failure):
    calls = []
    class Agent:
        def analyze(self, text):
            calls.append(text)
            if len(calls) == 1:
                raise failure
            return FoodUnderstandingAgent(Settings(), ScriptedChat([
                raw("banana", "100 g banana", "100", "g")])).analyze(text)
    service = AgentOrchestrator(food_factory=lambda observer: Agent())
    state = service.start({"text": "100 g banana"}, owner="alice")
    assert state.extraction is None and state.status == "waiting_for_retry"
    assert "private" not in state.model_dump_json()
    old_id = state.session_id
    state = retry(service, state)
    assert state.session_id == old_id and state.status == "completed"
    assert len(calls) == 2


def test_retry_can_target_one_failed_item(make_service, raw):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    provider.failures[173424] = USDAConnectionError("simulated")
    provider.failures[173944] = USDAConnectionError("simulated")
    service, state, _, _ = make_service([
        raw("banana", "100 g banana", "100", "g"), raw("egg", "100 g boiled eggs", "100", "g", "boiled")], provider=provider)
    with service.store.transaction(state.session_id, "alice") as checkpoint:
        item_id = checkpoint.items[0].item_id
    state = retry(service, state, item_id=item_id)
    assert state.status == "waiting_for_retry"
    assert state.nutrition.items[0].status == "complete"
    assert state.nutrition.items[1].status == "error"
    assert provider.gets == [173944, 173424, 173944]


def test_invalid_retry_does_not_change_state(make_service, raw):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    provider.failures[173944] = USDAConnectionError("simulated")
    service, state, _, _ = make_service([raw("banana", "100 g banana", "100", "g")], provider=provider)
    before = state.model_dump_json()
    with pytest.raises(OrchestrationError) as error:
        retry(service, state, item_id="wrong-item")
    assert error.value.code == "invalid_retry_item"
    assert service.get(state.session_id, owner="alice").model_dump_json() == before


def test_completed_session_does_not_retry(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "100 g banana", "100", "g")])
    with pytest.raises(OrchestrationError) as error:
        retry(service, state)
    assert error.value.code == "session_not_actionable"


@pytest.mark.parametrize("failure", [OllamaConnectionError("secret_api_key"), RuntimeError("secret_api_key")])
def test_failed_refinement_preserves_results_and_consumes_budget(make_service, raw, send, failure):
    service, state, _, _ = make_service([raw("banana", "banana")])
    before = state.nutrition.model_dump_json()
    class Fail:
        def analyze(self, text):
            raise failure
    service.food_factory = lambda observer: Fail()
    state = send(service, state, 0, {"kind": "refine_food", "description": "more specific banana"})
    assert state.nutrition.model_dump_json() == before
    assert state.usage.turns == 1 and state.usage.tool_calls == 4
    assert state.error is not None and state.questions
    assert not state.evidence
    assert "secret_api_key" not in state.model_dump_json()
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "100"})
    assert state.status == "completed" and state.error is None


def test_multiple_food_refinement_does_not_replace_one_item(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "banana")])
    before = state.nutrition.model_dump_json()
    service.food_factory = lambda observer: FoodUnderstandingAgent(Settings(), ScriptedChat([
        raw("banana", "100 g banana", "100", "g"), raw("egg", "100 g boiled egg", "100", "g", "boiled")]))
    state = send(service, state, 0, {"kind": "refine_food", "description": "100 g banana and 100 g boiled egg"})
    assert state.error.code == "refinement_requires_one_food"
    assert state.nutrition.model_dump_json() == before and state.usage.turns == 1


def test_caches_can_resume_without_initializing_provider(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "banana")])
    def unavailable_factory(*args):
        raise RuntimeError("unavailable provider configuration")
    service.provider_factory = unavailable_factory
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "100"})
    assert state.status == "completed"


def test_ollama_attempt_budget_bounds_schema_retries(monkeypatch):
    from agentic_ai.clients import ollama_client
    calls = []
    def invalid_response(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(json.dumps({"done": True, "message": {"role": "assistant", "content": "not json"}}).encode())
    monkeypatch.setattr(ollama_client, "urlopen", invalid_response)
    service = AgentOrchestrator(OrchestrationSettings(max_http_attempts=1))
    state = service.start({"text": "banana"}, owner="alice")
    assert state.status == "limit_reached" and state.error.code == "http_attempts_limit"
    assert state.usage.http_attempts == 1 and len(calls) == 1


def test_http_attempt_budget_counts_usda_internal_retries(monkeypatch, raw):
    from agentic_ai.clients import usda_client
    calls = []
    def server_failure(*args, **kwargs):
        calls.append(1)
        raise HTTPError("https://private/?api_key=secret", 503, "secret", {}, None)
    monkeypatch.setattr(usda_client, "urlopen", server_failure)
    service = AgentOrchestrator(OrchestrationSettings(max_http_attempts=1),
        food_factory=lambda observer: FoodUnderstandingAgent(Settings(), ScriptedChat([raw("banana", "banana")])),
        provider_factory=lambda mode, observer: LiveUSDAProvider(USDAClient(
            NutritionSettings(api_key=SecretStr("secret"), retries=2), sleeper=lambda wait: None,
            attempt_observer=observer, cache=False)))
    state = service.start({"text": "banana", "provider": "live"}, owner="alice")
    assert state.status == "limit_reached" and state.usage.http_attempts == 1
    assert len(calls) == 1
    assert "secret" not in state.model_dump_json()


def test_usda_cache_false_never_retains_raw_bodies(monkeypatch):
    from agentic_ai.clients import usda_client
    calls = []
    def respond(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(b'{"foods": [], "totalHits": 0}')
    monkeypatch.setattr(usda_client, "urlopen", respond)
    observed = []
    client = USDAClient(NutritionSettings(api_key=SecretStr("secret")),
                        cache=False, attempt_observer=lambda: observed.append(1))
    client.search("banana")
    client.search("banana")
    client.food(173944)
    assert len(calls) == len(observed) == 3
    assert not client._details and not client._searches


def test_live_provider_missing_credentials_no_snapshot_fallback(monkeypatch, raw):
    service = AgentOrchestrator(food_factory=lambda observer: FoodUnderstandingAgent(Settings(), ScriptedChat([raw("banana", "banana")])),
        provider_factory=lambda mode, observer: LiveUSDAProvider(USDAClient(NutritionSettings(), attempt_observer=observer, cache=False)))
    state = service.start({"text": "banana", "provider": "live"}, owner="alice")
    assert state.status == "waiting_for_retry"
    assert state.nutrition.items[0].issues[0].code == "usda_credentials_missing"
    assert state.nutrition.items[0].record is None and state.usage.http_attempts == 0


def test_model_reasoning_and_tool_exception_never_appear_in_trace(monkeypatch):
    from agentic_ai.clients import ollama_client
    secret_thought = "SECRET_PRIVATE_MODEL_THOUGHT"
    response = {"done": True, "message": {"role": "assistant", "content": '{"foods": []}', "thinking": secret_thought}}
    monkeypatch.setattr(ollama_client, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(response).encode()))
    service = AgentOrchestrator()
    state = service.start({"text": "Nothing to eat"}, owner="alice")
    assert state.status == "completed"
    assert secret_thought not in state.model_dump_json()
    assert state.usage.http_attempts == 1


def test_mocked_live_http_retry_search_and_real_snapshot_details(monkeypatch, raw):
    """Authentic snapshot body through mocked HTTP is NOT live USDA verification."""
    from pathlib import Path
    from agentic_ai.clients import usda_client
    foods = json.loads((Path(__file__).parents[2] / "data/usda/foods.json").read_text(encoding="utf-8"))
    banana = next(f for f in foods if f["fdcId"] == 173944)
    responses = [
        HTTPError("https://private", 429, "private", {"Retry-After": "0"}, None),
        {"totalHits": 1, "foods": [{"fdcId": 173944, "description": "Bananas, raw", "dataType": "SR Legacy"}]},
        banana,
    ]
    calls, waits = [], []
    def respond(request, timeout):
        calls.append(request.get_method())
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(json.dumps(response).encode())
    monkeypatch.setattr(usda_client, "urlopen", respond)
    service = AgentOrchestrator(
        food_factory=lambda observer: FoodUnderstandingAgent(Settings(), ScriptedChat([raw("banana", "100 g banana", "100", "g")])),
        provider_factory=lambda mode, observer: LiveUSDAProvider(USDAClient(
            NutritionSettings(api_key=SecretStr("mock-key"), retries=1), sleeper=waits.append,
            attempt_observer=observer, cache=False)))
    state = service.start({"text": "100 g banana", "provider": "live"}, owner="alice")
    assert state.status == "completed" and state.nutrition.complete_totals.calories == 89
    assert state.usage.http_attempts == 3 and waits == [0]
    assert len(calls) == 3 and not responses
    assert "mock-key" not in state.model_dump_json()
