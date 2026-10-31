"""Resolve only measured mass or compatible, explicitly documented portions."""

from decimal import Decimal, DecimalException, localcontext

from agentic_ai.nutrition_errors import NutritionInputError

from agentic_ai.schemas.nutrition import PortionResolution
from agentic_ai.tools.usda_normalization import portion_qualifiers


def resolve_portion(food, record, selection=None, *, exact_quantity=None):
    try:
        with localcontext() as context:
            context.prec = 40
            return _resolve_portion(food, record, selection, exact_quantity=exact_quantity)
    except DecimalException:
        raise NutritionInputError("The source portion exceeds supported numeric precision; no weight was guessed.") from None


def _resolve_portion(food, record, selection=None, *, exact_quantity=None):
    """Return resolution, available compatible portions, and an issue code."""
    if selection and selection.measured_grams is not None:
        return PortionResolution(requested_grams=selection.measured_grams, method="user_measured", evidence="User-supplied total edible grams for this item; not a USDA weight measurement."), [], None
    if food.quantity is None:
        return None, record.portions, "missing_quantity"
    quantity = Decimal(exact_quantity) if exact_quantity is not None else Decimal(str(food.quantity))
    if quantity <= 0 or not quantity.is_finite():
        return None, [], "invalid_quantity"
    if food.unit in {"g", "kg"}:
        if selection and selection.portion_id:
            return None, [], "incompatible_portion_selection"
        grams = quantity * (Decimal(1000) if food.unit == "kg" else Decimal(1))
        return PortionResolution(requested_grams=grams, method="mass", evidence="Explicit edible mass; 1 kg = 1000 g. No raw/cooked yield conversion applied."), [], None
    if food.unit is None:
        return None, record.portions, "missing_unit"
    unit = food.unit
    if unit == "l":
        unit, quantity = "ml", quantity * 1000
    source_qualifiers = set(portion_qualifiers(food.source_text))
    choices = []
    for portion in record.portions:
        portion_unit = portion.unit
        if portion_unit == "l":
            portion_unit = "ml"
        if portion_unit != unit:
            continue
        if selection and selection.portion_id:
            if portion.portion_id != selection.portion_id:
                continue
            # Explicit selection may supply a missing size/form, never contradict it.
            if source_qualifiers - set(portion.qualifiers):
                continue
        elif set(portion.qualifiers) != source_qualifiers:
            continue
        choices.append(portion)
    if selection and selection.portion_id and len(choices) != 1:
        return None, record.portions, "incompatible_portion_selection"
    if len(choices) != 1:
        return None, record.portions, "ambiguous_portion" if record.portions else "unsupported_portion"
    chosen = choices[0]
    amount = chosen.amount * (1000 if chosen.unit == "l" else 1)
    grams = quantity * chosen.gram_weight / amount
    return PortionResolution(requested_grams=grams, method="usda_portion", evidence=f"USDA FDC {record.provenance.fdc_id}, portion {chosen.portion_id}: {chosen.amount} {chosen.unit} = {chosen.gram_weight} g; requested quantity multiplied by gramWeight / amount.", portion=chosen), choices, None
