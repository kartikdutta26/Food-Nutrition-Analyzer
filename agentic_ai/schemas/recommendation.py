"""M4 v1: interpretation of supplied evidence, never a source of nutrition values."""
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agentic_ai.schemas.nutrition import (
    Nutrients, NutrientCoverage, NutrientEvidence, NutritionResult,
    PortionResolution, Provenance,
)
from agentic_ai.schemas.orchestration import SessionResponse, ClarificationEvidence

NutrientName = Literal["calories", "protein", "carbs", "fats", "fiber"]


class RecommendationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class ExplicitTarget(RecommendationModel):
    nutrient: NutrientName
    value: Decimal = Field(gt=0, le=1_000_000_000)
    unit: Literal["kcal", "g"]
    scope: Literal["meal", "daily"]

    @field_validator("value", mode="before")
    @classmethod
    def bounded_value(cls, value):
        if isinstance(value, bool) or len(str(value)) > 80:
            raise ValueError("Invalid target value")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid target value") from None
        if not number.is_finite() or number.as_tuple().exponent < -12:
            raise ValueError("Invalid target precision")
        return number

    @model_validator(mode="after")
    def correct_unit(self):
        if self.unit != ("kcal" if self.nutrient == "calories" else "g"):
            raise ValueError("Target unit does not match the nutrient")
        return self


class RecommendationContext(RecommendationModel):
    # Labels are retained as untrusted context, never interpolated into guidance.
    preferences: tuple[Annotated[str, Field(min_length=1, max_length=80)], ...] = Field(default=(), max_length=30)
    targets: tuple[ExplicitTarget, ...] = Field(default=(), max_length=5)

    @model_validator(mode="after")
    def distinct_targets(self):
        keys = [target.nutrient for target in self.targets]
        if len(keys) != len(set(keys)):
            raise ValueError("Supply one target per nutrient")
        if any(not value.strip() for value in self.preferences):
            raise ValueError("Preference labels must not be blank")
        return self


class NutritionInput(RecommendationModel):
    kind: Literal["nutrition"] = "nutrition"
    result: NutritionResult


class SessionInput(RecommendationModel):
    kind: Literal["session"] = "session"
    result: SessionResponse


class RecommendationRequest(RecommendationModel):
    schema_version: Literal["1.0"] = "1.0"
    source: Annotated[NutritionInput | SessionInput, Field(discriminator="kind")]
    context: RecommendationContext = Field(default_factory=RecommendationContext)
    expected_revision: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def revision_requires_session(self):
        if self.expected_revision is not None and self.source.kind != "session":
            raise ValueError("An expected revision requires session input")
        return self


class InputReference(RecommendationModel):
    kind: Literal["nutrition", "session"]
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    session_id: str | None = None
    revision: int | None = None
    session_status: str | None = None
    expires_at: float | None = None
    expired: bool = False


class NutritionFact(RecommendationModel):
    id: str
    nutrient: NutrientName
    amount: Decimal | None
    unit: Literal["kcal", "g"]
    basis: Literal["complete_total", "known_subtotal", "item", "unknown"]
    coverage: NutrientCoverage
    item_index: int | None = None
    source_refs: tuple[str, ...] = ()


class SourceCitation(RecommendationModel):
    id: str
    item_index: int
    provenance: Provenance
    basis_grams: Decimal
    basis_description: str
    source_nutrients: Nutrients
    source_issues: tuple[str, ...] = ()
    nutrient_evidence: dict[str, NutrientEvidence]
    portion: PortionResolution | None
    scale_factor: Decimal | None
    attribution: Literal["supplied_usda_record", "delegated_backend_record"]


class InterpretationMessage(RecommendationModel):
    code: str
    text: str
    evidence_refs: tuple[str, ...] = ()
    rule_id: str
    question_id: str | None = None
    item_id: str | None = None
    item_index: int | None = None
    allowed_actions: tuple[str, ...] = ()


class TargetComparison(RecommendationModel):
    nutrient: NutrientName
    target: ExplicitTarget
    relation: Literal["below", "equal", "above", "not_compared"]
    reason: Literal["user_supplied_meal_benchmark", "scope_mismatch", "incomplete_nutrient", "session_unavailable"]
    fact_ref: str


class RecommendationResult(RecommendationModel):
    schema_version: Literal["1.0"] = "1.0"
    ruleset_version: Literal["1.0"] = "1.0"
    status: Literal["ready", "limited", "unavailable"]
    generation_mode: Literal["deterministic"] = "deterministic"
    validation_scope: Literal["supplied_record_consistency_only"] = "supplied_record_consistency_only"
    input_ref: InputReference
    context: RecommendationContext
    nutrition_status: str | None
    complete_totals: Nutrients | None
    known_subtotals: Nutrients | None
    coverage: dict[str, NutrientCoverage]
    facts: tuple[NutritionFact, ...]
    observations: tuple[InterpretationMessage, ...]
    suggestions: tuple[InterpretationMessage, ...]
    next_steps: tuple[InterpretationMessage, ...]
    limitations: tuple[InterpretationMessage, ...]
    citations: tuple[SourceCitation, ...]
    session_evidence: tuple[ClarificationEvidence, ...] = ()
    comparisons: tuple[TargetComparison, ...]
