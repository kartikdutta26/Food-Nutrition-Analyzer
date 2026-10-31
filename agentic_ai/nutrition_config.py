"""Separate configuration keeps the committed food-understanding settings stable."""

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from agentic_ai.nutrition_errors import NutritionInputError


class NutritionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    timeout_seconds: float = Field(default=20, gt=0, le=120)
    retries: int = Field(default=1, ge=0, le=2)
    max_retry_wait: float = Field(default=2, ge=0, le=10)
    page_size: int = Field(default=25, ge=1, le=50)

    @classmethod
    def from_environment(cls, env_file: Path | None = None):
        path = env_file if env_file is not None else Path(__file__).parent / ".env"
        values = {**dotenv_values(path, interpolate=False), **os.environ}
        names = {"api_key": "USDA_API_KEY", "timeout_seconds": "USDA_TIMEOUT_SECONDS", "retries": "USDA_RETRIES"}
        try:
            return cls(**{field: values[key] for field, key in names.items() if key in values})
        except (ValueError, ValidationError):
            raise NutritionInputError("Invalid nutrition configuration; check agentic_ai/.env.example.") from None
