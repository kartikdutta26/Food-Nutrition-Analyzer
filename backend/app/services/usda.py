import math
import os
import re
from typing import Any

import httpx
from fastapi import HTTPException

from app.schemas.nutrition import (
    FoodAnalysisResponse,
    FoodMatchOption,
    FoodServing,
    NutritionValues,
)


FDC_API_BASE = "https://api.nal.usda.gov/fdc/v1"
REQUEST_TIMEOUT_SECONDS = 8.0
USDA_DATA_SOURCE = "usda_food_data_central"

NUTRIENT_IDS = {
    "calories": {1008, 208},
    "protein": {1003, 203},
    "carbs": {1005, 205},
    "fats": {1004, 204},
    "fiber": {1079, 291},
}

NUTRIENT_NAME_PARTS = {
    "calories": ("energy",),
    "protein": ("protein",),
    "carbs": ("carbohydrate",),
    "fats": ("total lipid", "total fat"),
    "fiber": ("fiber, total dietary", "dietary fiber", "fiber"),
}

# These descriptors change the food substantially when the user entered only
# the generic food name. Keep them eligible when the user explicitly asks for
# that preparation (for example, "banana powder").
SPECIALTY_PREPARATIONS = {
    "chip",
    "concentrate",
    "dehydrated",
    "dried",
    "extract",
    "flour",
    "powder",
    "juice",
}


def _normalized_tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", value.casefold())
    normalized = set()
    for token in tokens:
        if len(token) > 4 and token.endswith("ies"):
            token = f"{token[:-3]}y"
        elif len(token) > 4 and token.endswith(("sses", "ches", "shes", "xes", "zes", "oes")):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        normalized.add(token)
    return normalized


def _candidate_matches_query(query: str, candidate: dict[str, Any]) -> bool:
    description = candidate.get("description")
    if not isinstance(description, str) or not description.strip():
        return False
    query_tokens = _normalized_tokens(query)
    description_tokens = _normalized_tokens(description)
    if not query_tokens or not query_tokens.issubset(description_tokens):
        return False
    unrequested_preparations = (
        SPECIALTY_PREPARATIONS & (description_tokens - query_tokens)
    )
    requested_preparations = SPECIALTY_PREPARATIONS & query_tokens
    return not unrequested_preparations or bool(requested_preparations)


def _candidate_relevance(query: str, candidate: dict[str, Any]) -> tuple[int, int]:
    """Rank matching USDA names by closeness, with exact names first."""
    query_tokens = _normalized_tokens(query)
    description_tokens = _normalized_tokens(str(candidate.get("description") or ""))
    extra_tokens = description_tokens - query_tokens
    return (int(not extra_tokens), -len(extra_tokens))


def _request_json(url: str, params: dict[str, Any] | list[tuple[str, Any]]) -> Any:
    try:
        response = httpx.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="USDA FoodData Central took too long to respond. Try again.",
        ) from None
    except httpx.HTTPStatusError as error:
        status_code = 503 if error.response.status_code == 429 else 502
        raise HTTPException(
            status_code=status_code,
            detail="USDA FoodData Central could not complete the lookup. Try again later.",
        ) from None
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to USDA FoodData Central. Try again later.",
        ) from None

    try:
        return response.json()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=502,
            detail="USDA FoodData Central returned an unreadable response.",
        ) from None


def _read_nutrient(item: dict[str, Any]) -> tuple[int | None, str, str, Any]:
    nutrient = item.get("nutrient")
    nutrient = nutrient if isinstance(nutrient, dict) else {}
    identifier = item.get("nutrientId", nutrient.get("id"))
    try:
        identifier = int(identifier) if identifier is not None else None
    except (TypeError, ValueError):
        identifier = None
    name = str(item.get("nutrientName") or nutrient.get("name") or "").casefold()
    unit = str(item.get("unitName") or nutrient.get("unitName") or "").casefold()
    amount = item.get("amount", item.get("value"))
    return identifier, name, unit, amount


def _nutrient_amounts(food: dict[str, Any]) -> dict[str, float | None]:
    raw_nutrients = food.get("foodNutrients")
    if not isinstance(raw_nutrients, list):
        raw_nutrients = []

    amounts: dict[str, float | None] = {
        "calories": None,
        "protein": None,
        "carbs": None,
        "fats": None,
        "fiber": None,
    }
    units: dict[str, str] = {}

    for item in raw_nutrients:
        if not isinstance(item, dict):
            continue
        identifier, name, unit, raw_amount = _read_nutrient(item)
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(amount) or amount < 0:
            continue

        for nutrient_name, identifiers in NUTRIENT_IDS.items():
            if amounts[nutrient_name] is not None:
                continue
            name_parts = NUTRIENT_NAME_PARTS[nutrient_name]
            is_match = identifier in identifiers or any(part in name for part in name_parts)
            if is_match:
                amounts[nutrient_name] = amount
                units[nutrient_name] = unit
                break

    if amounts["calories"] is not None and units.get("calories") in {"kj", "kilojoule", "kilojoules"}:
        amounts["calories"] /= 4.184

    for name in ("protein", "carbs", "fats", "fiber"):
        if amounts[name] is not None and units.get(name) in {"mg", "milligram", "milligrams"}:
            amounts[name] /= 1000

    if any(amounts[name] is None for name in ("calories", "protein", "carbs", "fats")):
        raise HTTPException(
            status_code=404,
            detail="USDA FoodData Central found this food but does not report complete calories and macronutrients.",
        )
    return amounts


