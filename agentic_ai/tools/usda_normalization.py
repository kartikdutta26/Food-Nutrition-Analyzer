"""Normalize full USDA food details without using LLM values or nutrient names."""

import re
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from agentic_ai.nutrition_errors import USDAResponseError
from agentic_ai.schemas.nutrition import NutrientEvidence, Nutrients, NutritionRecord, Portion, Provenance

SUPPORTED_TYPES = {"Foundation", "SR Legacy", "Survey (FNDDS)"}
IDS = {"calories": (2048, 2047, 1008, 1062), "protein": (1003,), "carbs": (1005,), "fats": (1004,), "fiber": (1079,)}


def decimal_amount(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def portion_qualifiers(text):
    value = text.casefold()
    qualifiers = []
    size = re.search(r"\b(extra small|extra large|small|medium|large)\b", value)
    if size:
        qualifiers.append(size[0])
    for word, expression in {"sliced": r"\bslic(?:e|es|ed)\b", "chopped": r"\bchopped\b", "mashed": r"\bmashed\b", "quartered": r"\bquartered\b"}.items():
        if re.search(expression, value):
            qualifiers.append(word)
    return qualifiers


def _portions(raw, issues):
    result = []
    source = raw.get("foodPortions", [])
    if not isinstance(source, list):
        issues.append("invalid_food_portions")
        return result
    for index, portion in enumerate(source):
        if not isinstance(portion, dict):
            issues.append("invalid_portion")
            continue
        measure = portion.get("measureUnit")
        measure = measure if isinstance(measure, dict) else {}
        description = str(portion.get("portionDescription") or portion.get("modifier") or measure.get("name") or "").strip()
        if not description:
            issues.append("unlabeled_portion")
            continue
        amount = decimal_amount(portion.get("amount"))
        if amount is None:
            # FNDDS omits amount but may state it explicitly in the description.
            prefix = re.match(r"^(\d+(?:\.\d+)?)\s+", description)
            amount = decimal_amount(prefix[1]) if prefix else None
        weight = decimal_amount(portion.get("gramWeight"))
        if amount is None or weight is None or amount <= 0 or weight <= 0:
            issues.append("invalid_portion_amount_or_weight")
            continue
        text = " ".join([description, str(measure.get("name", ""))]).casefold()
        unit = None
        if re.search(r"\bfl\.?\s*oz\b|\bfluid ounce", text):
            unit = "fl_oz"  # Deliberately distinct from mass ounces.
        else:
            for canonical, pattern in [("ml", r"\b(?:ml|millilit(?:er|re)s?)\b"), ("l", r"\b(?:lit(?:er|re)s?)\b"), ("cup", r"\bcups?\b"), ("tbsp", r"\b(?:tbsp|tablespoons?)\b"), ("tsp", r"\b(?:tsp|teaspoons?)\b"), ("bowl", r"\bbowls?\b"), ("katori", r"\bkatoris?\b"), ("plate", r"\bplates?\b"), ("piece", r"\b(?:pieces?|whole|chappatti|chapati|roti|fruit|eggs?)\b"), ("slice", r"\bslices?\b"), ("serving", r"\bserving\b")]:
                if re.search(pattern, text):
                    unit = canonical
                    break
        qualifiers = portion_qualifiers(description)
        if unit is None and qualifiers and re.search(r"\b(?:Egg|Bananas|Apples)\b", raw["description"], re.I):
            unit = "piece"
        if "nlea" in text:
            qualifiers.append("nlea")
        result.append(Portion(portion_id=str(portion.get("id", f"index:{index}")), amount=amount, unit=unit, gram_weight=weight, description=description, qualifiers=qualifiers))
    return result


def normalize_usda_food(raw, *, provider, retrieved_at, snapshot_sha256=None, expected_id=None):
    try:
        if not isinstance(raw, dict) or isinstance(raw.get("fdcId"), bool) or not isinstance(raw.get("fdcId"), int):
            raise ValueError("Invalid food ID")
        if raw.get("dataType") not in SUPPORTED_TYPES:
            raise ValueError("Unsupported food data type")
        fdc_id = raw["fdcId"]
        if expected_id is not None and expected_id != fdc_id:
            raise ValueError("Response ID mismatch")
        provenance = Provenance(provider=provider, fdc_id=fdc_id, description=raw["description"], data_type=raw["dataType"], source_url=f"https://fdc.nal.usda.gov/food-details/{fdc_id}/nutrients", retrieved_at=retrieved_at, publication_date=raw.get("publicationDate"), snapshot_sha256=snapshot_sha256)
        entries = raw.get("foodNutrients")
        if not isinstance(entries, list):
            raise ValueError("Missing nutrient list")
        values, evidence, issues = {}, {}, []
        for name, identifiers in IDS.items():
            values[name] = None
            for identifier in identifiers:
                candidates = []
                for entry in entries:
                    if not isinstance(entry, dict) or not isinstance(entry.get("nutrient"), dict):
                        continue
                    nutrient = entry["nutrient"]
                    if nutrient.get("id") != identifier:
                        continue
                    amount = decimal_amount(entry.get("amount"))
                    unit = str(nutrient.get("unitName", "")).casefold()
                    loq = decimal_amount(entry.get("loq"))
                    if loq is not None and loq > 0:
                        issues.append(f"{name}:below_quantification_limit")
                        continue
                    factors = {"kcal": Decimal(1), "kj": Decimal(1) / Decimal("4.184")} if name == "calories" else {"g": Decimal(1), "mg": Decimal("0.001"), "ug": Decimal("0.000001")}
                    if amount is None or unit not in factors:
                        issues.append(f"{name}:invalid_amount_or_unit")
                        continue
                    candidates.append((amount * factors[unit], amount, unit))
                if candidates:
                    if len({value[0] for value in candidates}) != 1:
                        issues.append(f"{name}:conflicting_source_values")
                        break
                    normalized, original, unit = candidates[0]
                    values[name] = normalized
                    evidence[name] = NutrientEvidence(nutrient_id=identifier, source_unit=unit, source_amount=original, note="Atwater specific > general > conventional kcal > kJ" if name == "calories" else None)
                    break
        return NutritionRecord(provenance=provenance, basis_grams=Decimal(100), basis_description="USDA nutrient amounts per 100 g edible food", nutrients=Nutrients(**values), nutrient_evidence=evidence, portions=_portions(raw, issues), issues=issues)
    except (ValueError, TypeError, KeyError, ValidationError):
        raise USDAResponseError("USDA returned unsupported or invalid food details.") from None
