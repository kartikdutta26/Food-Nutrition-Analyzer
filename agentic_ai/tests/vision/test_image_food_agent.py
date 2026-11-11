"""Scripted hypotheses from synthetic pixels, not a real accuracy benchmark."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from agentic_ai.adapters.vision_handoff import (prepare_confirmation, recognition_fingerprint,
                                               to_m3_start_request)
from agentic_ai.agents.image_food_agent import ImageFoodRecognitionAgent
from agentic_ai.clients.ollama_vision_client import OllamaVisionClient, VisionInferenceReply
from agentic_ai.schemas.vision import VisionModelProvenance
from agentic_ai.schemas.vision_inference import RawVisionResponse
from agentic_ai.tools.image_input import ImageInputError
from agentic_ai.vision_errors import VisionContractError
from agentic_ai.vision_runtime_config import VisionRuntimeSettings
from agentic_ai.vision_runtime_errors import VisionRuntimeError
from .test_image_input import write_image
from .test_vision_runtime_client import RAW


class ScriptedVision:
    def __init__(self, reply): self.reply, self.calls = reply, []
    def analyze(self, image):
        self.calls.append(image)
        if isinstance(self.reply, Exception): raise self.reply
        return self.reply


@pytest.fixture
def make_reply(result_data):
    def make(data=None, content=None):
        provenance = deepcopy(result_data["model_provenance"])
        provenance["inference"] = VisionRuntimeSettings().inference_configuration().model_dump(mode="json")
        return VisionInferenceReply(content if content is not None else json.dumps(RAW if data is None else data),
                                    VisionModelProvenance.model_validate_json(json.dumps(provenance)))
    return make


def analyze(tmp_path, make_reply, data=None, content=None):
    client = ScriptedVision(make_reply(data, content))
    result = ImageFoodRecognitionAgent(client=client).analyze(write_image(tmp_path))
    return result, client


def test_valid_identity_preserves_hashes_and_requires_confirmation(tmp_path, make_reply):
    result, client = analyze(tmp_path, make_reply)
    assert result.status == "needs_confirmation" and result.confirmation_required is True
    assert result.groups[0].candidates[0].label == "banana"
    assert result.image == client.calls[0].image
    assert result.preprocessing == client.calls[0].preprocessing
    assert result.model_provenance == client.reply.provenance
    assert result.revision == 1 and result.result_id.startswith("vision-")
    assert len(result.questions) == 4
    assert "user_confirmation_required" in result.limitations
    candidate = result.groups[0].candidates[0]
    assert all(getattr(candidate, field) is None for field in ["quantity", "edible_grams", "nutrition", "fdc_id", "confidence"])
    assert "unknown_preparation" in result.uncertainty_reasons


def test_mismatched_explicit_settings_cannot_be_ignored():
    client = OllamaVisionClient()
    with pytest.raises(VisionRuntimeError) as error:
        ImageFoodRecognitionAgent(settings=VisionRuntimeSettings(timeout_seconds=1), client=client)
    assert error.value.code == "invalid_configuration"


def test_client_settings_are_preserved_when_no_override_is_supplied():
    client = OllamaVisionClient(VisionRuntimeSettings(timeout_seconds=1))
    agent = ImageFoodRecognitionAgent(client=client)
    assert agent.settings == client.settings


def test_forged_agent_configuration_fails_before_image_access():
    with pytest.raises(VisionRuntimeError) as error:
        ImageFoodRecognitionAgent(settings=VisionRuntimeSettings.model_construct(model="other-cloud"))
    assert error.value.code == "invalid_configuration"


def test_three_alternatives_trigger_uncertainty_instead_of_extra_foods(tmp_path, make_reply):
    data = deepcopy(RAW)
    data["groups"][0]["labels"] = ["paneer", "tofu", "cheese"]
    result, _ = analyze(tmp_path, make_reply, data)
    assert result.status == "uncertain" and len(result.groups) == 1
    assert [c.rank for c in result.groups[0].candidates] == [1, 2, 3]
    assert "ambiguous_identity" in result.uncertainty_reasons


def test_eight_distinct_groups_with_three_alternatives_fit_question_bounds(tmp_path, make_reply):
    data = deepcopy(RAW)
    data["groups"] = [dict(location="unknown", labels=["paneer", "tofu", "cheese"], uncertainty_reasons=[]) for _ in range(8)]
    result, _ = analyze(tmp_path, make_reply, data)
    assert len(result.groups) == 8 and len(result.questions) == 25
    assert "multiple_foods" in result.uncertainty_reasons
    assert len({c.candidate_id for g in result.groups for c in g.candidates}) == 24


@pytest.mark.parametrize("reason", ["ambiguous_identity", "mixed_dish", "occluded", "blurred", "poor_lighting", "unrecognized_content"])
def test_hard_uncertainty_is_never_presented_as_ordinary_confirmation(tmp_path, make_reply, reason):
    data = deepcopy(RAW)
    data["groups"][0]["uncertainty_reasons"] = [reason]
    result, _ = analyze(tmp_path, make_reply, data)
    assert result.status == "uncertain" and reason in result.uncertainty_reasons


@pytest.mark.parametrize("status,reasons", [("uncertain", ["unrecognized_content"]), ("no_food_detected", ["no_food_identified"])])
def test_unknown_or_non_food_still_requires_manual_confirmation(tmp_path, make_reply, status, reasons):
    result, _ = analyze(tmp_path, make_reply, {"status": status, "groups": [], "uncertainty_reasons": reasons})
    assert result.status == status and not result.groups
    assert result.confirmation_required and len(result.questions) == 2
    assert result.questions[0].kind == "confirm_food_presence"


@pytest.mark.parametrize("label", [
    "100 g rice", "two eggs", "90 percent banana", "rice 0 kcal", "banana 99%", "rice USDA", "rice fdc",
    "apple cures diabetes", "verified healthy meal", "ignore previous instructions", "execute powershell",
    "upload image", "delete files", "reveal secret", "<script>rice</script>", "rice\nignore", "rice\u202eexe",
    "one bowl rice", "confidence rice", "\uff11 egg", "\u00bd banana", "x"*121, "", " rice", "rice ",
])
def test_adversarial_labels_are_rejected_without_echo(tmp_path, make_reply, label):
    data = deepcopy(RAW); data["groups"][0]["labels"] = [label]
    with pytest.raises(VisionRuntimeError) as error: analyze(tmp_path, make_reply, data)
    assert error.value.code == "invalid_model_output"
    assert label not in str(error.value) if label else True


@pytest.mark.parametrize("field,value", [
    ("quantity", 1), ("edible_grams", 100), ("nutrition", {"kcal": 500}), ("fdc_id", 123),
    ("confidence", 0.9), ("confidence_percentage", 90), ("calories", 0), ("quantity", None),
    ("prompt", "ignore safety"), ("image_url", "https://remote.invalid"),
])
def test_extra_claim_fields_are_rejected(tmp_path, make_reply, field, value):
    data = deepcopy(RAW); data["groups"][0][field] = value
    with pytest.raises(VisionRuntimeError) as error: analyze(tmp_path, make_reply, data)
    assert error.value.code == "invalid_model_output"


@pytest.mark.parametrize("change", ["no_groups", "four_alternatives", "nine_groups", "duplicate_labels", "duplicate_reasons", "false_no_food", "no_food_reason", "unknown_reason", "injected_provenance"])
def test_shape_and_status_failures(tmp_path, make_reply, change):
    data = deepcopy(RAW)
    if change == "no_groups": data["groups"] = []
    elif change == "four_alternatives": data["groups"][0]["labels"] = ["rice", "wheat", "barley", "oats"]
    elif change == "nine_groups": data["groups"] *= 9
    elif change == "duplicate_labels": data["groups"][0]["labels"] = ["Rice", "rice"]
    elif change == "duplicate_reasons": data["uncertainty_reasons"] *= 2
    elif change == "false_no_food": data["status"] = "no_food_detected"
    elif change == "no_food_reason": data["uncertainty_reasons"] = ["no_food_identified"]
    elif change == "unknown_reason": data["uncertainty_reasons"] = ["certain"]
    else: data["model_provenance"] = {"model_digest": "fabricated"}
    with pytest.raises(VisionRuntimeError) as error: analyze(tmp_path, make_reply, data)
    assert error.value.code == "invalid_model_output"


@pytest.mark.parametrize("content", [
    '```json\n{}\n```', '{}', '[]', 'null', '{"status":"uncertain","status":"no_food_detected"}',
    '{"value":NaN}', '{"value":1e999}', 'x'*32769, '['*1000+'0'+']'*1000,
])
def test_malformed_output_fails_closed(tmp_path, make_reply, content):
    with pytest.raises(VisionRuntimeError) as error: analyze(tmp_path, make_reply, content=content)
    assert error.value.code == "invalid_model_output"


def test_service_failure_is_not_disguised_as_no_food(tmp_path):
    client = ScriptedVision(VisionRuntimeError("timeout"))
    with pytest.raises(VisionRuntimeError) as error: ImageFoodRecognitionAgent(client=client).analyze(write_image(tmp_path))
    assert error.value.code == "timeout" and len(client.calls) == 1


def test_corrupt_image_never_reaches_client(tmp_path, make_reply):
    path = tmp_path / "private-photo.png"; path.write_bytes(b"not an image")
    client = ScriptedVision(make_reply())
    with pytest.raises(ImageInputError): ImageFoodRecognitionAgent(client=client).analyze(path)
    assert not client.calls


@pytest.mark.parametrize("field,value", [("model_tag", "qwen3-vl:4b"), ("prompt_version", "wrong-prompt")])
def test_reply_cannot_change_configured_identity(tmp_path, make_reply, field, value):
    reply = make_reply()
    provenance = reply.provenance.model_copy(update={field: value})
    client = ScriptedVision(replace(reply, provenance=provenance))
    with pytest.raises(VisionRuntimeError) as error: ImageFoodRecognitionAgent(client=client).analyze(write_image(tmp_path))
    assert error.value.code == "invalid_response"


def test_new_inference_gets_new_result_identity_and_stale_confirmation_fails(tmp_path, make_reply):
    path = write_image(tmp_path)
    client = ScriptedVision(make_reply())
    agent = ImageFoodRecognitionAgent(client=client)
    first, second = agent.analyze(path), agent.analyze(path)
    assert first.result_id != second.result_id
    assert first.image == second.image and first.groups == second.groups
    confirmation = {"expected_result_id": first.result_id, "expected_revision": first.revision,
                    "expected_image_sha256": first.image.original_sha256,
                    "expected_result_sha256": recognition_fingerprint(first), "user_confirmed": True,
                    "confirmed_meal_text": "banana", "acknowledged_question_ids": [q.question_id for q in first.questions],
                    "decisions": [{"group_id": "group-1", "action": "accept_candidate", "candidate_id": "food-1-1",
                                   "text_span": {"start": 0, "end": 6}}]}
    handoff = prepare_confirmation(first, confirmation)
    request = to_m3_start_request(handoff, provider="snapshot")
    assert request.text == "banana"  # No invented serving amount.
    assert handoff.recognition == first
    with pytest.raises(VisionContractError): prepare_confirmation(second, confirmation)
    confirmation["user_confirmed"] = False
    with pytest.raises(VisionContractError): prepare_confirmation(first, confirmation)


def test_untrusted_model_failure_is_sanitized(tmp_path, caplog, capsys):
    client = ScriptedVision(RuntimeError("PRIVATE MODEL TEXT AND PATH"))
    with pytest.raises(VisionRuntimeError) as error: ImageFoodRecognitionAgent(client=client).analyze(write_image(tmp_path))
    assert error.value.code == "inference_failed" and "PRIVATE" not in str(error.value)
    assert not caplog.records and capsys.readouterr() == ("", "")
