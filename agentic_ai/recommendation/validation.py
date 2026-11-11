"""Read-only consistency checks. This is not independent USDA verification."""
import hashlib
import json
import math
import re
from datetime import datetime
from decimal import Decimal, DecimalException, localcontext

from pydantic import BaseModel, ValidationError

from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.schemas.nutrition import ItemSelection, NUTRIENTS
from agentic_ai.schemas.recommendation import RecommendationRequest
from agentic_ai.schemas.quantity import parse_quantity
from agentic_ai.schemas.food import RawFood
from agentic_ai.tools.nutrition_calculator import calculate, summarize
from agentic_ai.tools.portion_calculator import resolve_portion
from agentic_ai.tools.usda_normalization import IDS

_NUMBERS = set(NUTRIENTS) | {"quantity", "grams", "amount", "value", "source_amount", "basis_grams", "requested_grams", "gram_weight", "scale_factor", "revision", "expected_revision", "item_index", "fdc_id", "nutrient_id", "known_items", "total_items", "resolved_items", "created_at", "expires_at"}
_ACTIONS = {"quantity", "measured_grams", "select_food", "select_portion", "preparation", "refine_food", "leave_unresolved"}


def fail(code="inconsistent_nutrition"):
    raise RecommendationError(code) from None


def _scan(value, settings, *, key="", depth=0, counter=None):
    counter = counter if counter is not None else [0]
    counter[0] += 1
    if counter[0] > settings.max_nodes or depth > settings.max_depth:
        fail("input_limit")
    if isinstance(value, bool):
        if key in _NUMBERS:
            fail("invalid_input")
    elif isinstance(value, (float, Decimal)):
        number = Decimal(str(value))
        if not number.is_finite() or len(str(value)) > 160:
            fail("invalid_input")
        if abs(number.as_tuple().exponent) > 100 or len(number.as_tuple().digits) > 80:
            fail("input_limit")
    elif isinstance(value, int):
        if len(str(value)) > 40:
            fail("input_limit")
    elif isinstance(value, str):
        if len(value) > 4000:
            fail("input_limit")
        if key in _NUMBERS:
            try:
                _scan(Decimal(value), settings, key=key, depth=depth, counter=counter)
            except (DecimalException, ValueError):
                fail("invalid_input")
    elif isinstance(value, dict):
        for name, child in value.items():
            if not isinstance(name, str):
                fail("invalid_input")
            _scan(child, settings, key=name, depth=depth + 1, counter=counter)
    elif isinstance(value, (list, tuple)):
        if len(value) > 1000:
            fail("input_limit")
        for child in value:
            _scan(child, settings, key=key, depth=depth + 1, counter=counter)
    elif value is not None:
        fail("invalid_input")


def strict_json(raw):
    """Reject duplicate keys and nonfinite JSON constants before schema validation."""
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                fail("invalid_input")
            result[key] = value
        # M1 FoodItem deliberately exposes quantity as a strict float. Preserve
        # that contract while keeping nutrient/target/M3-action JSON decimals exact.
        if {"name", "source_text", "quantity"} <= result.keys() and isinstance(result["quantity"], Decimal):
            result["quantity"] = float(result["quantity"])
        return result
    return json.loads(raw, parse_float=Decimal,
                      parse_constant=lambda _: fail("invalid_input"), object_pairs_hook=pairs)


def parse_request(value, settings):
    try:
        if isinstance(value, (bytes, str)):
            if len(value.encode("utf-8") if isinstance(value, str) else value) > settings.max_input_bytes:
                fail("input_limit")
            raw = strict_json(value)
        else:
            raw = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
        _scan(raw, settings)
        encoded = json.dumps(raw, default=lambda item: str(item) if isinstance(item, Decimal) else fail("invalid_input"), allow_nan=False, sort_keys=True)
        if len(encoded.encode("utf-8")) > settings.max_input_bytes:
            fail("input_limit")
        request = RecommendationRequest.model_validate_json(encoded)
        # Revalidation above also covers mutated/model_construct Pydantic instances.
        if request.source.kind == "session":
            session = request.source.result
            if type(session.revision) is not int or session.revision < 0 or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", session.session_id):
                fail("invalid_input")
            if not (math.isfinite(session.created_at) and math.isfinite(session.expires_at)) or session.expires_at <= session.created_at:
                fail("invalid_input")
            if request.expected_revision is not None and request.expected_revision != session.revision:
                fail("stale_revision")
        return request, hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    except RecommendationError:
        raise
    except (ValidationError, ValueError, TypeError, OverflowError, RecursionError, DecimalException):
        fail("invalid_input")


