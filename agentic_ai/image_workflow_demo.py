"""Offline M5.5 example: synthetic pixels, simulated vision/M1 transport, real M2-M4."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.agents.image_food_agent import ImageFoodRecognitionAgent
from agentic_ai.clients.ollama_vision_client import VisionInferenceReply
from agentic_ai.config import Settings
from agentic_ai.errors import OllamaResponseError
from agentic_ai.image_workflow import ImageNutritionWorkflow
from agentic_ai.orchestration import AgentOrchestrator
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.providers.usda import SnapshotProvider
from agentic_ai.schemas.vision import VisionModelProvenance
from agentic_ai.adapters.vision_handoff import recognition_fingerprint
from agentic_ai.vision_runtime_config import VisionRuntimeSettings


DISCLOSURE = {
    "image": "generated synthetic RGB pixels; not a photograph of the proposed foods",
    "vision": "SIMULATED scripted VisionInferenceReply; no model execution or accuracy claim",
    "vision_provenance": "synthetic placeholders, not an installed model attestation",
    "M1": "SIMULATED scripted extraction JSON; real FoodUnderstandingAgent validation/normalization",
    "confirmation": "explicit scripted DEMO USER inputs; not inferred from the image or a real user interaction",
    "M2_M3": "real existing calculations/orchestration, authentic integrity-checked offline USDA snapshots",
    "M4": "real existing deterministic evidence-validation and recommendation rules",
    "network": "none; no live USDA validation, Ollama inference, authentication or databases",
}


class SimulatedVisionClient:
    """Declared hypotheses only. The synthetic image is deliberately not analyzed."""
    def __init__(self, hypotheses):
        self.content = json.dumps(hypotheses)
        self.calls = 0

    def analyze(self, image):
        self.calls += 1
        settings = VisionRuntimeSettings()
        provenance = VisionModelProvenance(model_tag=settings.model, model_digest="sha256:"+"0"*64,
                      ollama_version="0.0.0", prompt_version="vision-food-v1",
                      inference=settings.inference_configuration(), declared_at=datetime.now(timezone.utc).isoformat())
        return VisionInferenceReply(self.content, provenance)


class ScriptedMealClient:
    """Finite fixtures keyed by explicit USER text, not generated image captions."""
    def __init__(self, scripts):
        self.scripts, self.calls = scripts, []

    def chat(self, messages, schema):
        text = json.loads(messages[1]["content"])["meal_description"]
        self.calls.append(text)
        if text not in self.scripts:
            raise OllamaResponseError("No scripted extraction exists for this demo input.")
        return json.dumps({"foods": self.scripts[text]})


def raw_food(name, source, quantity=None, unit=None, preparation=None):
    return {"name": name, "source_text": source, "quantity_text": quantity,
            "unit": unit, "preparation": preparation}


def make_offline_workflow(scripts, hypotheses, *, provider=None, clock=time.time,
                          orchestration_settings=None, workflow_settings=None):
    vision = SimulatedVisionClient(hypotheses)
    extraction = ScriptedMealClient(scripts)
    source = provider if provider is not None else SnapshotProvider()
    def factory(mode, observer):
        if mode != "snapshot":
            raise ValueError("Offline demo requires snapshot mode")
        return source
    orchestrator = AgentOrchestrator(settings=orchestration_settings or OrchestrationSettings(), clock=clock,
                      food_factory=lambda observer: FoodUnderstandingAgent(Settings(validation_attempts=1), extraction),
                      provider_factory=factory)
    workflow = ImageNutritionWorkflow(vision_agent=ImageFoodRecognitionAgent(client=vision),
                                     orchestrator=orchestrator, settings=workflow_settings)
    return workflow, vision, extraction, source


def demo_confirmation(recognition, text):
    """A DEMO USER explicitly selects first alternatives present in their text.

    Not a production confirmation builder: never use this helper to auto-confirm
    arbitrary model output. Real callers must collect independent user choices.
    """
    decisions = []
    for group in recognition.groups:
        candidate = group.candidates[0]
        start = text.index(candidate.label)
        decisions.append({"group_id": group.group_id, "action": "accept_candidate",
                          "candidate_id": candidate.candidate_id,
                          "text_span": {"start": start, "end": start+len(candidate.label)}})
    return {"expected_result_id": recognition.result_id, "expected_revision": recognition.revision,
            "expected_image_sha256": recognition.image.original_sha256,
            "expected_result_sha256": recognition_fingerprint(recognition), "user_confirmed": True,
            "confirmed_meal_text": text, "acknowledged_question_ids": [q.question_id for q in recognition.questions],
            "decisions": decisions}


def run_example(scenario, image_path):
    if scenario == "complete":
        text = "banana and eggs"
        foods = [raw_food("banana", "banana"), raw_food("egg", "eggs")]
        labels = [["banana", "plantain"], ["eggs"]]
        actions = [(0, {"kind": "quantity", "quantity": "100", "unit": "g"}),
                   (1, {"kind": "preparation", "preparation": "boiled"}),
                   (1, {"kind": "quantity", "quantity": "100", "unit": "g"})]
    elif scenario == "partial":
        text = "100 g banana and paneer curry"
        foods = [raw_food("banana", "100 g banana", "100", "g"), raw_food("paneer curry", "paneer curry")]
        labels = [["banana"], ["paneer curry", "tofu curry"]]
        actions = [(1, {"kind": "leave_unresolved"})]
    else:
        raise ValueError("Unknown offline scenario")
    hypotheses = {"status": "uncertain", "groups": [{"location": "unknown", "labels": names,
                  "uncertainty_reasons": ["ambiguous_identity"]} for names in labels],
                  "uncertainty_reasons": ["ambiguous_identity"]}
    workflow, vision, extraction, _ = make_offline_workflow({text: foods}, hypotheses)
    owner = "offline-demo-owner"  # A local test context, NOT authenticated login.
    state = workflow.begin(image_path, owner=owner)
    transitions = [{"phase": state.phase, "session": None}]
    def note(snapshot):
        transitions.append({"phase": snapshot.phase, "status": snapshot.session.status,
                            "revision": snapshot.session.revision,
                            "nutrition_status": snapshot.session.nutrition.status if snapshot.session.nutrition else None,
                            "questions": [q.reason for q in snapshot.session.questions]})
    state = workflow.confirm(state.workflow_id, demo_confirmation(state.recognition, text), owner=owner)
    note(state)
    for number, (index, action) in enumerate(actions, 1):
        question = next(q for q in state.session.questions if q.item_index == index)
        state = workflow.respond(state.workflow_id, {"expected_revision": state.session.revision,
                 "request_id": f"demo-reply-{number}", "question_id": question.question_id,
                 "item_id": question.item_id, "action": action}, owner=owner)
        note(state)
    state = workflow.recommend(state.workflow_id, expected_revision=state.session.revision, owner=owner)
    report = {"scenario": scenario, "disclosure": DISCLOSURE, "transitions": transitions,
              "vision_calls": vision.calls, "extraction_inputs": extraction.calls,
              "snapshot": state.model_dump(mode="json")}
    workflow.close(state.workflow_id, owner=owner)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["complete", "partial", "all"], default="all")
    args = parser.parse_args(argv)
    # Generated data stays in this module's ignored test-temp namespace.
    root = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix=".test-tmp-m55-demo-", dir=root) as temporary:
        directory = Path(temporary).resolve()
        if directory.parent != root or not directory.name.startswith(".test-tmp-m55-demo-"):
            raise RuntimeError("Unexpected demo directory")
        from PIL import Image
        image_path = directory / "synthetic.png"
        with Image.new("RGBA", (24, 16), (30, 90, 140, 200)) as image:
            image.save(image_path, format="PNG")
        for scenario in (["complete", "partial"] if args.scenario == "all" else [args.scenario]):
            print(json.dumps(run_example(scenario, image_path), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
