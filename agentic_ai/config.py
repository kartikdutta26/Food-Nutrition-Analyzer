"""Load only this module's .env; real environment variables take priority."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from agentic_ai.errors import ConfigurationError


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    base_url: str = "http://127.0.0.1:11434"
    model: str = Field(default="qwen3:4b-instruct", min_length=1, max_length=120)
    timeout_seconds: float = Field(default=120, gt=0, le=600)
    validation_attempts: int = Field(default=2, ge=1, le=3)
    max_input_chars: int = Field(default=4000, ge=1, le=12000)

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in {"", "/"}
        ):
            raise ValueError("Use an HTTP(S) server origin without credentials or a path.")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("Invalid server port.") from exc
        return value.rstrip("/")

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Model name must not be blank.")
        return value.strip()

    @classmethod
    def from_environment(cls, env_file: Path | None = None) -> "Settings":
        path = env_file if env_file is not None else Path(__file__).parent / ".env"
        values = {**dotenv_values(path, interpolate=False), **os.environ}
        names = {
            "base_url": "OLLAMA_BASE_URL", "model": "OLLAMA_MODEL",
            "timeout_seconds": "OLLAMA_TIMEOUT_SECONDS",
            "validation_attempts": "FOOD_VALIDATION_ATTEMPTS",
            "max_input_chars": "FOOD_MAX_INPUT_CHARS",
        }
        try:
            return cls(**{field: values[key] for field, key in names.items() if key in values})
        except (ValidationError, ValueError) as exc:
            raise ConfigurationError("Invalid agentic_ai configuration; check .env.example.") from exc
