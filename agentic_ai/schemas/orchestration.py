"""Versioned JSON boundary for a future authenticated HTTP adapter.

Owner identity is deliberately absent: the application passes it out of band.
Decimal amounts serialize as strings, as in the Milestone 2 contracts.
"""
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from agentic_ai.schemas.food import FoodUnderstandingResult
from agentic_ai.schemas.nutrition import FoodCandidate, NutritionResult, Portion
from agentic_ai.schemas.units import ServingUnit


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]


class StartRequest(Contract):
    text: str = Field(min_length=1, max_length=4000)
    provider: Literal["snapshot", "live"] = "snapshot"

    @field_validator("text")
    @classmethod
    def text_is_meaningful(cls, value):
        if not value.strip() or any(ord(c) < 32 and c not in "\t\r\n" for c in value):
            raise ValueError("Invalid meal text")
        return value


class Quantity(Contract):
    kind: Literal["quantity"]
    quantity: Decimal = Field(gt=0, le=1_000_000)
    unit: ServingUnit

    @field_validator("quantity", mode="before")
    @classmethod
    def bounded_decimal(cls, value):
        if isinstance(value, bool) or len(str(value)) > 64:
            raise ValueError("Unsupported quantity")
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            raise ValueError("Unsupported quantity") from None
        if not number.is_finite() or not -12 <= number.as_tuple().exponent <= 9 or len(number.as_tuple().digits) > 20:
            raise ValueError("Unsupported precision")
        return value


class MeasuredGrams(Contract):
    kind: Literal["measured_grams"]
    grams: Decimal = Field(gt=0, le=1_000_000_000)
    _bounded = field_validator("grams", mode="before")(Quantity.bounded_decimal.__func__)


class SelectFood(Contract):
    kind: Literal["select_food"]
    fdc_id: int = Field(gt=0, strict=True)


class SelectPortion(Contract):
    kind: Literal["select_portion"]
    portion_id: str = Field(min_length=1, max_length=100)


class Preparation(Contract):
    kind: Literal["preparation"]
    preparation: str = Field(min_length=1, max_length=120)


class RefineFood(Contract):
    kind: Literal["refine_food"]
    description: str = Field(min_length=1, max_length=1000)


class LeaveUnresolved(Contract):
    kind: Literal["leave_unresolved"]


ReplyAction = Annotated[Quantity | MeasuredGrams | SelectFood | SelectPortion | Preparation | RefineFood | LeaveUnresolved, Field(discriminator="kind")]


class ReplyRequest(Contract):
    expected_revision: int = Field(ge=0, strict=True)
    request_id: Identifier
    question_id: Identifier
    item_id: Identifier
    action: ReplyAction


class RetryRequest(Contract):
    expected_revision: int = Field(ge=0, strict=True)
    request_id: Identifier
    item_id: Identifier | None = None


class Question(Contract):
    question_id: Identifier
    item_id: Identifier
    item_index: int
    reason: str
    allowed_actions: list[str]
    candidates: list[FoodCandidate] = Field(default_factory=list)
    portions: list[Portion] = Field(default_factory=list)


class TraceEvent(Contract):
    sequence: int
    revision: int
    stage: Literal["extraction", "nutrition", "clarification", "session"]
    event: Literal["started", "completed", "needs_clarification", "error", "reused", "applied", "limit_reached"]
    item_id: str | None = None
    reason_code: str | None = None
    fdc_id: int | None = None
    basis_grams: Decimal | None = None
    requested_grams: Decimal | None = None
    scale_factor: Decimal | None = None


class SafeError(Contract):
    code: str
    message: str


class BudgetUsage(Contract):
    turns: int = 0
    steps: int = 0
    tool_calls: int = 0
    http_attempts: int = 0


class ClarificationEvidence(Contract):
    item_id: str
    revision: int
    request_id: str
    action: ReplyAction


class SessionResponse(Contract):
    schema_version: Literal["1.0"] = "1.0"
    session_id: str
    revision: int
    status: Literal["awaiting_clarification", "waiting_for_retry", "completed", "failed", "limit_reached"]
    created_at: float
    expires_at: float
    extraction: FoodUnderstandingResult | None = None
    nutrition: NutritionResult | None = None
    questions: list[Question] = Field(default_factory=list)
    evidence: list[ClarificationEvidence] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    usage: BudgetUsage = Field(default_factory=BudgetUsage)
    error: SafeError | None = None
