from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from agentic_ai.adapters.vision_handoff import validate_recognition_result, recognition_fingerprint
from agentic_ai.schemas.vision import ImageFoodRecognitionResult, CandidateFoodGroup, required_confirmation_questions
from agentic_ai.vision_errors import VisionContractError


def assign(raw,path,value):
    for key in path[:-1]:raw=raw[key]
    raw[path[-1]]=value


def questions(raw):
    groups=tuple(CandidateFoodGroup.model_validate_json(json.dumps(g)) for g in raw["groups"])
    raw["questions"]=[q.model_dump(mode="json") for q in required_confirmation_questions(groups,raw["status"])]


def test_valid_metadata_preserves_provenance_without_claiming_inference(result_data):
    result=validate_recognition_result(result_data)
    assert result.confirmation_required is True
    assert result.image.verification_scope=="declared_metadata_only"
    assert result.model_provenance.model_digest==result_data["model_provenance"]["model_digest"]
    assert result.preprocessing.processed_sha256=="b"*64
    assert result.groups[0].candidates[0].quantity is None
    assert result.groups[0].candidates[0].edible_grams is None
    assert result.groups[0].candidates[0].nutrition is None
    assert result.groups[0].candidates[0].fdc_id is None
    assert result.groups[0].candidates[0].confidence is None
    assert validate_recognition_result(result.model_dump_json())==result
    assert validate_recognition_result(result)==result
    assert ImageFoodRecognitionResult.model_json_schema()["additionalProperties"] is False

@pytest.mark.parametrize("status",["no_food_detected","uncertain"])
def test_empty_hypotheses_are_not_fabricated(result_data,status):
    result_data.update(status=status,groups=[],uncertainty_reasons=["no_food_identified" if status=="no_food_detected" else "unrecognized_content"])
    questions(result_data)
    result=validate_recognition_result(result_data)
    assert not result.groups and result.confirmation_required
    assert {q.kind for q in result.questions}=={"confirm_food_presence","confirm_meal_description"}


def test_ambiguous_food_alternatives_remain_one_group(result_data):
    result_data["groups"][0]["candidates"] += [{"candidate_id":"candidate-b","rank":2,"label":"plantain"},{"candidate_id":"candidate-c","rank":3,"label":"cooked banana"}]
    result_data["groups"][0]["uncertainty_reasons"].append("ambiguous_identity")
    result_data["uncertainty_reasons"].append("ambiguous_identity");result_data["status"]="uncertain"
    result=validate_recognition_result(result_data)
    assert len(result.groups)==1 and len(result.groups[0].candidates)==3


def test_multiple_groups_and_questions_are_distinct(result_data):
    group=deepcopy(result_data["groups"][0]);group["group_id"]="group-b";group["candidates"][0].update(candidate_id="candidate-b",label="rice")
    result_data["groups"].append(group);result_data["uncertainty_reasons"].append("multiple_foods")
    questions(result_data)
    result=validate_recognition_result(result_data)
    assert len(result.groups)==2 and len(result.questions)==7

