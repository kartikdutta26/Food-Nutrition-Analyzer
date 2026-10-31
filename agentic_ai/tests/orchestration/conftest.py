"""Scripted extraction and fault injection only; USDA values come from real snapshots."""
import pytest
from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.config import Settings
from agentic_ai.orchestration import AgentOrchestrator
from agentic_ai.orchestration_demo import ScriptedChat, raw_food
from agentic_ai.providers.usda import SnapshotProvider


class RecordingProvider(SnapshotProvider):
    def __init__(self):
        super().__init__()
        self.searches, self.gets = [], []
        self.failures = {}

    def search(self, query):
        self.searches.append(query)
        if "search" in self.failures:
            raise self.failures.pop("search")
        return super().search(query)

    def get(self, fdc_id):
        self.gets.append(fdc_id)
        if fdc_id in self.failures:
            raise self.failures.pop(fdc_id)
        return super().get(fdc_id)


@pytest.fixture
def raw():
    return raw_food


@pytest.fixture
def make_service():
    def build(foods, *, provider=None, settings=None, clock=None):
        provider = provider or RecordingProvider()
        calls = []
        class Agent:
            def analyze(self, text):
                calls.append(text)
                return FoodUnderstandingAgent(Settings(), ScriptedChat(foods)).analyze(text)
        service = AgentOrchestrator(settings, food_factory=lambda observer: Agent(),
            provider_factory=lambda mode, observer: provider, **({"clock": clock} if clock else {}))
        text = " and ".join(food["source_text"] for food in foods) or "Nothing to eat"
        state = service.start({"text": text}, owner="alice")
        return service, state, provider, calls
    return build


@pytest.fixture
def send():
    def send(service, state, index, action, *, request_id=None, **changes):
        question = next(q for q in state.questions if q.item_index == index)
        reply = dict(expected_revision=state.revision, request_id=request_id or f"reply_{state.revision}",
                     question_id=question.question_id, item_id=question.item_id, action=action)
        reply.update(changes)
        return service.respond(state.session_id, reply, owner="alice")
    return send


@pytest.fixture(autouse=True)
def no_network_in_orchestration_tests(monkeypatch):
    """Offline tests must never reach a real TCP service, including local Ollama."""
    import socket
    def blocked(*args, **kwargs):
        raise AssertionError("Unexpected network access in an offline orchestration test")
    monkeypatch.setattr(socket.socket, "connect", blocked)
