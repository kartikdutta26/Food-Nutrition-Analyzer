"""Convert explicit quantities, without guessing grams or ambiguous amounts."""

import math
import re
from fractions import Fraction

from agentic_ai.schemas.units import UNIT_ALIASES


SMALL_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
FRACTIONS = {
    "¼": "1/4", "½": "1/2", "¾": "3/4", "⅓": "1/3", "⅔": "2/3",
    "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8",
}


def _whole_words(value: str) -> float | None:
    if value in {"a", "an"}:
        return 1.0
    if value in SMALL_NUMBERS:
        return float(SMALL_NUMBERS[value])
    words = value.split()
    if (
        len(words) == 2 and words[0] in SMALL_NUMBERS
        and SMALL_NUMBERS[words[0]] >= 20 and words[1] in SMALL_NUMBERS
        and 0 < SMALL_NUMBERS[words[1]] < 10
    ):
        return float(SMALL_NUMBERS[words[0]] + SMALL_NUMBERS[words[1]])
    return None


def parse_quantity(text: str, unit: str | None = None) -> float | None:
    """Return an explicit number, or None for ranges/unsupported expressions.

    Zero/negative results are returned for the agent to flag as invalid.
    'Some' and 'a few' are never treated as measured amounts.
    """
    value = text.casefold().strip().replace("−", "-").replace("⁄", "/")
    # Models sometimes quote the complete measured amount ('half a cup').
    # Strip only a suffix matching the separately validated unit, never a food.
    if unit is not None:
        canonical = UNIT_ALIASES.get(unit, unit)
        aliases = {unit, canonical, canonical + "s"}
        aliases.update(key for key, target in UNIT_ALIASES.items() if target == canonical)
        suffix = "|".join(re.escape(item) for item in sorted(aliases, key=len, reverse=True))
        value = re.sub(rf"\s+(?:{suffix})$", "", value).strip()
    for glyph, fraction in FRACTIONS.items():
        value = value.replace(glyph, " " + fraction)
    value = re.sub(r"\s+", " ", value).strip()
    if re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", value):
        value = value.replace(",", "")
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", value):
        result = float(value)
        return result if math.isfinite(result) else None
    mixed = re.fullmatch(r"([+-]?\d+)\s+(\d+)\s*/\s*(\d+)", value)
    fraction = re.fullmatch(r"([+-]?\d+)\s*/\s*(\d+)", value)
    try:
        if mixed:
            whole, numerator, denominator = map(int, mixed.groups())
            sign = -1 if value.startswith("-") else 1
            return float(sign * (abs(whole) + Fraction(numerator, denominator)))
        if fraction:
            return float(Fraction(*map(int, fraction.groups())))
    except (ZeroDivisionError, OverflowError, ValueError):
        return None
    value = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", value)
    if " and " in value:
        whole, rest = value.split(" and ", 1)
        left, right = _whole_words(whole), parse_quantity(rest)
        if left is not None and right is not None and 0 < right < 1:
            return left + right
        return None
    if value in {"half", "a half", "half a", "half an", "one half"}:
        return 0.5
    if value in {"quarter", "a quarter", "one quarter"}:
        return 0.25
    parts = re.fullmatch(r"(.+) (halves|quarters|thirds)", value)
    if parts:
        numerator = _whole_words(parts[1])
        if numerator is not None:
            return numerator / {"halves": 2, "quarters": 4, "thirds": 3}[parts[2]]
    return _whole_words(value)
