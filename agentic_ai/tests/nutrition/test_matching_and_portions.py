from decimal import Decimal

import pytest

from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.schemas.nutrition import FoodCandidate, ItemSelection, Portion
from agentic_ai.tools.food_matching import compatible
from agentic_ai.tools.portion_calculator import resolve_portion


@pytest.mark.parametrize(("name","description","expected"), [
    ("banana","Bananas, raw",True), ("banana","Banana pepper, raw",False),
    ("banana","Bananas, dehydrated, or banana powder",False),
    ("apple","Apples, raw, pie filling",False),
    ("rice","Rice with chicken",False), ("chapati","Bread, chappatti or roti",True),
])
def test_identity_does_not_silently_match_different_foods(item,name,description,expected):
    food=item(name=name,preparation=None,source_text="100 g "+name)
    candidate=FoodCandidate(fdc_id=999001,description=description,data_type="SR Legacy")
    assert compatible(food,candidate) is expected


@pytest.mark.parametrize(("method","description"), [("boiled","Egg, cooked, fried"),("raw","Rice, cooked"),("cooked","Rice, raw"),("grilled","Chicken, roasted")])
def test_conflicting_preparations_are_rejected(item,method,description):
    name="egg" if "Egg" in description else "rice" if "Rice" in description else "chicken"
    assert not compatible(item(name=name,preparation=method,source_text=f"100 g {method} {name}"),FoodCandidate(fdc_id=999001,description=description,data_type="SR Legacy"))


def test_generic_apple_never_selects_skin_variant(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="apple",preparation=None)))
    assert result.status=="needs_clarification"
    assert {c.fdc_id for c in result.items[0].candidates}=={171688,171689}
    assert result.items[0].record is None


def test_explicit_skin_selects_compatible_record(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="apple",preparation="raw",source_text="100 g raw apples without skin",quantity=100)))
    assert result.items[0].record.provenance.fdc_id==171689
    assert result.complete_totals.calories==48


def test_generic_egg_does_not_choose_boiled_or_fried(snapshot,item,meal):
    result=NutritionAnalysisAgent(snapshot).analyze(meal(item(name="egg",preparation=None)))
    assert len(result.items[0].candidates)==2
    assert result.items[0].record is None


@pytest.mark.parametrize(("quantity","unit","grams"),[(150,"g",150),(.25,"kg",250)])
def test_mass_conversion_is_exact(snapshot,item,quantity,unit,grams):
    resolution,_,issue=resolve_portion(item(quantity=quantity,unit=unit),snapshot.get(168878))
    assert issue is None and resolution.requested_grams==grams


def test_half_cup_uses_food_specific_usda_weight(snapshot,item):
    food=item(quantity=.5,unit="cup",source_text="1/2 cup cooked white rice")
    resolution,_,issue=resolve_portion(food,snapshot.get(168878))
    assert issue is None and resolution.requested_grams==79
    assert resolution.portion.portion_id=="83928"


def test_multi_piece_portion_divides_by_source_amount(snapshot,item):
    record=snapshot.get(173424)
    # Synthetic portion mutation verifies arithmetic; not used in the snapshot/demo.
    record.portions=[Portion(portion_id="synthetic-two",amount=2,unit="piece",gram_weight=100,description="2 pieces")]
    resolution,_,_=resolve_portion(item(name="egg",quantity=3,unit="piece",preparation="boiled",source_text="3 boiled eggs"),record)
    assert resolution.requested_grams==150


def test_roti_size_uses_actual_fndds_portion(snapshot,item):
    resolution,_,issue=resolve_portion(item(name="roti",quantity=2,unit="piece",preparation=None,source_text="2 small rotis"),snapshot.get(2707713))
    assert issue is None and resolution.requested_grams==54


@pytest.mark.parametrize(("name","fdc_id","unit","source"),[
    ("banana",173944,"piece","1 banana"), ("roti",2707713,"piece","1 roti"),
    ("banana",173944,"cup","1 cup banana"), ("white rice",168878,"bowl","1 bowl cooked white rice"),
    ("white rice",168878,"katori","1 katori cooked white rice"),
    ("milk",171265,"ml","250 ml milk"), ("milk",171265,"l","1 l milk"),
    ("milk",171265,"oz","1 oz milk"),
])
def test_no_default_size_density_or_household_weight(snapshot,item,name,fdc_id,unit,source):
    resolution,_,issue=resolve_portion(item(name=name,quantity=1,unit=unit,preparation=None,source_text=source),snapshot.get(fdc_id))
    assert resolution is None and issue


def test_piece_size_and_form_must_agree_with_selected_portion(snapshot,item):
    food=item(name="banana",quantity=1,unit="piece",preparation=None,source_text="1 small banana")
    selection=ItemSelection(item_index=0,fdc_id=173944,portion_id="93515")
    assert resolve_portion(food,snapshot.get(173944),selection)[2]=="incompatible_portion_selection"


def test_explicit_portion_selection_resolves_missing_size(snapshot,item):
    food=item(name="banana",quantity=2,unit="piece",preparation=None,source_text="2 bananas")
    selection=ItemSelection(item_index=0,fdc_id=173944,portion_id="93515")
    resolution,_,issue=resolve_portion(food,snapshot.get(173944),selection)
    assert issue is None and resolution.requested_grams==236


def test_documented_ml_portion_can_convert_volume_without_assumed_density(snapshot,item):
    record=snapshot.get(171265)
    record.portions=[Portion(portion_id="synthetic-ml",amount=100,unit="ml",gram_weight=103,description="100 ml")]
    resolution,_,issue=resolve_portion(item(name="milk",quantity=.25,unit="l",preparation=None,source_text="0.25 l milk"),record)
    assert issue is None and resolution.requested_grams==Decimal("257.5")


def test_total_measured_grams_are_not_multiplied_by_count(snapshot,item):
    food=item(name="roti",quantity=2,unit="piece",preparation=None,source_text="2 rotis")
    selection=ItemSelection(item_index=0,measured_grams=70)
    resolution,_,_=resolve_portion(food,snapshot.get(2707713),selection)
    assert resolution.requested_grams==70 and resolution.method=="user_measured"


def test_original_text_fortification_is_preserved(snapshot,item,meal):
    food=item(name="whole milk",quantity=100,preparation=None,source_text="100 g whole milk with added vitamin D")
    result=NutritionAnalysisAgent(snapshot).analyze(meal(food))
    assert result.items[0].record.provenance.fdc_id==171265


def test_selected_milk_id_does_not_invent_ml_density(snapshot,item,meal):
    food=item(name="whole milk",quantity=250,unit="ml",preparation=None,source_text="250 ml whole milk")
    result=NutritionAnalysisAgent(snapshot).analyze(meal(food),[ItemSelection(item_index=0,fdc_id=171265)])
    assert result.status=="needs_clarification"
    assert result.items[0].record.provenance.fdc_id==171265
    assert result.items[0].portion is None


def test_corrupt_extreme_portion_is_reported_as_an_error(snapshot,item):
    from agentic_ai.nutrition_errors import NutritionInputError
    record=snapshot.get(168878)
    record.portions=[Portion(portion_id="synthetic-overflow",amount=1,unit="cup",gram_weight=Decimal("1e1000000"),description="1 cup")]
    with pytest.raises(NutritionInputError):
        resolve_portion(item(quantity=2,unit="cup",source_text="2 cups cooked rice"),record)
