from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from agentic_ai.adapters.vision_handoff import prepare_confirmation, to_m3_start_request, recognition_fingerprint
from agentic_ai.schemas.vision import ConfirmedImageMeal
from agentic_ai.schemas.orchestration import StartRequest
from agentic_ai.vision_errors import VisionContractError
from .test_contracts import questions, assign


def test_explicit_text_is_only_m3_input_and_provenance_stays_separate(result_data,confirm_data):
    before=deepcopy((result_data,confirm_data))
    handoff=prepare_confirmation(result_data,confirm_data)
    request=to_m3_start_request(handoff)
    assert isinstance(request,StartRequest)
    assert request.text=="100 g banana" and request.provider=="snapshot"
    assert set(request.model_dump())=={"text","provider"}
    assert handoff.description_origin=="explicit_user_confirmation"
    assert handoff.image_contents_verified is False
    assert handoff.recognition.groups[0].candidates[0].quantity is None
    assert handoff.recognition.image.original_sha256=="a"*64
    assert handoff.recognition.model_provenance.model_digest=="sha256:"+"c"*64
    assert (result_data,confirm_data)==before
    assert to_m3_start_request(handoff.model_dump_json()).text==request.text
    assert ConfirmedImageMeal.model_validate_json(handoff.model_dump_json())==handoff
    request.text="caller edited separate request"
    assert handoff.confirmation.confirmed_meal_text=="100 g banana"
    with pytest.raises(ValidationError):handoff.recognition.groups[0].candidates[0].label="changed"


def test_no_model_or_orchestration_invocation(result_data,confirm_data,monkeypatch):
    from agentic_ai.orchestration import AgentOrchestrator
    from agentic_ai.agents.food_agent import FoodUnderstandingAgent
    from agentic_ai.clients.ollama_client import OllamaClient
    from agentic_ai.providers.usda import SnapshotProvider
    def forbidden(*args,**kwargs):raise AssertionError("M5.1 may not execute existing tools")
    monkeypatch.setattr(AgentOrchestrator,"start",forbidden)
    monkeypatch.setattr(FoodUnderstandingAgent,"analyze",forbidden)
    monkeypatch.setattr(OllamaClient,"chat",forbidden)
    monkeypatch.setattr(SnapshotProvider,"get",forbidden)
    assert to_m3_start_request(prepare_confirmation(result_data,confirm_data)).text=="100 g banana"

@pytest.mark.parametrize("path,value",[
    (("user_confirmed",),False),(("user_confirmed",),1),(("user_confirmed",),"true"),
    (("confirmed_meal_text",),""),(("confirmed_meal_text",)," "),(("confirmed_meal_text",),"123"),
    (("confirmed_meal_text",),"banana\x00"),(("confirmed_meal_text",),"banana\u202e"),
    (("confirmed_meal_text",),"x"*4001),(("acknowledged_question_ids",),[]),
    (("acknowledged_question_ids",),["global-meal-description"]),
    (("decisions",),[]),(("decisions",0,"group_id"),"other-group"),
    (("decisions",0,"candidate_id"),"candidate-z"),(("decisions",0,"candidate_id"),None),
    (("decisions",0,"action"),"assume_default_amount"),
    (("decisions",0,"corrected_label"),"rice"),(("decisions",0,"text_span","start"),True),
    (("decisions",0,"text_span","end"),99),(("decisions",0,"text_span","start"),12),
    (("decisions",0,"text_span"),None),(("confirmed_meal_text",),"100 g pineapple"),
    (("confirmed_meal_text",),"100 g bananas"),
])
def test_invalid_or_inconsistent_confirmation(result_data,confirm_data,path,value):
    assign(confirm_data,path,value)
    with pytest.raises(VisionContractError):prepare_confirmation(result_data,confirm_data)

@pytest.mark.parametrize("field,value",[("expected_result_id","recognition-other"),("expected_revision",2),("expected_image_sha256","d"*64),("expected_result_sha256","e"*64)])
def test_stale_confirmation_references(result_data,confirm_data,field,value):
    confirm_data[field]=value
    with pytest.raises(VisionContractError) as error:prepare_confirmation(result_data,confirm_data)
    assert error.value.code=="stale_result"


def test_changed_hypotheses_cannot_reuse_confirmation(result_data,confirm_data):
    result_data["groups"][0]["candidates"][0]["label"]="plantain"
    with pytest.raises(VisionContractError) as error:prepare_confirmation(result_data,confirm_data)
    assert error.value.code=="stale_result"


def test_explicit_correction_does_not_rewrite_original_hypothesis(result_data,confirm_data):
    confirm_data["confirmed_meal_text"]="150 g cooked rice"
    confirm_data["decisions"]=[{"group_id":"group-a","action":"correct_identity","corrected_label":"rice","text_span":{"start":0,"end":17}}]
    handoff=prepare_confirmation(result_data,confirm_data)
    assert handoff.recognition.groups[0].candidates[0].label=="banana"
    assert to_m3_start_request(handoff).text=="150 g cooked rice"


def test_excluded_food_is_not_inserted_in_description(result_data,confirm_data):
    confirm_data["decisions"]=[{"group_id":"group-a","action":"exclude_group"}]
    confirm_data["confirmed_meal_text"]="I ate nothing"
    handoff=prepare_confirmation(result_data,confirm_data)
    assert to_m3_start_request(handoff).text=="I ate nothing"
    assert handoff.recognition.groups[0].candidates[0].label=="banana"


