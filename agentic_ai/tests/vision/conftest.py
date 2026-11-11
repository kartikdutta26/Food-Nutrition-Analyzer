"""Synthetic declared metadata only, never an image/model acceptance fixture."""
import socket
import pytest
from agentic_ai.schemas.vision import CandidateFoodGroup, required_confirmation_questions
from agentic_ai.adapters.vision_handoff import recognition_fingerprint

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args,**kwargs):raise AssertionError("M5.1 must not contact services")
    monkeypatch.setattr(socket.socket,"connect",blocked)

@pytest.fixture
def result_data():
    groups=(CandidateFoodGroup.model_validate_json('{"group_id":"group-a","candidates":[{"candidate_id":"candidate-a","rank":1,"label":"banana"}],"uncertainty_reasons":["identity_unconfirmed"]}'),)
    return {
        "schema_version":"1.0", "result_id":"recognition-a", "revision":1,"status":"needs_confirmation",
        "image":{"image_id":"photo-a","original_sha256":"a"*64,"media_type":"image/jpeg","byte_size":1000,"width":1200,"height":800},
        "preprocessing":{"processed_sha256":"b"*64,"media_type":"image/jpeg","width":1024,"height":683,"original_exif_orientation":1,"metadata_removed":True},
        "model_provenance":{"provider":"ollama_local","model_tag":"qwen3-vl:2b","model_digest":"sha256:"+"c"*64,
            "ollama_version":"0.40.16","prompt_version":"vision-food-v1","declared_at":"2026-11-11T12:00:00Z",
            "inference":{"temperature":0,"num_ctx":4096,"num_predict":1024}},
        "groups":[g.model_dump(mode="json") for g in groups],"uncertainty_reasons":["identity_unconfirmed"],
        "questions":[q.model_dump(mode="json") for q in required_confirmation_questions(groups,"needs_confirmation")],
    }

@pytest.fixture
def confirm_data(result_data):
    return {"schema_version":"1.0","expected_result_id":result_data["result_id"],"expected_revision":1,
        "expected_image_sha256":result_data["image"]["original_sha256"],"expected_result_sha256":recognition_fingerprint(result_data),
        "user_confirmed":True,"confirmed_meal_text":"100 g banana",
        "acknowledged_question_ids":[q["question_id"] for q in result_data["questions"]],
        "decisions":[{"group_id":"group-a","action":"accept_candidate","candidate_id":"candidate-a","text_span":{"start":0,"end":12}}]}
