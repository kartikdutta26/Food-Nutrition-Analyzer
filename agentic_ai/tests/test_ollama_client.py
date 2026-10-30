import io
import json
from http.client import IncompleteRead
from urllib.error import HTTPError, URLError

import pytest

from agentic_ai.clients import ollama_client
from agentic_ai.clients.ollama_client import OllamaClient
from agentic_ai.config import Settings
from agentic_ai.errors import (
    OllamaConnectionError, OllamaModelNotFoundError, OllamaResponseError,
    OllamaServiceError, OllamaTimeoutError,
)


def envelope(**changes):
    return {"done": True, "done_reason": "stop", "message": {
        "role": "assistant", "content": '{"foods": []}',
    }, **changes}


def respond(monkeypatch, payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    monkeypatch.setattr(ollama_client, "urlopen", lambda *args, **kwargs: io.BytesIO(body))


def test_http_request_uses_installed_model_and_structured_schema(monkeypatch):
    seen = {}
    def open_request(request, timeout):
        seen.update(url=request.full_url, method=request.method, timeout=timeout,
                    payload=json.loads(request.data))
        return io.BytesIO(json.dumps(envelope()).encode())
    monkeypatch.setattr(ollama_client, "urlopen", open_request)
    schema = {"type": "object"}
    assert OllamaClient(Settings()).chat([], schema) == '{"foods": []}'
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["method"] == "POST"
    assert seen["timeout"] == 120
    assert seen["payload"]["model"] == "qwen3:4b-instruct"
    assert seen["payload"]["format"] == schema
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["think"] is False


@pytest.mark.parametrize(("failure", "expected"), [
    (URLError(ConnectionRefusedError()), OllamaConnectionError),
    (TimeoutError(), OllamaTimeoutError),
    (URLError(TimeoutError()), OllamaTimeoutError),
    (OSError(), OllamaConnectionError),
    (IncompleteRead(b"partial"), OllamaConnectionError),
    (HTTPError("http://localhost", 404, "missing", {}, None), OllamaModelNotFoundError),
    (HTTPError("http://localhost", 503, "private upstream detail", {}, None), OllamaServiceError),
])
def test_transport_failures_have_stable_errors(monkeypatch, failure, expected):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(ollama_client, "urlopen", fail)
    with pytest.raises(expected) as captured:
        OllamaClient(Settings()).chat([], {})
    assert "private upstream detail" not in str(captured.value)


@pytest.mark.parametrize("payload", [
    b"not JSON", b"\xff", [], {"error": "failed"}, envelope(done=False),
    envelope(done_reason="length"), envelope(message=None), envelope(message={}),
    envelope(message={"role": "assistant", "content": ""}),
    envelope(message={"role": "assistant", "content": []}),
    envelope(message={"role": "user", "content": "{}"}),
])
def test_malformed_or_incomplete_responses_are_rejected(monkeypatch, payload):
    respond(monkeypatch, payload)
    with pytest.raises(OllamaResponseError):
        OllamaClient(Settings()).chat([], {})


def test_oversized_response_is_rejected(monkeypatch):
    respond(monkeypatch, b"x" * (ollama_client.MAX_RESPONSE_BYTES + 1))
    with pytest.raises(OllamaResponseError, match="oversized"):
        OllamaClient(Settings()).chat([], {})
