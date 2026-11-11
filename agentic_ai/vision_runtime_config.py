"""M5.3 settings are explicit, local-only, independent of M1 environment files."""
import ipaddress
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal

from agentic_ai.schemas.vision import VisionInferenceConfiguration


class VisionRuntimeSettings(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid",
                             revalidate_instances="always", hide_input_in_errors=True)
    base_url: str = "http://127.0.0.1:11434"
    model: Literal["qwen3-vl:2b"] = "qwen3-vl:2b"
    timeout_seconds: int = Field(default=120, ge=1, le=180)
    max_response_bytes: int = Field(default=1_048_576, ge=1024, le=1_048_576)
    max_model_output_bytes: int = Field(default=32_768, ge=1024, le=32_768)
    num_ctx: int = Field(default=4096, ge=1024, le=4096)
    num_predict: int = Field(default=1024, ge=64, le=2048)
    seed: int = Field(default=0, ge=0, le=2_147_483_647)

    @field_validator("base_url")
    @classmethod
    def loopback_http_only(cls, value):
        if any(ord(char) < 33 or ord(char) > 126 for char in value):
            raise ValueError("Use a numeric loopback HTTP origin")
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                or "?" in value or "#" in value):
            raise ValueError("Use a numeric loopback HTTP origin")
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
            port = parsed.port
        except ValueError:
            raise ValueError("Use a numeric loopback HTTP origin") from None
        if (not address.is_loopback or (address.version == 6 and address != ipaddress.IPv6Address("::1"))
                or port == 0 or parsed.netloc.endswith(":")):
            raise ValueError("Use a numeric loopback HTTP origin")
        host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        return f"http://{host}:{port or 11434}"

    def inference_configuration(self):
        return VisionInferenceConfiguration(temperature=0, num_ctx=self.num_ctx,
                                            num_predict=self.num_predict, seed=self.seed)
