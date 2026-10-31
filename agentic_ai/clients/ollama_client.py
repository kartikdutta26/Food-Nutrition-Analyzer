"""Small Ollama HTTP adapter; no SDK or backend imports are required."""

import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agentic_ai.config import Settings
from agentic_ai.errors import (
    OllamaConnectionError, OllamaModelNotFoundError, OllamaResponseError,
    OllamaServiceError, OllamaTimeoutError,
)


MAX_RESPONSE_BYTES = 1_048_576


class OllamaClient:
    def __init__(self, settings: Settings, *, attempt_observer=None):
        self.settings = settings
        self.attempt_observer = attempt_observer

    def chat(self, messages: list[dict[str, str]], schema: dict) -> str:
        payload = {
            "model": self.settings.model, "messages": messages, "format": schema,
            "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": 2048, "num_ctx": 8192},
        }
        request = Request(
            self.settings.base_url + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        if self.attempt_observer is not None:
            self.attempt_observer()
        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as exc:
            exc.close()
            if exc.code == 404:
                raise OllamaModelNotFoundError(
                    "The configured model or /api/chat endpoint was not found. "
                    "Check that qwen3:4b-instruct is installed and OLLAMA_BASE_URL is correct."
                ) from exc
            raise OllamaServiceError(f"Ollama returned HTTP {exc.code}; try again later.") from exc
        except TimeoutError as exc:
            raise OllamaTimeoutError("Ollama timed out. Try again or increase OLLAMA_TIMEOUT_SECONDS.") from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise OllamaTimeoutError("Ollama timed out. Try again or increase OLLAMA_TIMEOUT_SECONDS.") from exc
            raise OllamaConnectionError("Cannot connect to Ollama. Start Ollama and check OLLAMA_BASE_URL.") from exc
        except (OSError, HTTPException) as exc:
            raise OllamaConnectionError("The connection to Ollama failed or was interrupted.") from exc
        if len(body) > MAX_RESPONSE_BYTES:
            raise OllamaResponseError("Ollama returned an oversized response.")
        try:
            envelope = json.loads(body)
        except (ValueError, UnicodeError) as exc:
            raise OllamaResponseError("Ollama returned unreadable JSON.") from exc
        if not isinstance(envelope, dict) or envelope.get("error"):
            raise OllamaResponseError("Ollama returned an invalid response envelope.")
        if envelope.get("done") is not True or envelope.get("done_reason") == "length":
            raise OllamaResponseError("Ollama did not finish the extraction; shorten the description.")
        message = envelope.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise OllamaResponseError("Ollama returned no assistant message.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError("Ollama returned an empty food extraction.")
        return content
