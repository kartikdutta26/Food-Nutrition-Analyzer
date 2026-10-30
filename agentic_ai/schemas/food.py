"""The model's evidence contract and the public food-understanding result."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from agentic_ai.schemas.units import ServingUnit, UNIT_ALIASES


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class RawFood(StrictModel):
    name: str = Field(min_length=1, max_length=120, description="A specific food name, not a nutrient.")
    quantity_text: str | None = Field(description="Exact quantity substring, e.g. 'two', '1/2'; null if absent.")
    unit: ServingUnit | None = Field(description="Singular unit, e.g. piece, g, ml, cup, katori; null if unknown.")
    preparation: str | None = Field(description="Exact preparation substring from source_text, otherwise null.")
    source_text: str = Field(min_length=1, max_length=4000, description="Exact contiguous meal substring for this item, including its quantity.")

    @field_validator("unit", mode="before")
    @classmethod
    def normalize_unit(cls, value):
        if isinstance(value, str):
            value = value.strip().casefold()
            return UNIT_ALIASES.get(value, value)
        return value

    @model_validator(mode="after")
    def validate_text_fields(self) -> "RawFood":
        for field in ("name", "quantity_text", "unit", "preparation", "source_text"):
            value = getattr(self, field)
            if value is not None and not value.strip():
                raise ValueError(f"{field} must not be blank; use null for missing fields.")
            if value is not None and len(value) > 4000:
                raise ValueError(f"{field} is too long.")
        if self.quantity_text is not None:
            boundary = r"[\w./+−\-¼½¾⅓⅔⅛⅜⅝⅞]"
            pattern = rf"(?<!{boundary}){re.escape(self.quantity_text)}(?!{boundary})"
            # Reject dropping the whole part of a mixed numeric fraction.
            numeric = r"[+\-\u2212]?(?:\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+(?:\.\d+)?|\.\d+)"
            stated, quoted = re.match(numeric, self.source_text), re.match(numeric, self.quantity_text)
            if stated and quoted and stated[0] != quoted[0]:
                raise ValueError("quantity_text omits part of the numeric expression.")
            if not re.search(pattern, self.source_text):
                raise ValueError("quantity_text must be a complete expression in source_text.")
        return self


class RawMeal(StrictModel):
    foods: list[RawFood] = Field(max_length=40)

    @model_validator(mode="after")
    def validate_sources(self, info: ValidationInfo) -> "RawMeal":
        original = (info.context or {}).get("original_text")
        if original is None:
            return self
        cursor = 0
        for food in self.foods:
            start = original.find(food.source_text, cursor)
            if start < 0:
                raise ValueError("Food source_text must quote distinct, ordered spans of the original input.")
            # A quoted span must not start halfway through a signed/decimal number.
            if food.source_text[0].isdigit() and start > 0:
                previous = original[start - 1]
                if previous.isdigit() or previous in "./+-\u2212":
                    raise ValueError("source_text starts inside a quantity expression.")
            if re.match(r"\d+\s*/", food.source_text) and re.search(r"\d+\s+$", original[:start]):
                raise ValueError("source_text omits the whole part of a mixed fraction.")
            cursor = start + len(food.source_text)
        return self


Issue = Literal["missing_quantity", "unresolved_quantity", "invalid_quantity", "missing_unit"]


class FoodItem(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: float | None = Field(gt=0, le=1_000_000)
    quantity_text: str | None
    unit: ServingUnit | None
    preparation: str | None
    source_text: str = Field(min_length=1, max_length=4000)
    issues: list[Issue] = Field(default_factory=list)


class FoodUnderstandingResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["success", "needs_clarification", "no_food"]
    foods: list[FoodItem] = Field(max_length=40)
    questions: list[str] = Field(default_factory=list)
