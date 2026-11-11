"""Synthetic image/transport fixtures; nutrition uses authentic offline records."""
import socket

from PIL import Image
import pytest

from agentic_ai.image_workflow_demo import make_offline_workflow, demo_confirmation, raw_food

OWNER = "owner-a"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("M5.5 tests must not contact a model or external service")
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def make_flow(tmp_path):
    count = 0
    def make(text="100 g banana", foods=None, hypotheses=None, **kwargs):
        nonlocal count
        count += 1
        path = tmp_path / f"synthetic-{count}.png"
        with Image.new("RGBA", (19, 13), (40, 90, 30, 150)) as image:
            image.save(path, format="PNG")
        if foods is None:
            foods = [raw_food("banana", "100 g banana", "100", "g")]
        if hypotheses is None:
            hypotheses = {"status": "needs_confirmation", "groups": [
                {"location": "unknown", "labels": ["banana"], "uncertainty_reasons": []}],
                "uncertainty_reasons": ["identity_unconfirmed"]}
        workflow, vision, extraction, provider = make_offline_workflow({text: foods}, hypotheses, **kwargs)
        state = workflow.begin(path, owner=OWNER)
        return workflow, state, vision, extraction, provider
    return make


@pytest.fixture
def start_flow(make_flow):
    def start(text="100 g banana", **kwargs):
        workflow, state, vision, extraction, provider = make_flow(text=text, **kwargs)
        state = workflow.confirm(state.workflow_id, demo_confirmation(state.recognition, text), owner=OWNER)
        return workflow, state, vision, extraction, provider
    return start


@pytest.fixture
def send():
    def reply(workflow, state, index, action, request_id="reply-a"):
        question = next(q for q in state.session.questions if q.item_index == index)
        return workflow.respond(state.workflow_id, {"expected_revision": state.session.revision,
                    "request_id": request_id, "item_id": question.item_id,
                    "question_id": question.question_id, "action": action}, owner=OWNER)
    return reply
