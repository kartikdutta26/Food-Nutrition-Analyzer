"""Opt-in external API checks and actual Qwen3-to-snapshot acceptance tests."""

import json
import os

import pytest

from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.config import Settings
from agentic_ai.providers.usda import LiveUSDAProvider, SnapshotProvider


@pytest.fixture(scope="module")
def live_usda():
    return LiveUSDAProvider()


@pytest.mark.usda_live
@pytest.mark.skipif(os.getenv("NUTRIAI_RUN_USDA_LIVE")!="1",reason="Explicit opt-in required for live USDA calls")
@pytest.mark.parametrize("fdc_id",[168878,173424,2707713])
def test_actual_usda_details_match_saved_snapshot(live_usda,fdc_id):
    current=live_usda.get(fdc_id)
    saved=SnapshotProvider().get(fdc_id)
    print(json.dumps({"verification":"actual live USDA details","fdc_id":fdc_id,"provenance":current.provenance.model_dump(mode="json"),"nutrients":current.nutrients.model_dump(mode="json")}))
    assert current.provenance.provider=="usda_live"
    assert current.nutrients==saved.nutrients
    assert {p.portion_id:p for p in current.portions}=={p.portion_id:p for p in saved.portions}
    assert current.basis_grams==100


@pytest.mark.usda_live
@pytest.mark.skipif(os.getenv("NUTRIAI_RUN_USDA_LIVE")!="1",reason="Explicit opt-in required for live USDA calls")
def test_actual_usda_search_returns_traceable_candidates(live_usda):
    found=live_usda.search("egg whole cooked hard boiled")
    print(found.model_dump_json())
    assert found.candidates and all(candidate.fdc_id>0 for candidate in found.candidates)


@pytest.mark.nutrition_integration
@pytest.mark.skipif(os.getenv("NUTRIAI_RUN_NUTRITION_LIVE")!="1",reason="Explicit opt-in required for actual local Qwen3")
@pytest.mark.parametrize(("text","status","calories","subtotal"),[
    ("I ate 100 g boiled eggs and 150 g cooked white rice.","complete","350.0000","350.0000"),
    ("I ate 2 small rotis and 1/2 cup cooked white rice.","complete","264.1600","264.1600"),
    ("I ate 100 g bananas and one bowl of paneer curry.","partial",None,"89.0000"),
    ("I ate 100 g apples.","needs_clarification",None,None),
])
def test_actual_qwen_to_snapshot_workflow(text,status,calories,subtotal):
    extraction=FoodUnderstandingAgent(Settings()).analyze(text)
    result=NutritionAnalysisAgent(SnapshotProvider()).analyze(extraction)
    print(json.dumps({"verification":"actual Qwen3 + offline USDA snapshot; no live nutrition API","input":text,"extraction":extraction.model_dump(mode="json"),"nutrition":result.model_dump(mode="json")}))
    assert result.status==status
    assert result.complete_totals.model_dump(mode="json")["calories"]==calories
    assert result.known_subtotals.model_dump(mode="json")["calories"]==subtotal
