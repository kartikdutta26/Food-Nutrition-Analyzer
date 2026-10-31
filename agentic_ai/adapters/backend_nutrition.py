"""Read the existing backend response without importing or changing backend code."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agentic_ai.nutrition_errors import USDAResponseError
from agentic_ai.schemas.nutrition import Nutrients, NutritionRecord, Portion, Positive, Provenance


class BackendServing(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    description: str = Field(min_length=1)
    gram_weight: Positive


class BackendResponse(BaseModel):
    # Ignore documented fields not used by the adapter: notice, matches, preset_id.
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    data_source: Literal["usda_food_data_central"]
    fdc_id: int = Field(gt=0, strict=True)
    name: str = Field(min_length=1)
    category: str | None = None
    serving: BackendServing
    nutrition: Nutrients


def normalize_backend_response(payload, *, retrieved_at=None):
    """The input is a trusted backend response, not proof of an independent API check.

    Its nutrition basis is the returned serving weight, never an assumed 100 g.
    Omitted nutrients stay unknown. This adapter makes no network request.
    """
    try:
        parsed = BackendResponse.model_validate(payload)
        source = Provenance(provider="backend_usda", fdc_id=parsed.fdc_id, description=parsed.name, data_type=parsed.category or "USDA data type not supplied by backend", source_url=f"https://fdc.nal.usda.gov/food-details/{parsed.fdc_id}/nutrients", retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat())
        return NutritionRecord(provenance=source, basis_grams=parsed.serving.gram_weight, basis_description="Backend per-serving values for " + parsed.serving.description, nutrients=parsed.nutrition, portions=[Portion(portion_id="backend-serving", amount=Decimal(1), unit="serving", gram_weight=parsed.serving.gram_weight, description=parsed.serving.description)], issues=["Backend attribution retained; this adapter did not independently fetch USDA details."])
    except (ValidationError, TypeError, ValueError):
        raise USDAResponseError("Expected a USDA backend response with source ID, serving weight and valid nutrients. Sample presets are not verified nutrition.") from None
