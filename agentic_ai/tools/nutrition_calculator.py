"""Pure Decimal arithmetic, retaining unknowns and per-nutrient coverage."""

from decimal import Decimal, DecimalException, localcontext

from agentic_ai.nutrition_errors import NutritionInputError

from agentic_ai.schemas.nutrition import NUTRIENTS, Nutrients, NutrientCoverage, NutritionResult


def calculate(record, grams):
    try:
        if isinstance(grams, bool):
            raise ValueError("Boolean is not a mass")
        grams = Decimal(str(grams))
        if not grams.is_finite() or grams <= 0:
            raise ValueError("Mass must be positive and finite")
        with localcontext() as context:
            context.prec = 40
            factor = grams / record.basis_grams
            values = {name: getattr(record.nutrients, name) * factor if getattr(record.nutrients, name) is not None else None for name in NUTRIENTS}
            return Nutrients(**values), factor
    except (DecimalException, ValueError, TypeError):
        raise NutritionInputError("Portion calculation requires a positive finite mass within supported numeric precision.") from None


def summarize(items):
    try:
        with localcontext() as context:
            context.prec = 40
            return _summarize(items)
    except DecimalException:
        raise NutritionInputError("Nutrient totals exceed supported numeric precision.") from None


def _summarize(items):
    totals, subtotals, coverage = {}, {}, {}
    count = len(items)
    for name in NUTRIENTS:
        known = [getattr(item.nutrition, name) for item in items if getattr(item.nutrition, name) is not None]
        subtotal = sum(known, Decimal(0)) if known else None
        complete = bool(count and len(known) == count)
        subtotals[name] = subtotal.quantize(Decimal("0.0001")) if subtotal is not None else None
        totals[name] = subtotals[name] if complete else None
        coverage[name] = NutrientCoverage(known_items=len(known), total_items=count, complete=complete)
    if not items:
        status = "no_food"
    elif all(item.status == "complete" for item in items):
        status = "complete"
    elif any(getattr(item.nutrition, name) is not None for item in items for name in NUTRIENTS):
        status = "partial"
    elif all(item.status == "error" for item in items):
        status = "error"
    else:
        status = "needs_clarification"
    # Sum unrounded contributions first, then round each public item for display.
    for item in items:
        item.nutrition = Nutrients(**{name: getattr(item.nutrition, name).quantize(Decimal("0.0001")) if getattr(item.nutrition, name) is not None else None for name in NUTRIENTS})
    return NutritionResult(status=status, items=items, complete_totals=Nutrients(**totals), known_subtotals=Nutrients(**subtotals), coverage=coverage, total_items=count, resolved_items=sum(item.portion is not None for item in items), questions=[question for item in items for question in item.questions])