def _record(record):
    source = record.provenance
    if source.source_url != f"https://fdc.nal.usda.gov/food-details/{source.fdc_id}/nutrients":
        fail("invalid_evidence")
    try:
        datetime.fromisoformat(source.retrieved_at.replace("Z", "+00:00"))
    except ValueError:
        fail("invalid_evidence")
    if not source.description.strip() or not source.data_type.strip() or not record.basis_description.strip():
        fail("invalid_evidence")
    if source.provider == "usda_snapshot":
        if not source.snapshot_sha256 or not re.fullmatch(r"[a-f0-9]{64}", source.snapshot_sha256):
            fail("invalid_evidence")
    elif source.snapshot_sha256 is not None:
        fail("invalid_evidence")
    ids = [portion.portion_id for portion in record.portions]
    if len(ids) != len(set(ids)) or len(ids) > 200:
        fail("invalid_evidence")
    if set(record.nutrient_evidence) - set(NUTRIENTS):
        fail("invalid_evidence")
    for name in NUTRIENTS:
        amount = getattr(record.nutrients, name)
        evidence = record.nutrient_evidence.get(name)
        if amount is None:
            if evidence is not None:
                fail("invalid_evidence")
            continue
        if evidence is None:
            if source.provider != "backend_usda":
                fail("invalid_evidence")
            continue
        if evidence.nutrient_id not in IDS[name] and not (source.provider == "backend_usda" and evidence.nutrient_id is None):
            fail("invalid_evidence")
        unit = evidence.source_unit.casefold()
        # Match M2 normalization's source arithmetic, including its 28-digit kJ factor.
        with localcontext() as context:
            context.prec = 28
            factors = {"kcal": Decimal(1), "kj": Decimal(1) / Decimal("4.184")} if name == "calories" else {"g": Decimal(1), "mg": Decimal("0.001"), "ug": Decimal("0.000001")}
            if unit not in factors or amount != evidence.source_amount * factors[unit]:
                fail("invalid_evidence")
    if source.provider != "backend_usda" and record.basis_grams != 100:
        fail("invalid_evidence")


def _exact_quantity(food, session):
    if session is None:
        return None
    # M3 preserves exact Decimal clarification quantity_text separately from its float.
    # Public M3 results do not map every completed item to a private item ID; these
    # are consistency checks on upstream evidence, not proof of original user input.
    for entry in session.evidence:
        action = entry.action
        if action.kind == "quantity" and str(action.quantity) == food.quantity_text and action.unit == food.unit and float(action.quantity) == food.quantity:
            return str(action.quantity)
    return None


def _portion(item, session):
    resolution, record, food = item.portion, item.record, item.food
    if resolution is None:
        return
    if record is None or resolution.requested_grams > Decimal("1000000000"):
        fail("invalid_evidence")
    selection = ItemSelection(item_index=item.item_index, fdc_id=record.provenance.fdc_id)
    if resolution.method == "user_measured":
        if resolution.portion is not None:
            fail("invalid_evidence")
        if session is not None and not any(e.action.kind == "measured_grams" and e.action.grams == resolution.requested_grams for e in session.evidence):
            fail("invalid_evidence")
        selection = selection.model_copy(update={"measured_grams": resolution.requested_grams})
    elif resolution.method == "usda_portion":
        if resolution.portion is None or not any(p == resolution.portion for p in record.portions):
            fail("invalid_evidence")
        selection = selection.model_copy(update={"portion_id": resolution.portion.portion_id})
    elif resolution.portion is not None:
        fail("invalid_evidence")
    exact = _exact_quantity(food, session)
    if exact is None:
        try:
            RawFood.model_validate({key:getattr(food,key) for key in ("name", "quantity_text", "unit", "preparation", "source_text")})
        except ValidationError:
            fail("invalid_evidence")
    if food.quantity is not None and exact is None:
        if food.quantity_text is None or parse_quantity(food.quantity_text, unit=food.unit) != food.quantity:
            fail("invalid_evidence")
    expected, _, issue = resolve_portion(food, record, selection, exact_quantity=exact)
    if issue is not None or expected != resolution:
        fail("invalid_evidence")


