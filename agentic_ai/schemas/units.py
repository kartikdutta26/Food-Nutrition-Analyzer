"""Canonical extraction units. These labels never imply gram weights."""

import re
from typing import Literal


ServingUnit = Literal[
    "piece", "g", "kg", "ml", "l", "cup", "tbsp", "tsp", "bowl", "plate",
    "slice", "serving", "katori", "glass", "handful", "pinch", "oz", "lb",
    "packet", "scoop", "can", "bottle", "clove", "dash", "stick",
]


UNIT_ALIASES = {
    "ounces": "oz", "ounce": "oz", "pounds": "lb", "pound": "lb",
    "grams": "g", "gram": "g", "kilograms": "kg", "kilogram": "kg",
    "milliliters": "ml", "millilitres": "ml", "milliliter": "ml", "millilitre": "ml",
    "liters": "l", "litres": "l", "liter": "l", "litre": "l",
    "tablespoons": "tbsp", "tablespoon": "tbsp", "teaspoons": "tsp", "teaspoon": "tsp",
    "pieces": "piece", "count": "piece", "cups": "cup", "bowls": "bowl",
    "plates": "plate", "slices": "slice", "servings": "serving", "katoris": "katori",
    "glasses": "glass", "handfuls": "handful", "pinches": "pinch",
}


def unit_is_stated(unit: str, source_text: str) -> bool:
    """Match actual measurement words, including forms such as 250ml."""
    aliases = {unit, unit + "s"}
    aliases.update(alias for alias, canonical in UNIT_ALIASES.items() if canonical == unit)
    pattern = "|".join(re.escape(alias) for alias in aliases)
    return re.search(rf"(?<![a-z])(?:{pattern})(?![a-z])", source_text.casefold()) is not None


def counted_piece_unit(source_text: str, quantity_text: str | None, preparation: str | None) -> str | None:
    """Normalize explicit counts of common foods when the model leaves unit null.

    This does not recognize foods without a model, infer weight, or turn an
    unknown measure ('one dozen eggs') into a piece. Unlisted phrases stay unknown.
    """
    if quantity_text is None or not source_text.startswith(quantity_text):
        return None
    remainder = source_text[len(quantity_text):].strip().casefold().rstrip(".,;!")
    if preparation and remainder.startswith(preparation.casefold() + " "):
        remainder = remainder[len(preparation):].strip()
    modifiers = r"(?:(?:a|an|small|medium|large|masala|whole|multigrain|wheat)\s+)*"
    nouns = r"(?:eggs?|apples?|bananas?|oranges?|rotis?|chapatis?|dosas?|idlis?|pancakes?|sandwich(?:es)?|cookies?)"
    return "piece" if re.fullmatch(modifiers + nouns, remainder) else None
