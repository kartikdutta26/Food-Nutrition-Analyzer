from decimal import Decimal

import pytest
from pydantic import ValidationError

from agentic_ai.adapters.backend_nutrition import normalize_backend_response
from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.nutrition_errors import NutritionInputError, USDAResponseError, USDATimeoutError
from agentic_ai.schemas.nutrition import ItemSelection, NUTRIENTS, Nutrients, SearchResults
from agentic_ai.tools.nutrition_calculator import calculate


def test_complete_two_food_meal(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="egg",quantity=100,preparation="boiled"),item()))
    assert result.status=="complete"
    assert result.complete_totals.calories==350
    assert result.complete_totals.protein==Decimal("16.6150")
    assert result.complete_totals.fiber==Decimal("0.6000")
    assert all(c.complete and c.known_items==2 for c in result.coverage.values())
    assert result.items[1].scale_factor==Decimal("1.5")
    assert result.items[1].record.basis_grams==100


def test_unresolved_item_leaves_complete_totals_unknown(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="banana",quantity=100,preparation=None),item(name="paneer curry",unit="bowl",preparation=None)))
    assert result.status=="partial"
    assert result.complete_totals.calories is None
    assert result.known_subtotals.calories==89
    assert result.coverage["calories"].known_items==1
    assert result.coverage["calories"].total_items==2
    assert result.resolved_items==1


def test_missing_one_nutrient_does_not_erase_other_complete_totals(snapshot,item,meal):
    class MissingFiber:
        def search(self,query): return snapshot.search(query)
        def get(self,fdc_id):
            record=snapshot.get(fdc_id)
            record.nutrients.fiber=None
            return record
    result=NutritionAnalysisAgent(MissingFiber()).analyze(meal(item(quantity=100)))
    assert result.status=="partial"
    assert result.complete_totals.calories==130
    assert result.complete_totals.fiber is None
    assert result.known_subtotals.fiber is None
    assert result.coverage["fiber"].known_items==0


def test_no_food_does_not_report_zero_consumption(snapshot,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal())
    assert result.status=="no_food" and result.total_items==0
    assert all(getattr(result.complete_totals,n) is None for n in NUTRIENTS)
    assert not result.coverage["calories"].complete


def test_truncated_search_is_not_treated_as_unique(snapshot,item,meal):
    class Truncated:
        def search(self,query):
            return SearchResults(candidates=snapshot.search(query).candidates,exhaustive=False,scope="test truncated search")
    result=NutritionAnalysisAgent(Truncated()).analyze(meal(item()))
    assert result.items[0].issues[0].code=="search_incomplete"
    assert result.items[0].record is None


def test_selected_id_must_match_preparation(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="egg",preparation="boiled")),[ItemSelection(item_index=0,fdc_id=173423)])
    assert result.items[0].issues[0].code=="incompatible_food_selection"
    assert result.complete_totals.calories is None


def test_selected_id_resolves_ambiguous_apple(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="apple",quantity=100,preparation=None)),[ItemSelection(item_index=0,fdc_id=171688)])
    assert result.complete_totals.calories==52
    assert result.items[0].record.provenance.fdc_id==171688


def test_repeated_foods_get_separate_selections(snapshot,item,meal):
    foods=meal(item(name="apple",quantity=100,preparation=None),item(name="apple",quantity=100,preparation=None))
    result=NutritionAnalysisAgent(snapshot).analyze(foods,[ItemSelection(item_index=0,fdc_id=171688),ItemSelection(item_index=1,fdc_id=171689)])
    assert result.complete_totals.calories==100
    assert [i.record.provenance.fdc_id for i in result.items]==[171688,171689]


@pytest.mark.parametrize("selections",[[{"item_index":9,"fdc_id":168878}],[{"item_index":0,"fdc_id":168878},{"item_index":0,"fdc_id":168878}]])
def test_invalid_selection_indices_are_rejected(snapshot,item,meal,selections):
    with pytest.raises(NutritionInputError):
        NutritionAnalysisAgent(snapshot).analyze(meal(item()),selections)


@pytest.mark.parametrize("values",[{"item_index":0},{"item_index":0,"portion_id":"x"},{"item_index":0,"measured_grams":0},{"item_index":0,"measured_grams":"NaN"},{"item_index":0,"fdc_id":1,"portion_id":"x","measured_grams":10}])
def test_invalid_selections_are_rejected(values):
    with pytest.raises(ValidationError):
        ItemSelection(**values)


def test_provider_failure_is_explicit_and_never_becomes_zero(snapshot,item,meal):
    class Broken:
        def search(self,query): raise USDATimeoutError("USDA lookup timed out.")
    result=NutritionAnalysisAgent(Broken()).analyze(meal(item()))
    assert result.status=="error"
    assert result.items[0].issues[0].code=="usda_timeout"
    assert result.complete_totals.calories is None


def test_missing_quantity_can_be_resolved_with_explicit_total_weight(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(quantity=None,unit=None)),[ItemSelection(item_index=0,measured_grams=200)])
    assert result.complete_totals.calories==260
    assert result.items[0].portion.method=="user_measured"


def backend_payload():
    # Synthetic contract fixture, not a real USDA nutrient assertion.
    return {"data_source":"usda_food_data_central","fdc_id":168878,"name":"Rice, white, cooked","category":"SR Legacy","serving":{"description":"test serving","gram_weight":200},"nutrition":{"calories":260,"protein":5.38,"carbs":56.34,"fats":.56}}


def test_backend_serving_is_scaled_once_and_missing_fiber_stays_unknown():
    record=normalize_backend_response(backend_payload(),retrieved_at="2026-10-31")
    nutrition,factor=calculate(record,Decimal(100))
    assert record.basis_grams==200
    assert factor==Decimal("0.5")
    assert nutrition.calories==130 and nutrition.protein==Decimal("2.690")
    assert nutrition.fiber is None
    assert record.provenance.provider=="backend_usda"


@pytest.mark.parametrize("change",[{"data_source":"sample_preset"},{"data_source":"user_provided"},{"fdc_id":None},{"serving":None},{"serving":{"description":"x","gram_weight":0}}])
def test_backend_adapter_rejects_unverified_or_invalid_responses(change):
    payload=backend_payload()
    payload.update(change)
    with pytest.raises(USDAResponseError):
        normalize_backend_response(payload)


def test_decimal_precision_is_retained_until_meal_total(snapshot,item,meal):
    class Tiny:
        def search(self,query): return snapshot.search(query)
        def get(self,fdc_id):
            record=snapshot.get(fdc_id)
            record.nutrients.calories=Decimal("0.00004")
            return record
    result=NutritionAnalysisAgent(Tiny()).analyze(meal(item(quantity=100),item(quantity=100),item(quantity=100)))
    assert result.complete_totals.calories==Decimal("0.0001")
    assert result.items[0].nutrition.calories==0


@pytest.mark.parametrize("grams",[0,-1,True,"NaN","Infinity","not mass"])
def test_invalid_calculation_mass_is_a_clear_error(snapshot,grams):
    with pytest.raises(NutritionInputError): calculate(snapshot.get(168878),grams)
