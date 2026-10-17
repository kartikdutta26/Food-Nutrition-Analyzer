from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NutritionValues(BaseModel):
    """Nutrition values per serving, with grams for macros and fiber."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    calories: float = Field(ge=0, le=100_000, description="kcal per serving")
    protein: float = Field(ge=0, le=10_000, description="grams per serving")
    carbs: float = Field(ge=0, le=10_000, description="grams per serving")
    fats: float = Field(ge=0, le=10_000, description="grams per serving")
    fiber: float | None = Field(
        default=0,
        ge=0,
        le=10_000,
        description="grams per serving, or null when the source does not report it",
    )


class FoodServing(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=200)
    gram_weight: float = Field(gt=0, le=100_000)


class FoodAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    preset_id: str | None = Field(default=None, min_length=1, max_length=80)
    food_name: str | None = Field(default=None, min_length=1, max_length=120)
    fdc_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_one_food_identifier(self):
        if not self.preset_id and not self.food_name:
            raise ValueError(
                "Provide 'preset_id' or 'food_name'; an 'fdc_id' requires its food_name."
            )
        if self.preset_id and self.food_name:
            raise ValueError(
                "Send only one of 'preset_id' or 'food_name'; remove the other field."
            )
        if self.preset_id and self.fdc_id is not None:
            raise ValueError("Send 'preset_id' alone, or 'food_name' with a USDA 'fdc_id'.")
        return self


class FoodMatchOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fdc_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=400)
    category: str | None = None


class FoodAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset_id: str | None = None
    fdc_id: int | None = None
    name: str = Field(min_length=1, max_length=400)
    category: str | None = None
    serving: FoodServing | None = None
    nutrition: NutritionValues
    data_source: Literal["sample_preset", "usda_food_data_central"]
    notice: str
    matches: list[FoodMatchOption] = Field(default_factory=list)


class MealCreateRequest(BaseModel):
    """Log a supported preset, USDA lookup, or user-supplied nutrition values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    preset_id: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=400)
    nutrition: NutritionValues | None = None
    data_source: Literal["user_provided", "usda_food_data_central"] = "user_provided"
    fdc_id: int | None = Field(default=None, gt=0)
    serving: FoodServing | None = None
    meal_slot: Literal["Breakfast", "Lunch", "Dinner", "Snack"] = "Lunch"
    consumed_at: datetime | None = None

    @field_validator("meal_slot", mode="before")
    @classmethod
    def normalize_meal_slot(cls, value):
        if isinstance(value, str):
            allowed = {
                "breakfast": "Breakfast",
                "lunch": "Lunch",
                "dinner": "Dinner",
                "snack": "Snack",
            }
            return allowed.get(value.strip().casefold(), value)
        return value

    @model_validator(mode="after")
    def validate_source(self):
        if self.preset_id:
            if (
                self.name is not None
                or self.nutrition is not None
                or self.data_source != "user_provided"
                or self.fdc_id is not None
                or self.serving is not None
            ):
                raise ValueError(
                    "When 'preset_id' is supplied, omit custom nutrition and source fields; "
                    "the server supplies the preset values."
                )
        elif self.name is None and self.nutrition is None:
            raise ValueError(
                "Provide 'preset_id' alone, or provide both 'name' and 'nutrition'."
            )
        elif self.name is None:
            raise ValueError(
                "'name' is required with caller-provided 'nutrition'; "
                "or use 'preset_id' alone."
            )
        elif self.nutrition is None:
            raise ValueError(
                "'nutrition' is required with a custom 'name'; include calories, "
                "protein, carbs, and fats (fiber is optional), or use 'preset_id'."
            )
        elif self.data_source == "usda_food_data_central":
            if self.fdc_id is None or self.serving is None:
                raise ValueError(
                    "USDA meal records require 'fdc_id' and 'serving' from the food lookup."
                )
        elif self.fdc_id is not None or self.serving is not None:
            raise ValueError(
                "'fdc_id' and 'serving' are only supported for USDA FoodData Central meals."
            )
        return self


class MealResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    preset_id: str | None = None
    name: str
    meal_slot: Literal["Breakfast", "Lunch", "Dinner", "Snack"]
    consumed_at: datetime
    meal_day: date
    nutrition: NutritionValues
    data_source: Literal["sample_preset", "user_provided", "usda_food_data_central"]
    fdc_id: int | None = None
    serving: FoodServing | None = None


class MealListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MealResponse]
    count: int


class DailyNutritionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    meal_count: int
    totals: NutritionValues


class NutritionTargets(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    calories: float = Field(gt=0, le=100_000)
    protein: float = Field(gt=0, le=10_000)
    carbs: float = Field(gt=0, le=10_000)
    fats: float = Field(gt=0, le=10_000)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dietary_preferences: (
        list[Annotated[str, Field(min_length=1, max_length=80)]] | None
    ) = Field(
        default=None,
        max_length=30,
        description=(
            "Up to 30 non-empty preference labels; use [] to clear the list."
        ),
    )
    targets: NutritionTargets | None = None

    @model_validator(mode="after")
    def require_update(self):
        fields = self.model_fields_set
        if not fields:
            raise ValueError(
                "Provide at least one field: 'dietary_preferences' or 'targets'."
            )
        if "dietary_preferences" in fields and self.dietary_preferences is None:
            raise ValueError(
                "'dietary_preferences' cannot be null; provide an array "
                "(use [] to clear it) or omit the field."
            )
        if "targets" in fields and self.targets is None:
            raise ValueError(
                "'targets' cannot be null; provide all four target values "
                "or omit the field."
            )
        return self


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dietary_preferences: list[str]
    targets: NutritionTargets | None = None
    updated_at: datetime | None = None


class RootResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str


class DatabaseHealthResponse(BaseModel):
    status: Literal["connected"]
    database: str
