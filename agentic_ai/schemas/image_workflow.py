"""Additive snapshot envelope; nested M3/M4/M5 contracts are unchanged."""
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agentic_ai.schemas.orchestration import Identifier, SessionResponse
from agentic_ai.schemas.recommendation import RecommendationResult
from agentic_ai.schemas.vision import ConfirmedImageMeal, ImageFoodRecognitionResult


class ImageWorkflowSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal["1.0"] = "1.0"
    workflow_id: Identifier
    phase: Literal["awaiting_confirmation", "session_started", "start_failed"]
    expires_at: float
    recognition: ImageFoodRecognitionResult
    handoff: ConfirmedImageMeal | None = None
    session: SessionResponse | None = None
    recommendations: RecommendationResult | None = None
