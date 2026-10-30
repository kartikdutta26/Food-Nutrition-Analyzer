"""Opt-in local inference: these tests never substitute a fake model."""

import json
import os
from pathlib import Path

import pytest

from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.config import Settings


CASES = json.loads(Path(__file__).with_name("live_cases.json").read_text(encoding="utf-8"))
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("NUTRIAI_RUN_LIVE_TESTS") != "1", reason="Set NUTRIAI_RUN_LIVE_TESTS=1 for actual Ollama inference"),
]


@pytest.fixture(scope="module")
def live_agent():
    # Always evaluate the requested installed model, not an accidental .env override.
    settings = Settings.from_environment().model_copy(update={"model": "qwen3:4b-instruct"})
    return FoodUnderstandingAgent(settings)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_actual_qwen_extraction(live_agent, case):
    result = live_agent.analyze(case["text"])
    print(json.dumps({"case": case["id"], "input": case["text"], "model": live_agent.settings.model, "result": result.model_dump()}, ensure_ascii=True))
    assert result.status == case["status"]
    assert len(result.foods) == len(case["foods"])
    for actual, expected in zip(result.foods, case["foods"], strict=True):
        assert expected["name"] in actual.name.casefold()
        if expected["quantity"] is None:
            assert actual.quantity is None
        else:
            assert actual.quantity == pytest.approx(expected["quantity"])
        for field in ("unit", "preparation"):
            if field in expected:
                assert getattr(actual, field) == expected[field]
        if "issues" in expected:
            assert set(expected["issues"]) <= set(actual.issues)
        assert actual.source_text in case["text"]
    assert bool(result.questions) == (result.status == "needs_clarification")
    assert "calories" not in result.model_dump_json()
