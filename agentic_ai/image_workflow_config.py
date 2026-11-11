"""Bounded process-local workflow metadata; no environment or database access."""
from pydantic import BaseModel, ConfigDict, Field


class ImageWorkflowSettings(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
                             revalidate_instances="always", hide_input_in_errors=True)
    max_workflows: int = Field(default=20, ge=1, le=100)
    ttl_seconds: int = Field(default=1800, ge=1, le=86400)
    max_metadata_bytes: int = Field(default=262_144, ge=1024, le=262_144)
    max_store_bytes: int = Field(default=4_194_304, ge=1024, le=16_777_216)
    max_output_bytes: int = Field(default=8_388_608, ge=1024, le=8_388_608)
