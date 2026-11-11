from copy import deepcopy
from decimal import Decimal
import pytest
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.recommendation_config import RecommendationSettings
from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent


def assign(raw,path,value):
    for part in path[:-1]:
        raw=raw[part]
    raw[path[-1]]=value

@pytest.mark.parametrize("path,value",[
    (("complete_totals","calories"),"1"),
    (("known_subtotals","fiber"),"123"),
    (("coverage","protein","known_items"),0),
    (("coverage","protein","complete"),False),
    (("total_items",),99),(("resolved_items",),0),(("status",),"partial"),
    (("items",0,"item_index"),2),(("items",0,"nutrition","calories"),"999"),
    (("items",0,"scale_factor"),"2"),
    (("items",0,"portion","requested_grams"),"101"),
    (("items",0,"portion","evidence"),"made up serving"),
    (("items",0,"record","nutrient_evidence","calories","source_unit"),"g"),
    (("items",0,"record","nutrient_evidence","protein","source_unit"),"kcal"),
    (("items",0,"record","nutrient_evidence","fiber","nutrient_id"),1003),
    (("items",0,"record","nutrient_evidence","protein","source_amount"),"999"),
    (("items",0,"record","nutrients","protein"),"999"),
    (("items",0,"record","provenance","source_url"),"javascript:alert(1)"),
    (("items",0,"record","provenance","fdc_id"),999),
    (("items",0,"record","provenance","snapshot_sha256"),"forged"),
    (("items",0,"record","provenance","retrieved_at"),"yesterday"),
    (("items",0,"record","basis_grams"),"200"),
    (("items",0,"food","quantity"),200),
    (("items",0,"record","nutrient_evidence","fiber"),None),
])
def test_inconsistent_evidence_rejected(agent,complete,path,value):
    raw=complete.model_dump(mode="json")
    assign(raw,path,value)
    with pytest.raises(RecommendationError):
        agent.recommend(raw)

@pytest.mark.parametrize("value",["NaN","Infinity","-Infinity",True,-1,"1e10000","1e-10000"])
def test_invalid_nutrient_numbers(agent,complete,value):
    raw=complete.model_dump(mode="json")
    raw["items"][0]["nutrition"]["calories"]=value
    with pytest.raises(RecommendationError):
        agent.recommend(raw)


def test_mutated_pydantic_model_is_revalidated(agent,complete):
    object.__setattr__(complete.items[0].nutrition,"calories",Decimal("NaN"))
    with pytest.raises(RecommendationError):
        agent.recommend(complete)

@pytest.mark.parametrize("payload",['{"source":{},"source":{}}','NaN','{"source":Infinity}',bytes([255])])
def test_invalid_json_rejected(agent,payload):
    with pytest.raises(RecommendationError):
        agent.recommend_request(payload)


def test_extra_contract_fields_rejected(agent,complete):
    with pytest.raises(RecommendationError):
        agent.recommend_request({"source":{"kind":"nutrition","result":complete.model_dump(mode="json")},"medical_diagnosis":"diabetes"})

@pytest.mark.parametrize("setting,value",[("max_input_bytes",1024),("max_nodes",100),("max_depth",4),("max_items",1)])
def test_input_limits(complete,setting,value):
    agent=NutritionRecommendationAgent(RecommendationSettings(**{setting:value}))
    with pytest.raises(RecommendationError) as error:
        agent.recommend(complete)
    assert error.value.code=="input_limit"

@pytest.mark.parametrize("setting,value",[("max_output_bytes",1024),("max_messages",1)])
def test_output_limits_are_safe_and_not_truncation(complete,setting,value):
    agent=NutritionRecommendationAgent(RecommendationSettings(**{setting:value}))
    with pytest.raises(RecommendationError) as error:
        agent.recommend(complete)
    assert error.value.code=="output_limit"


def test_oversized_and_recursive_inputs(agent):
    for value in [" "*4_194_305,{"source":"x"*4001},{"source":[None]*1001}]:
        with pytest.raises(RecommendationError):
            agent.recommend_request(value)
    raw={};raw["source"]=raw
    with pytest.raises(RecommendationError):
        agent.recommend_request(raw)


def test_no_provider_or_extraction_calls(agent,complete,monkeypatch):
    from agentic_ai.agents.food_agent import FoodUnderstandingAgent
    from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
    from agentic_ai.providers.usda import SnapshotProvider
    def forbidden(*args,**kwargs):
        raise AssertionError("M4 must not extract or fetch")
    monkeypatch.setattr(FoodUnderstandingAgent,"analyze",forbidden)
    monkeypatch.setattr(NutritionAnalysisAgent,"analyze",forbidden)
    monkeypatch.setattr(SnapshotProvider,"get",forbidden)
    monkeypatch.setattr(SnapshotProvider,"search",forbidden)
    assert agent.recommend(complete).status=="ready"


def test_consistently_changed_mass_still_requires_original_quantity_quote(agent,complete):
    from agentic_ai.tools.nutrition_calculator import calculate, summarize
    items=[i.model_copy(deep=True) for i in complete.items]
    item=items[0]
    item.food.quantity=200
    item.food.quantity_text="200"
    item.portion.requested_grams=Decimal(200)
    item.nutrition,item.scale_factor=calculate(item.record,Decimal(200))
    # Arithmetic alone agrees, but original M1 source text still says 100 g.
    with pytest.raises(RecommendationError) as error:
        agent.recommend(summarize(items))
    assert error.value.code=="invalid_evidence"
