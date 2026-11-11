"""Build lossless facts and citations from validated copies, not model guesses."""
from agentic_ai.schemas.nutrition import NUTRIENTS, NutrientCoverage
from agentic_ai.schemas.recommendation import NutritionFact, SourceCitation


def extract_evidence(nutrition):
    if nutrition is None:
        return (), ()
    facts, citations = [], []
    for item in nutrition.items:
        if item.record:
            record = item.record
            citations.append(SourceCitation(
                id=f"source-{item.item_index}", item_index=item.item_index,
                provenance=record.provenance.model_copy(deep=True),
                basis_grams=record.basis_grams, basis_description=record.basis_description,
                source_nutrients=record.nutrients.model_copy(deep=True), source_issues=tuple(record.issues),
                nutrient_evidence={k:v.model_copy(deep=True) for k,v in record.nutrient_evidence.items()},
                portion=item.portion.model_copy(deep=True) if item.portion else None,
                scale_factor=item.scale_factor,
                attribution="delegated_backend_record" if record.provenance.provider == "backend_usda" else "supplied_usda_record",
            ))
    for name in NUTRIENTS:
        coverage = nutrition.coverage[name].model_copy(deep=True)
        amount = getattr(nutrition.complete_totals if coverage.complete else nutrition.known_subtotals, name)
        basis = "unknown" if amount is None else "complete_total" if coverage.complete else "known_subtotal"
        facts.append(NutritionFact(id=f"meal-{name}", nutrient=name, amount=amount,
            unit="kcal" if name == "calories" else "g", basis=basis, coverage=coverage,
            source_refs=tuple(f"source-{item.item_index}" for item in nutrition.items if getattr(item.nutrition,name) is not None)))
    for item in nutrition.items:
        for name in NUTRIENTS:
            amount = getattr(item.nutrition,name)
            facts.append(NutritionFact(id=f"item-{item.item_index}-{name}", item_index=item.item_index,
                nutrient=name, amount=amount, unit="kcal" if name == "calories" else "g",
                basis="item" if amount is not None else "unknown",
                coverage=NutrientCoverage(known_items=int(amount is not None),total_items=1,complete=amount is not None),
                source_refs=(f"source-{item.item_index}",) if item.record else ()))
    return tuple(facts), tuple(citations)