def test_user_can_supply_text_after_model_no_food_without_fake_detection(result_data,confirm_data):
    result_data.update(status="no_food_detected",groups=[],uncertainty_reasons=["no_food_identified"]);questions(result_data)
    confirm_data.update(expected_result_sha256=recognition_fingerprint(result_data),decisions=[],acknowledged_question_ids=[q["question_id"] for q in result_data["questions"]])
    handoff=prepare_confirmation(result_data,confirm_data)
    assert handoff.recognition.status=="no_food_detected" and not handoff.recognition.groups
    assert to_m3_start_request(handoff).text=="100 g banana"


def test_missing_quantity_is_never_filled_in(result_data,confirm_data):
    confirm_data["confirmed_meal_text"]="banana"
    confirm_data["decisions"][0]["text_span"]={"start":0,"end":6}
    assert to_m3_start_request(prepare_confirmation(result_data,confirm_data)).text=="banana"


def test_multiple_groups_require_nonoverlapping_confirmed_spans(result_data,confirm_data):
    other=deepcopy(result_data["groups"][0]);other["group_id"]="group-b";other["candidates"][0]["candidate_id"]="candidate-b"
    result_data["groups"].append(other);result_data["uncertainty_reasons"].append("multiple_foods");questions(result_data)
    confirm_data.update(expected_result_sha256=recognition_fingerprint(result_data),acknowledged_question_ids=[q["question_id"] for q in result_data["questions"]],confirmed_meal_text="banana and banana")
    confirm_data["decisions"]=[{"group_id":"group-a","action":"accept_candidate","candidate_id":"candidate-a","text_span":{"start":0,"end":6}},
        {"group_id":"group-b","action":"accept_candidate","candidate_id":"candidate-b","text_span":{"start":11,"end":17}}]
    assert to_m3_start_request(prepare_confirmation(result_data,confirm_data)).text=="banana and banana"
    confirm_data["decisions"][1]["text_span"]={"start":0,"end":6}
    with pytest.raises(VisionContractError) as error:prepare_confirmation(result_data,confirm_data)
    assert error.value.code=="confirmation_mismatch"


def test_duplicate_acknowledgements_and_decisions_rejected(result_data,confirm_data):
    first=deepcopy(confirm_data);first["acknowledged_question_ids"]*=2
    second=deepcopy(confirm_data);second["decisions"]*=2
    for value in (first,second):
        with pytest.raises(VisionContractError):prepare_confirmation(result_data,value)


def test_alternative_is_not_an_additional_consumed_food(result_data,confirm_data):
    result_data["groups"][0]["candidates"].append({"candidate_id":"candidate-b","rank":2,"label":"plantain"})
    confirm_data["expected_result_sha256"]=recognition_fingerprint(result_data)
    confirm_data["decisions"][0].update(candidate_id="candidate-b",text_span={"start":0,"end":8})
    confirm_data["confirmed_meal_text"]="plantain"
    handoff=prepare_confirmation(result_data,confirm_data)
    assert to_m3_start_request(handoff).text=="plantain"
    assert len(handoff.recognition.groups[0].candidates)==2

@pytest.mark.parametrize("provider",["snapshot","live"])
def test_provider_is_explicit_caller_choice_only(result_data,confirm_data,provider):
    handoff=prepare_confirmation(result_data,confirm_data)
    assert to_m3_start_request(handoff,provider=provider).provider==provider

@pytest.mark.parametrize("provider",[None,"cloud",False,{"user_id":"attacker"}])
def test_invalid_provider_cannot_reach_m3(result_data,confirm_data,provider):
    with pytest.raises(VisionContractError):to_m3_start_request(prepare_confirmation(result_data,confirm_data),provider=provider)


def test_tampered_serialized_or_constructed_handoff_is_revalidated(result_data,confirm_data):
    handoff=prepare_confirmation(result_data,confirm_data)
    raw=handoff.model_dump(mode="json");raw["recognition"]["groups"][0]["candidates"][0]["label"]="rice"
    with pytest.raises(VisionContractError):to_m3_start_request(raw)
    object.__setattr__(handoff.confirmation,"user_confirmed",False)
    with pytest.raises(VisionContractError):to_m3_start_request(handoff)


def test_unchanged_m3_and_m4_accept_explicit_request_object(result_data,confirm_data):
    # Scripted M1 transport only; M2 uses authentic existing USDA snapshot values.
    # No vision model or image has been executed in this contract test.
    from agentic_ai.orchestration_demo import scripted_orchestrator, raw_food
    from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent
    service=scripted_orchestrator([raw_food("banana","100 g banana","100","g")])
    handoff=prepare_confirmation(result_data,confirm_data)
    request=to_m3_start_request(handoff)
    state=service.start(request,owner="explicit-test-owner")
    assert state.extraction.foods[0].source_text==confirm_data["confirmed_meal_text"]
    assert state.nutrition.complete_totals.calories==89
    assert state.nutrition.items[0].record.provenance.fdc_id==173944
    assert NutritionRecommendationAgent().recommend_session(state,expected_revision=state.revision).status=="ready"
    assert handoff.recognition.groups[0].candidates[0].nutrition is None
