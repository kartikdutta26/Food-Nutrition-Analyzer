from decimal import Decimal

import pytest

from agentic_ai.nutrition_errors import USDAResponseError
from agentic_ai.tools.usda_normalization import normalize_usda_food


def normalize(raw):
    return normalize_usda_food(raw, provider="usda_snapshot", retrieved_at="2026-10-31T00:00:00Z")


def test_authentic_rice_record_has_explicit_basis_and_source(raw_usda):
    record = normalize(raw_usda())
    assert record.provenance.fdc_id == 168878
    assert record.basis_grams == 100
    assert record.nutrients.calories == 130
    assert record.nutrients.protein == Decimal("2.69")
    assert record.nutrients.fiber == Decimal("0.4")
    assert record.portions[0].gram_weight == 158
    assert record.portions[0].amount == 1
    assert record.portions[0].unit == "cup"


def test_source_zero_is_not_missing(raw_usda):
    assert normalize(raw_usda(173424)).nutrients.fiber == 0


def test_missing_fiber_remains_none(raw_usda):
    raw = raw_usda()
    raw["foodNutrients"] = [n for n in raw["foodNutrients"] if n["nutrient"]["id"] != 1079]
    assert normalize(raw).nutrients.fiber is None


@pytest.mark.parametrize("bad", [-1, True, "NaN", "Infinity", "not a number", None])
def test_invalid_amounts_are_unknown(raw_usda, bad):
    raw = raw_usda()
    for n in raw["foodNutrients"]:
        if n["nutrient"]["id"] == 1003:
            n["amount"] = bad
    record = normalize(raw)
    assert record.nutrients.protein is None
    assert "protein:invalid_amount_or_unit" in record.issues


@pytest.mark.parametrize("unit", ["IU", "mystery", "", "kcal"])
def test_macro_units_must_be_supported(raw_usda, unit):
    raw = raw_usda()
    for n in raw["foodNutrients"]:
        if n["nutrient"]["id"] == 1003:
            n["nutrient"]["unitName"] = unit
    assert normalize(raw).nutrients.protein is None


def test_mg_converts_to_grams(raw_usda):
    raw = raw_usda()
    for n in raw["foodNutrients"]:
        if n["nutrient"]["id"] == 1003:
            n["nutrient"]["unitName"] = "mg"
            n["amount"] = 2690
    assert normalize(raw).nutrients.protein == Decimal("2.690")


def test_energy_precedence_does_not_add_duplicate_energy_fields(raw_usda):
    raw = raw_usda()
    raw["foodNutrients"] += [
        {"nutrient": {"id": 2047, "unitName": "kcal"}, "amount": 131},
        {"nutrient": {"id": 2048, "unitName": "kcal"}, "amount": 129},
    ]
    record = normalize(raw)
    assert record.nutrients.calories == 129
    assert record.nutrient_evidence["calories"].nutrient_id == 2048


def test_kilojoules_convert_explicitly(raw_usda):
    raw = raw_usda()
    for n in raw["foodNutrients"]:
        if n["nutrient"]["id"] == 1008:
            n["nutrient"]["unitName"] = "kJ"
            n["amount"] = Decimal("418.4")
    assert normalize(raw).nutrients.calories == pytest.approx(Decimal(100))


def test_conflicting_duplicate_nutrient_is_unknown(raw_usda):
    raw = raw_usda()
    raw["foodNutrients"].append({"nutrient":{"id":1003,"unitName":"g"},"amount":99})
    assert normalize(raw).nutrients.protein is None


def test_loq_zero_is_qualified_not_treated_as_precise_zero(raw_usda):
    raw = raw_usda()
    for n in raw["foodNutrients"]:
        if n["nutrient"]["id"] == 1003:
            n.update(amount=0, loq=Decimal("0.03"))
    record = normalize(raw)
    assert record.nutrients.protein is None
    assert "protein:below_quantification_limit" in record.issues


@pytest.mark.parametrize("change", [{"fdcId": True}, {"dataType":"Branded"}, {"foodNutrients":None}, {"description":""}])
def test_invalid_details_are_rejected(raw_usda, change):
    raw=raw_usda()
    raw.update(change)
    with pytest.raises(USDAResponseError):
        normalize(raw)


def test_response_id_must_match_requested_id(raw_usda):
    with pytest.raises(USDAResponseError):
        normalize_usda_food(raw_usda(), provider="usda_live", retrieved_at="now", expected_id=173424)


def test_fndds_portion_amount_is_read_from_actual_description(raw_usda):
    record=normalize(raw_usda(2707713))
    small=next(p for p in record.portions if p.portion_id=="299422")
    assert small.amount==1 and small.gram_weight==27 and small.unit=="piece"
    assert small.qualifiers==["small"]
    assert not any(p.description=="Quantity not specified" for p in record.portions)


def test_fluid_ounce_is_not_mass_ounce(raw_usda):
    record=normalize(raw_usda(171265))
    assert next(p for p in record.portions if p.description=="fl oz").unit=="fl_oz"
