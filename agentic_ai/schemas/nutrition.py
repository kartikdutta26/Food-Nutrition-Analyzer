"""Lossless nutrition contracts. Decimal quantities serialize as JSON strings."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentic_ai.schemas.food import FoodItem, FoodUnderstandingResult

Nonnegative = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
NUTRIENTS = ("calories", "protein", "carbs", "fats", "fiber")


class NutritionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class Nutrients(NutritionModel):
    """Calories in kcal; all other fields in grams. None means unknown."""
    calories: Nonnegative | None = None
    protein: Nonnegative | None = None
    carbs: Nonnegative | None = None
    fats: Nonnegative | None = None
    fiber: Nonnegative | None = None


class Provenance(NutritionModel):
    provider: Literal["usda_snapshot", "usda_live", "backend_usda"]
    fdc_id: int = Field(gt=0, strict=True)
    description: str = Field(min_length=1, max_length=1000)
    data_type: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    publication_date: str | None = None
    snapshot_sha256: str | None = None


class NutrientEvidence(NutritionModel):
    nutrient_id: int | None
    source_unit: str
    source_amount: Nonnegative
    note: str | None = None


class Portion(NutritionModel):
    portion_id: str = Field(min_length=1)
    amount: Positive
    unit: str | None
    gram_weight: Positive
    description: str = Field(min_length=1)
    qualifiers: list[str] = Field(default_factory=list)


class NutritionRecord(NutritionModel):
    provenance: Provenance
    basis_grams: Positive
    basis_description: str = Field(min_length=1)
    nutrients: Nutrients
    nutrient_evidence: dict[str, NutrientEvidence] = Field(default_factory=dict)
    portions: list[Portion] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class FoodCandidate(NutritionModel):
    fdc_id: int = Field(gt=0, strict=True)
    description: str = Field(min_length=1, max_length=1000)
    data_type: str = Field(min_length=1)


class SearchResults(NutritionModel):
    candidates: list[FoodCandidate]
    exhaustive: bool
    scope: str


class ItemSelection(NutritionModel):
    item_index: int = Field(ge=0, strict=True)
    fdc_id: int | None = Field(default=None, gt=0, strict=True)
    portion_id: str | None = Field(default=None, min_length=1)
    measured_grams: Positive | None = None

    @model_validator(mode="after")
    def validate_selection(self):
        if self.fdc_id is None and self.portion_id is None and self.measured_grams is None:
            raise ValueError("Provide a source ID, portion ID, or total measured edible grams.")
        if self.portion_id is not None and self.fdc_id is None:
            raise ValueError("A portion ID requires its food's fdc_id.")
        if self.portion_id is not None and self.measured_grams is not None:
            raise ValueError("Choose a database portion or measured total grams, not both.")
        return self


class NutritionRequest(NutritionModel):
    extraction: FoodUnderstandingResult
    selections: list[ItemSelection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_indices(self):
        indices = [s.item_index for s in self.selections]
        if len(indices) != len(set(indices)) or any(i >= len(self.extraction.foods) for i in indices):
            raise ValueError("Selections must refer to distinct, existing food item indices.")
        return self


class NutritionIssue(NutritionModel):
    code: str
    message: str


class PortionResolution(NutritionModel):
    requested_grams: Positive
    method: Literal["mass", "usda_portion", "user_measured"]
    evidence: str
    portion: Portion | None = None


class NutritionItemResult(NutritionModel):
    item_index: int
    food: FoodItem
    status: Literal["complete", "incomplete_nutrients", "needs_clarification", "error"]
    candidates: list[FoodCandidate] = Field(default_factory=list)
    search_scope: str | None = None
    record: NutritionRecord | None = None
    portion: PortionResolution | None = None
    scale_factor: Positive | None = None
    nutrition: Nutrients = Field(default_factory=Nutrients)
    issues: list[NutritionIssue] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class NutrientCoverage(NutritionModel):
    known_items: int = Field(ge=0)
    total_items: int = Field(ge=0)
    complete: bool


class NutritionResult(NutritionModel):
    schema_version: Literal["1.0"] = "1.0"
    status: Literal["complete", "partial", "needs_clarification", "no_food", "error"]
    items: list[NutritionItemResult]
    complete_totals: Nutrients
    known_subtotals: Nutrients
    coverage: dict[str, NutrientCoverage]
    total_items: int
    resolved_items: int
    questions: list[str]
    note: str = "Coverage counts food items, not food weight. Database reference values do not establish a homemade recipe's composition."