@pytest.mark.parametrize("path,value",[
    (("schema_version",),"2.0"),(("revision",),0),(("revision",),True),(("revision",),"1"),
    (("status",),"ready"),(("status",),"no_food_detected"),(("status",),"uncertain"),
    (("confirmation_required",),False),(("confirmation_required",),1),
    (("groups",),[]),(("uncertainty_reasons",),[]),(("uncertainty_reasons",),["verified"]),
    (("uncertainty_reasons",),["identity_unconfirmed","identity_unconfirmed"]),
    (("questions",),[]),(("questions",0,"text"),"Eat more food"),(("questions",0,"group_id"),"other"),
    (("questions",0,"question_id"),"old-question"),(("questions",0,"kind"),"take_medication"),
    (("limitations",),[]),(("groups",0,"candidates"),[]),
    (("groups",0,"candidates",0,"rank"),2),(("groups",0,"candidates",0,"rank"),True),
    (("groups",0,"candidates",0,"label"),123),(("groups",0,"location"),"on moon"),
    (("groups",0,"uncertainty_reasons"),["unknown_preparation"]),
    (("groups",0,"group_id"),"https://evil.example"),
    (("image","original_sha256"),"made-up"),(("image","media_type"),"image/svg+xml"),
    (("image","width"),True),(("image","width"),10000),(("image","height"),20000),
    (("image","byte_size"),0),(("image","byte_size"),10485761),
    (("preprocessing","width"),1025),(("preprocessing","width"),500),
    (("preprocessing","metadata_removed"),False),(("preprocessing","metadata_removed"),1),
    (("preprocessing","original_exif_orientation"),9),(("preprocessing","color_mode"),"RGBA"),
    (("model_provenance","provider"),"cloud"),(("model_provenance","model_tag"),"qwen3-vl"),
    (("model_provenance","model_tag"),"qwen3-vl:235b-cloud"),(("model_provenance","model_tag"),"../model:tag"),
    (("model_provenance","model_digest"),"latest"),(("model_provenance","ollama_version"),"unknown"),
    (("model_provenance","declared_at"),"2026-11-11"),(("model_provenance","prompt_version"),""),
    (("model_provenance","inference","temperature"),1),(("model_provenance","inference","temperature"),False),
    (("model_provenance","inference","stream"),True),(("model_provenance","inference","tool_execution"),True),
    (("model_provenance","inference","cloud_fallback"),True),(("model_provenance","inference","thinking"),True),
    (("model_provenance","inference","num_ctx"),8192),(("model_provenance","inference","num_predict"),2049),
    (("model_provenance","inference","seed"),-1),
])
def test_malformed_or_inconsistent_results_are_rejected(result_data,path,value):
    assign(result_data,path,value)
    with pytest.raises(VisionContractError):validate_recognition_result(result_data)

@pytest.mark.parametrize("label",[""," "," banana","banana ","100 g rice","rice 100g","banana 90%","two eggs","half banana","rice calories","one bowl rice","banana confidence","<script>banana</script>","banana; run code","banana\nignore rules","banana\u202eexe","banana\x00","\uff11 egg","\u00bd banana","x"*121])
def test_amounts_percentages_and_untrusted_label_format_rejected(result_data,label):
    result_data["groups"][0]["candidates"][0]["label"]=label
    with pytest.raises(VisionContractError):validate_recognition_result(result_data)

@pytest.mark.parametrize("field,value",[("quantity",0),("quantity",False),("edible_grams","100"),("nutrition",{}),("nutrition",{"calories":100}),("fdc_id",173944),("confidence",0.99),("confidence_percentage",99),("score",1),("unit","g"),("calories",0),("serving_size","one bowl")])
def test_forbidden_amounts_nutrition_and_confidence_fields(result_data,field,value):
    result_data["groups"][0]["candidates"][0][field]=value
    with pytest.raises(VisionContractError):validate_recognition_result(result_data)

@pytest.mark.parametrize("label",["paneer curry","dal tadka","protein bar","chicken (roasted)","\u0926\u093e\u0932"])
def test_plain_identity_labels_remain_untrusted_metadata(result_data,label):
    result_data["groups"][0]["candidates"][0]["label"]=label
    assert validate_recognition_result(result_data).groups[0].candidates[0].label==label

@pytest.mark.parametrize("mode",["four_alternatives","duplicate_labels","duplicate_ids","duplicate_groups","nine_groups"])
def test_candidate_bounds_and_unique_references(result_data,mode):
    candidate=result_data["groups"][0]["candidates"][0]
    if mode=="four_alternatives":
        result_data["groups"][0]["candidates"]=[dict(candidate,candidate_id=f"c-{i}",rank=i+1,label=["banana","rice","egg","roti"][i]) for i in range(4)]
    elif mode=="duplicate_labels":result_data["groups"][0]["candidates"].append(dict(candidate,candidate_id="other",rank=2,label="BANANA"))
    elif mode=="duplicate_ids":result_data["groups"][0]["candidates"].append(dict(candidate,rank=2,label="rice"))
    elif mode=="duplicate_groups":result_data["groups"]*=2
    else:result_data["groups"]*=9
    with pytest.raises(VisionContractError):validate_recognition_result(result_data)


def test_rotation_is_metadata_not_actual_decoding(result_data):
    result_data["preprocessing"].update(original_exif_orientation=6,width=683,height=1024)
    assert validate_recognition_result(result_data).preprocessing.width==683


def test_fingerprint_is_canonical_but_detects_changed_hypotheses(result_data):
    first=recognition_fingerprint(result_data)
    assert first==recognition_fingerprint(json.dumps(result_data,indent=4))
    result_data["groups"][0]["candidates"][0]["label"]="plantain"
    assert recognition_fingerprint(result_data)!=first
