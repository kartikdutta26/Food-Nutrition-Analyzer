"""Scripted offline scenarios and an explicit real-Qwen interactive CLI.

Nothing here contacts live USDA unless --provider live is explicitly selected.
"""
import argparse
import json
import sys
from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.config import Settings
from agentic_ai.nutrition_errors import USDAConnectionError
from agentic_ai.orchestration import AgentOrchestrator
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.providers.usda import SnapshotProvider

OWNER = "local-cli-user"  # A future web adapter must use its authenticated subject.


class ScriptedChat:
    """A test double providing declared raw food JSON, never actual model inference."""
    def __init__(self, foods):
        self.foods = foods

    def chat(self, messages, schema):
        return json.dumps({"foods": self.foods})


def raw_food(name, source, quantity=None, unit=None, preparation=None):
    return dict(name=name, source_text=source, quantity_text=quantity, unit=unit,
                preparation=preparation)


def scripted_orchestrator(foods, provider=None):
    return AgentOrchestrator(food_factory=lambda observer: FoodUnderstandingAgent(
        Settings(), ScriptedChat(foods)), provider_factory=lambda mode, observer: provider or SnapshotProvider())


def reply(service, state, index, action, request_id):
    question = next(q for q in state.questions if q.item_index == index)
    return service.respond(state.session_id, dict(expected_revision=state.revision,
        request_id=request_id, item_id=question.item_id, question_id=question.question_id,
        action=action), owner=OWNER)


def show(label, state):
    print(json.dumps({"scenario": label, "extraction_mode": "scripted JSON test double; no Qwen3 inference",
                      "nutrition_mode": "authentic local USDA snapshots; no live USDA verification",
                      "session": state.model_dump(mode="json")}, ensure_ascii=False), flush=True)


def offline_examples():
    indian = scripted_orchestrator([
        raw_food("roti", "2 rotis", "2", "piece"),
        raw_food("white rice", "cooked white rice", preparation="cooked")])
    state = indian.start({"text": "I ate 2 rotis and cooked white rice."}, owner=OWNER)
    show("Indian meal: two missing portion details", state)
    state = reply(indian, state, 1, {"kind": "quantity", "quantity": "0.5", "unit": "cup"}, "rice-half-cup")
    show("Rice resolved; roti unchanged", state)
    state = reply(indian, state, 0, {"kind": "select_portion", "portion_id": "299422"}, "small-roti")
    assert state.status == "completed" and state.nutrition.status == "complete"
    show("Indian meal complete: USDA small roti and half-cup rice", state)

    international = scripted_orchestrator([
        raw_food("apple", "100 g apples", "100", "g"),
        raw_food("banana", "1 banana", "1", "piece")])
    state = international.start({"text": "I ate 100 g apples and 1 banana."}, owner=OWNER)
    show("International meal: skin and banana size need confirmation", state)
    before = state.model_dump_json()
    try:
        reply(international, state, 0, {"kind": "select_food", "fdc_id": 999999}, "wrong-id")
    except OrchestrationError as error:
        assert error.code == "invalid_food_selection"
        assert international.get(state.session_id, owner=OWNER).model_dump_json() == before
        print(json.dumps({"scenario": "unsuccessful selection rejected atomically", "error": error.code}))
    state = reply(international, state, 0, {"kind": "select_food", "fdc_id": 171688}, "apple-with-skin")
    state = reply(international, state, 1, {"kind": "select_portion", "portion_id": "93515"}, "medium-banana")
    assert state.status == "completed" and state.nutrition.status == "complete"
    show("International meal complete", state)

    class FailingOnce(SnapshotProvider):
        def __init__(self):
            super().__init__()
            self.failed = False

        def get(self, fdc_id):
            if not self.failed:
                self.failed = True
                raise USDAConnectionError("Scripted outage; no HTTP request occurred")
            return super().get(fdc_id)

    recovery = scripted_orchestrator([raw_food("egg", "100 g boiled eggs", "100", "g", "boiled")], FailingOnce())
    state = recovery.start({"text": "100 g boiled eggs"}, owner=OWNER)
    assert state.status == "waiting_for_retry"
    show("Simulated provider outage; search checkpoint retained", state)
    state = recovery.retry(state.session_id, {"expected_revision": state.revision, "request_id": "recover"}, owner=OWNER)
    assert state.status == "completed"
    show("Recovered session; cached search reused", state)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline-examples", action="store_true")
    mode.add_argument("--text", help="Actual local Qwen3 inference; then structured JSON replies on stdin.")
    parser.add_argument("--provider", choices=["snapshot", "live"], default="snapshot")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.offline_examples:
        if args.provider != "snapshot":
            parser.error("Offline examples require snapshot mode.")
        return offline_examples()
    service = AgentOrchestrator()
    try:
        state = service.start({"text": args.text, "provider": args.provider}, owner=OWNER)
        print(json.dumps({"extraction_mode": "actual local Ollama Qwen3 inference",
                          "nutrition_mode": args.provider, "session": state.model_dump(mode="json")}))
        while state.status in {"awaiting_clarification", "waiting_for_retry"}:
            print("Enter a full ReplyRequest JSON, a RetryRequest JSON, or 'quit':", file=sys.stderr)
            line = sys.stdin.readline()
            if not line or line.strip() == "quit":
                break
            try:
                request = json.loads(line)
                state = (service.respond(state.session_id, request, owner=OWNER) if "action" in request
                         else service.retry(state.session_id, request, owner=OWNER))
                print(state.model_dump_json())
            except (ValueError, OrchestrationError) as error:
                print(json.dumps({"error": getattr(error, "code", "invalid_json")}))
                try:
                    state = service.get(state.session_id, owner=OWNER)
                except OrchestrationError as missing:
                    print(json.dumps({"error": missing.code}))
                    return 1
                print(state.model_dump_json())
        return int(state.status in {"failed", "limit_reached", "waiting_for_retry"})
    except OrchestrationError as error:
        print(json.dumps({"error": error.code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
