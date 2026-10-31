import json
import pytest
from pydantic import ValidationError
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.orchestration_demo import main


def test_offline_cli_covers_multi_turn_and_recovery(capsys):
    assert main(["--offline-examples"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(rows) == 8
    assert any(r.get("error") == "invalid_food_selection" for r in rows)
    states = [r["session"] for r in rows if "session" in r]
    assert sum(s["status"] == "completed" for s in states) == 3
    assert any(s["status"] == "waiting_for_retry" for s in states)
    assert all("scripted" in r["extraction_mode"] and "no live" in r["nutrition_mode"] for r in rows if "session" in r)


def test_offline_cli_cannot_enable_live_usda():
    with pytest.raises(SystemExit) as error:
        main(["--offline-examples", "--provider", "live"])
    assert error.value.code == 2


@pytest.mark.parametrize("field,value", [
    ("max_sessions", 0), ("max_sessions", 101), ("ttl_seconds", 0),
    ("max_trace_events", 3), ("max_steps", 1001), ("max_turns", 31),
    ("max_http_attempts", 0), ("max_session_bytes", 100_000_000),
    ("max_store_bytes", 100_000_000), ("max_reply_bytes", 100_000),
])
def test_configuration_hard_bounds(field, value):
    with pytest.raises(ValidationError):
        OrchestrationSettings(**{field: value})


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("NUTRIAI_ORCH_MAX_SESSIONS", "7")
    assert OrchestrationSettings.from_environment().max_sessions == 7
    monkeypatch.setenv("NUTRIAI_ORCH_MAX_SESSIONS", "bad")
    with pytest.raises(OrchestrationError) as error:
        OrchestrationSettings.from_environment()
    assert error.value.code == "invalid_configuration"


def test_interactive_cli_recovers_from_invalid_selection(monkeypatch, capsys):
    import sys
    from agentic_ai import orchestration_demo as demo
    service = demo.scripted_orchestrator([demo.raw_food("banana", "banana")])
    monkeypatch.setattr(demo, "AgentOrchestrator", lambda: service)
    class Replies:
        count = 0
        def readline(self):
            self.count += 1
            session_id = next(iter(service.store._entries))
            state = service.get(session_id, owner=demo.OWNER)
            question = state.questions[0]
            action = ({"kind": "select_food", "fdc_id": 173944} if self.count == 1
                      else {"kind": "measured_grams", "grams": "100"})
            return json.dumps(dict(expected_revision=state.revision, request_id=f"cli_{self.count}",
                item_id=question.item_id, question_id=question.question_id, action=action)) + "\n"
    monkeypatch.setattr(sys, "stdin", Replies())
    assert demo.main(["--text", "banana"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert any(row.get("error") == "action_not_allowed" for row in rows)
    assert rows[-1]["status"] == "completed"
    assert rows[-1]["nutrition"]["complete_totals"]["calories"] == "89.0000"
