from decimal import Decimal, localcontext
import json
from pathlib import Path
import pytest
from agentic_ai.tools.nutrition_calculator import calculate, summarize
from agentic_ai.schemas.nutrition import FoodCandidate
from agentic_ai.recommendation_errors import RecommendationError

@pytest.mark.parametrize("name,unit,factor",[("protein","mg",Decimal(1000)),("fiber","ug",Decimal(1000000))])
def test_documented_source_unit_conversion(agent,complete,name,unit,factor):
    items=[i.model_copy(deep=True) for i in complete.items]
    for item in items:
        item.record.nutrient_evidence[name].source_unit=unit
        item.record.nutrient_evidence[name].source_amount=getattr(item.record.nutrients,name)*factor
        item.nutrition,item.scale_factor=calculate(item.record,item.portion.requested_grams)
    assert agent.recommend(summarize(items)).complete_totals==complete.complete_totals


def test_kilojoule_source_arithmetic_matches_m2(agent,complete):
    # Synthetic conversion boundary; no fixture file or USDA amount is changed.
    items=[i.model_copy(deep=True) for i in complete.items]
    for item in items:
        evidence=item.record.nutrient_evidence["calories"]
        evidence.source_unit="kJ";evidence.nutrient_id=1062;evidence.source_amount=Decimal("418.4")
        with localcontext() as ctx:
            ctx.prec=28
            item.record.nutrients.calories=evidence.source_amount*(Decimal(1)/Decimal("4.184"))
        item.nutrition,item.scale_factor=calculate(item.record,item.portion.requested_grams)
    assert agent.recommend(summarize(items)).status=="ready"


def test_delegated_backend_record_has_explicit_trust_limit(agent,complete):
    from agentic_ai.adapters.backend_nutrition import normalize_backend_response
    item=complete.items[0].model_copy(deep=True)
    record=item.record
    payload={"data_source":"usda_food_data_central","fdc_id":record.provenance.fdc_id,
        "name":record.provenance.description,"category":record.provenance.data_type,
        "serving":{"description":"200 g reference","gram_weight":200},
        "nutrition":{name:str(getattr(record.nutrients,name)*2) for name in ("calories","protein","carbs","fats")}}
    item.record=normalize_backend_response(payload,retrieved_at="2026-11-11")
    item.candidates=[FoodCandidate(fdc_id=item.record.provenance.fdc_id,description=item.record.provenance.description,data_type=item.record.provenance.data_type)]
    item.nutrition,item.scale_factor=calculate(item.record,item.portion.requested_grams)
    item.status="incomplete_nutrients"
    output=agent.recommend(summarize([item]))
    assert output.status=="limited"
    assert output.complete_totals.fiber is None
    assert output.citations[0].attribution=="delegated_backend_record"
    assert output.citations[0].basis_grams==200
    assert any(m.code=="backend_attribution" for m in output.limitations)


def test_forged_usda_portion_is_rejected(agent,examples):
    source=examples[2].model_dump(mode="json")
    source["items"][0]["portion"]["portion"]["gram_weight"]="999"
    with pytest.raises(RecommendationError):agent.recommend(source)


def test_claimed_missing_value_with_nonmissing_evidence_rejected(agent,complete):
    raw=complete.model_dump(mode="json")
    raw["items"][0]["record"]["nutrients"]["fiber"]=None
    with pytest.raises(RecommendationError):agent.recommend(raw)

@pytest.mark.parametrize("mutation",["new_rule","duplicate","wrong_version","clinical_scope","extra_field"])
def test_catalog_cannot_add_unreviewed_claims(agent,complete,monkeypatch,mutation):
    import io
    catalog_path=Path(__file__).parents[2]/"data/recommendation_rules.json"
    catalog=json.loads(catalog_path.read_text())
    if mutation=="new_rule":catalog["rule_ids"].append("diagnose_diabetes")
    elif mutation=="duplicate":catalog["rule_ids"].append(catalog["rule_ids"][0])
    elif mutation=="wrong_version":catalog["ruleset_version"]="2.0"
    elif mutation=="clinical_scope":catalog["scope"]="medical_advice"
    else:catalog["advice"]="take supplements"
    original=Path.open
    def patched(path,*args,**kwargs):
        if path==catalog_path.resolve():return io.BytesIO(json.dumps(catalog).encode())
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"open",patched)
    with pytest.raises(RecommendationError) as error:agent.recommend(complete)
    assert error.value.code=="invalid_rules"
