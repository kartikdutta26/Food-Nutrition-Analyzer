"""Metadata-only hard bounds. No environment, model or image is loaded."""
from pydantic import BaseModel, ConfigDict, Field


class VisionContractSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    max_result_bytes: int = Field(default=65_536, ge=1024, le=65_536)
    max_confirmation_bytes: int = Field(default=32_768, ge=1024, le=32_768)
    max_handoff_bytes: int = Field(default=131_072, ge=1024, le=131_072)
    max_groups: int = Field(default=8, ge=1, le=8)
    max_candidates_per_group: int = Field(default=3, ge=1, le=3)
    max_meal_text_chars: int = Field(default=4000, ge=1, le=4000)
    max_m3_request_bytes: int = Field(default=16_384, ge=256, le=16_384)
    max_nodes: int = Field(default=10_000, ge=100, le=10_000)
    max_depth: int = Field(default=20, ge=4, le=20)
