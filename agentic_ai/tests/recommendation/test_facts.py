from decimal import Decimal
import pytest
from agentic_ai.schemas.nutrition import NUTRIENTS, Nutrients
from agentic_ai.schemas.recommendation import RecommendationResult
from agentic_ai.tools.nutrition_calculator import calculate, summarize

@pytest.mark.parametrize("index,status",[(0,"ready"),(1,"limited"),(2,"ready"),(3,"unavailable"),(4,"limited"),(5,"unavailable")])
def test_authentic_snapshot_examples(agent,examples,index,status):
    source=examples[index]
    output=agent.recommend(source)
    assert output.status==status
    assert output.complete_totals==source.complete_totals
    assert output.known_subtotals==source.known_subtotals
    assert output.coverage==source.coverage
    assert output.generation_mode=="deterministic"
    assert output.validation_scope=="supplied_record_consistency_only"
    assert RecommendationResult.model_validate_json(output.model_dump_json())==output
    for citation in output.citations:
        record=source.items[citation.item_index].record
        assert citation.provenance==record.provenance
        assert citation.nutrient_evidence==record.nutrient_evidence
        assert citation.source_nutrients==record.nutrients
    references={f.id for f in output.facts}|{c.id for c in output.citations}|{"input","context"}
    for entry in output.observations+output.suggestions+output.next_steps+output.limitations:
        assert entry.rule_id==entry.code
        assert set(entry.evidence_refs)<=references


def rebuild(source, nutrient=None, value=None, all_unknown=False):
    items=[]
    for item in source.items:
        item=item.model_copy(deep=True)
        names=NUTRIENTS if all_unknown else [nutrient] if nutrient else []
        for name in names:
            setattr(item.record.nutrients,name,value)
            if value is None:
                item.record.nutrient_evidence.pop(name,None)
            else:
                item.record.nutrient_evidence[name].source_amount=value
        item.nutrition,item.scale_factor=calculate(item.record,item.portion.requested_grams)
        item.status="complete" if all(getattr(item.nutrition,n) is not None for n in NUTRIENTS) else "incomplete_nutrients"
        items.append(item)
    return summarize(items)


def test_unknown_fiber_is_not_zero(agent,complete):
    source=rebuild(complete,"fiber",None)
    output=agent.recommend(source)
    assert output.status=="limited"
    fact=next(f for f in output.facts if f.id=="meal-fiber")
    assert fact.amount is None and fact.basis=="unknown"
    assert output.known_subtotals.fiber is None
    assert output.coverage["fiber"].known_items==0
    assert any(m.code=="unknown_fact" and m.evidence_refs==("meal-fiber",) for m in output.observations)


def test_true_zero_is_retained(agent,complete):
    source=rebuild(complete,"fiber",Decimal(0))
    output=agent.recommend(source)
    fact=next(f for f in output.facts if f.id=="meal-fiber")
    assert fact.amount==0 and fact.basis=="complete_total" and fact.coverage.complete


def test_all_unknown_is_unavailable(agent,complete):
    source=rebuild(complete,all_unknown=True)
    output=agent.recommend(source)
    assert output.status=="unavailable"
    assert all(f.amount is None for f in output.facts)
    assert not output.comparisons


def test_no_food_is_unavailable(agent):
    output=agent.recommend(summarize([]))
    assert output.status=="unavailable"
    assert all(f.amount is None for f in output.facts)
    assert any(m.code=="no_food" for m in output.limitations)


def test_partial_subtotal_never_becomes_total(agent,examples):
    output=agent.recommend(examples[4])
    assert output.complete_totals.calories is None
    assert output.known_subtotals.calories==Decimal("89")
    fact=next(f for f in output.facts if f.id=="meal-calories")
    assert fact.basis=="known_subtotal" and fact.coverage.known_items==1 and fact.coverage.total_items==2
    assert any(m.code=="subtotal_fact" for m in output.observations)


def test_sum_unrounded_source_contributions(agent,complete):
    # Synthetic precision fault fixture only, not a new USDA snapshot/value.
    base=complete.items[0].model_copy(deep=True)
    base.food.quantity=100
    base.food.quantity_text="100"
    base.record.nutrients.calories=Decimal("0.00004")
    base.record.nutrient_evidence["calories"].source_amount=Decimal("0.00004")
    items=[]
    for index in range(3):
        item=base.model_copy(deep=True)
        item.item_index=index
        item.nutrition,item.scale_factor=calculate(item.record,item.portion.requested_grams)
        items.append(item)
    source=summarize(items)
    assert source.complete_totals.calories==Decimal("0.0001")
    assert all(item.nutrition.calories==0 for item in source.items)
    assert agent.recommend(source).complete_totals.calories==Decimal("0.0001")


def test_input_and_returned_metadata_are_independent(agent,complete):
    before=complete.model_dump_json()
    first=agent.recommend(complete)
    first.citations[0].provenance.description="changed by caller"
    first.complete_totals.calories=Decimal(1)
    assert complete.model_dump_json()==before
    second=agent.recommend(complete)
    assert second.complete_totals.calories==complete.complete_totals.calories
    assert second.citations[0].provenance.description!="changed by caller"
