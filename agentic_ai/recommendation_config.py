"""Explicit, bounded M4 configuration. No environment, model or network setup."""
from pydantic import BaseModel, ConfigDict, Field


class RecommendationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    max_input_bytes: int = Field(default=4_194_304, ge=1024, le=4_194_304)
    max_output_bytes: int = Field(default=2_097_152, ge=1024, le=2_097_152)
    max_items: int = Field(default=40, ge=1, le=40)
    max_messages: int = Field(default=128, ge=1, le=128)
    max_nodes: int = Field(default=100_000, ge=100, le=100_000)
    max_depth: int = Field(default=32, ge=4, le=32)
