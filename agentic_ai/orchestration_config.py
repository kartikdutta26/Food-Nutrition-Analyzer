"""Hard upper bounds; environment configuration reads only named variables."""
import os
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from agentic_ai.orchestration_errors import OrchestrationError


class OrchestrationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_sessions: int = Field(default=20, ge=1, le=100)
    ttl_seconds: int = Field(default=1800, ge=1, le=86400)
    max_session_bytes: int = Field(default=2_097_152, ge=4096, le=4_194_304)
    max_store_bytes: int = Field(default=16_777_216, ge=4096, le=67_108_864)
    max_request_bytes: int = Field(default=16384, ge=256, le=32768)
    max_reply_bytes: int = Field(default=4096, ge=256, le=8192)
    max_turns: int = Field(default=10, ge=1, le=30)
    max_steps: int = Field(default=200, ge=1, le=1000)
    max_tool_calls: int = Field(default=100, ge=1, le=300)
    max_http_attempts: int = Field(default=100, ge=1, le=300)
    max_trace_events: int = Field(default=500, ge=4, le=1000)

    @classmethod
    def from_environment(cls):
        values = {name: os.environ["NUTRIAI_ORCH_" + name.upper()]
                  for name in cls.model_fields if "NUTRIAI_ORCH_" + name.upper() in os.environ}
        try:
            return cls(**values)
        except ValidationError:
            raise OrchestrationError("invalid_configuration") from None
