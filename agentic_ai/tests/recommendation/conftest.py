"""Authentic snapshot inputs; explicit synthetic mutations are fault tests only."""
import json
import socket
from pathlib import Path
import pytest
from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent
from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.providers.usda import SnapshotProvider
from agentic_ai.schemas.food import FoodUnderstandingResult
from agentic_ai.orchestration import AgentOrchestrator
from agentic_ai.orchestration_demo import raw_food, ScriptedChat
from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.config import Settings

@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("M4 tests must not access the network")
    monkeypatch.setattr(socket.socket, "connect", blocked)

@pytest.fixture
def agent():
    return NutritionRecommendationAgent(clock=lambda: 1001)

@pytest.fixture
def examples():
    payload = json.loads((Path(__file__).parents[2] / "data/demo_extractions.json").read_text())
    provider = SnapshotProvider()
    return [NutritionAnalysisAgent(provider).analyze(FoodUnderstandingResult.model_validate(item["extraction"])) for item in payload]

@pytest.fixture
def complete(examples):
    return examples[0]

@pytest.fixture
def session_factory():
    def build(foods=None, failure=None):
        foods = foods if foods is not None else [raw_food("banana", "100 g banana", "100", "g")]
        class Extractor:
            def analyze(self, text):
                if failure:
                    raise failure
                return FoodUnderstandingAgent(Settings(), ScriptedChat(foods)).analyze(text)
        service = AgentOrchestrator(food_factory=lambda observer: Extractor(),
            provider_factory=lambda mode, observer: SnapshotProvider(), clock=lambda: 1000)
        state = service.start({"text":" and ".join(f["source_text"] for f in foods) or "nothing"},owner="owner")
        return service, state
    return build

@pytest.fixture
def reply():
    def send(service, state, index, action):
        question = next(q for q in state.questions if q.item_index == index)
        return service.respond(state.session_id, {"expected_revision":state.revision,
            "request_id":f"reply_{state.revision}","question_id":question.question_id,
            "item_id":question.item_id,"action":action},owner="owner")
    return send