def validate_nutrition(request, settings):
    session = request.source.result if request.source.kind == "session" else None
    nutrition = session.nutrition if session else request.source.result
    if session:
        if session.extraction is None:
            if nutrition is not None or session.questions or session.status in {"completed", "awaiting_clarification"}:
                fail("inconsistent_nutrition")
            return None, session
        if nutrition is None or len(session.extraction.foods) != len(nutrition.items):
            fail("inconsistent_nutrition")
        if session.revision < 1:
            fail("invalid_input")
        request_ids = [entry.request_id for entry in session.evidence]
        if len(request_ids) != len(set(request_ids)) or any(entry.revision < 1 or entry.revision > session.revision for entry in session.evidence):
            fail("invalid_evidence")
        questions = session.questions
        if len({q.question_id for q in questions}) != len(questions) or len({q.item_id for q in questions}) != len(questions):
            fail("invalid_evidence")
        for q in questions:
            if q.item_index < 0 or q.item_index >= len(nutrition.items) or nutrition.items[q.item_index].status != "needs_clarification" or not q.allowed_actions or set(q.allowed_actions) - _ACTIONS:
                fail("invalid_evidence")
        if session.status == "completed" and questions:
            fail("inconsistent_nutrition")
        if session.status == "awaiting_clarification" and not questions:
            fail("inconsistent_nutrition")
    if len(nutrition.items) > settings.max_items:
        fail("input_limit")
    if [item.item_index for item in nutrition.items] != list(range(len(nutrition.items))):
        fail("inconsistent_nutrition")
    originals = []
    for item in nutrition.items:
        draft = item.model_copy(deep=True)
        if item.record:
            _record(item.record)
            offered = [c for c in item.candidates if c.fdc_id == item.record.provenance.fdc_id]
            if len(offered) != 1 or offered[0].description != item.record.provenance.description or offered[0].data_type != item.record.provenance.data_type:
                fail("invalid_evidence")
        _portion(item, session)
        if item.status in {"complete", "incomplete_nutrients"}:
            if item.record is None or item.portion is None:
                fail("invalid_evidence")
            calculated, factor = calculate(item.record, item.portion.requested_grams)
            with localcontext() as context:
                context.prec = 40
                for name in NUTRIENTS:
                    value = getattr(calculated, name)
                    rounded = value.quantize(Decimal("0.0001")) if value is not None else None
                    if getattr(item.nutrition, name) != rounded:
                        fail("inconsistent_nutrition")
            if factor != item.scale_factor:
                fail("inconsistent_nutrition")
            complete = all(getattr(calculated, name) is not None for name in NUTRIENTS)
            if item.status != ("complete" if complete else "incomplete_nutrients"):
                fail("inconsistent_nutrition")
            draft.nutrition = calculated
        elif item.scale_factor is not None or any(getattr(item.nutrition, name) is not None for name in NUTRIENTS):
            fail("inconsistent_nutrition")
        originals.append(draft)
    # Recreate unrounded contributions; never sum rounded public item values.
    expected = summarize(originals)
    for name in ("status", "complete_totals", "known_subtotals", "coverage", "total_items", "resolved_items", "questions"):
        if getattr(nutrition, name) != getattr(expected, name):
            fail("inconsistent_nutrition")
    return nutrition, session