def _default_serving(food: dict[str, Any]) -> FoodServing:
    portions = food.get("foodPortions")
    if isinstance(portions, list):
        valid_portions: list[tuple[tuple[int, int], FoodServing]] = []
        for portion in portions:
            if not isinstance(portion, dict):
                continue
            try:
                gram_weight = float(portion.get("gramWeight"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(gram_weight) or gram_weight <= 0:
                continue
            description = str(portion.get("portionDescription") or "").strip()
            if not description:
                modifier = str(portion.get("modifier") or "").strip()
                try:
                    amount = float(portion.get("amount"))
                except (TypeError, ValueError):
                    amount = None
                unit = portion.get("measureUnit", {})
                unit_name = unit.get("name", "") if isinstance(unit, dict) else ""
                if modifier:
                    description = modifier
                elif amount and unit_name:
                    description = f"{amount:g} {unit_name}"
                else:
                    description = "1 serving"
            serving = FoodServing(
                description=f"{description[:160]} ({gram_weight:g} g)",
                gram_weight=gram_weight,
            )
            portion_text = " ".join(
                str(value)
                for value in (
                    portion.get("portionDescription"),
                    portion.get("modifier"),
                    portion.get("measureUnit", {}).get("name")
                    if isinstance(portion.get("measureUnit"), dict)
                    else None,
                )
                if value
            ).casefold()
            preference = 0
            if re.search(r"\bmedium\b", portion_text):
                preference += 5
            if re.search(r"\bcup\b", portion_text):
                preference += 4
            if re.search(r"\b(whole|fruit|piece)\b", portion_text):
                preference += 3
            if re.search(r"\b(inch|inches|cm|millimeter|millimeters)\b", portion_text):
                preference -= 2
            if gram_weight < 10:
                preference -= 5
            valid_portions.append(((preference, int(bool(description))), serving))

        if valid_portions:
            return max(valid_portions, key=lambda item: item[0])[1]

    return FoodServing(description="100 g", gram_weight=100)


def lookup_usda_food(
    food_name: str, selected_fdc_id: int | None = None
) -> FoodAnalysisResponse:
    api_key = os.getenv("USDA_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="USDA food lookup is not configured. Add USDA_API_KEY to backend/.env.",
        )

    search_payload = _request_json(
        f"{FDC_API_BASE}/foods/search",
        [
            ("api_key", api_key),
            ("query", food_name),
            ("pageSize", 25),
            ("dataType", "Foundation,SR Legacy,Survey (FNDDS)"),
        ],
    )
    foods = search_payload.get("foods") if isinstance(search_payload, dict) else None
    if not isinstance(foods, list):
        raise HTTPException(
            status_code=502,
            detail="USDA FoodData Central returned an invalid search response.",
        )

    candidates = []
    for candidate in foods:
        if not isinstance(candidate, dict) or not _candidate_matches_query(food_name, candidate):
            continue
        try:
            candidate_id = int(candidate.get("fdcId"))
        except (TypeError, ValueError):
            continue
        if candidate_id > 0:
            candidates.append((candidate, candidate_id))

    candidates.sort(
        key=lambda entry: _candidate_relevance(food_name, entry[0]), reverse=True
    )
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No USDA FoodData Central match found for '{food_name}'. Try a more specific food name.",
        )

    if selected_fdc_id is None:
        match, fdc_id = candidates[0]
    else:
        selected = next(
            (entry for entry in candidates if entry[1] == selected_fdc_id),
            None,
        )
        if selected is None:
            raise HTTPException(
                status_code=404,
                detail=f"The selected USDA food is not a match for '{food_name}'. Search again and choose a listed match.",
            )
        match, fdc_id = selected

    matches = []
    seen_ids = set()
    for candidate, candidate_id in candidates:
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        matches.append(
            FoodMatchOption(
                fdc_id=candidate_id,
                name=str(candidate.get("description") or "").strip(),
                category=(
                    str(candidate["dataType"])
                    if candidate.get("dataType")
                    else None
                ),
            )
        )
        if len(matches) == 5:
            break

    food = _request_json(
        f"{FDC_API_BASE}/food/{fdc_id}",
        {"api_key": api_key},
    )
    if not isinstance(food, dict):
        raise HTTPException(
            status_code=502,
            detail="USDA FoodData Central returned invalid food details.",
        )

    amounts = _nutrient_amounts(food)
    serving = _default_serving(food)
    scale = serving.gram_weight / 100
    nutrition = NutritionValues(
        calories=round(amounts["calories"] * scale, 4),
        protein=round(amounts["protein"] * scale, 4),
        carbs=round(amounts["carbs"] * scale, 4),
        fats=round(amounts["fats"] * scale, 4),
        fiber=(
            round(amounts["fiber"] * scale, 4)
            if amounts["fiber"] is not None
            else None
        ),
    )
    description = str(food.get("description") or match.get("description") or food_name).strip()
    data_type = str(food.get("dataType") or match.get("dataType") or "USDA FoodData Central")

    return FoodAnalysisResponse(
        fdc_id=fdc_id,
        name=description,
        category=data_type,
        serving=serving,
        nutrition=nutrition,
        data_source=USDA_DATA_SOURCE,
        matches=matches,
        notice=(
            f"Nutrition values from USDA FoodData Central for {serving.description}. "
            "Values are scaled from the USDA nutrient amounts per 100 g."
        ),
    )
