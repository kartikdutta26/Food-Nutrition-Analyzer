"""Scripted loopback transport tests. No model inference or network access."""
import base64
from dataclasses import replace
from io import BytesIO
import json
from threading import Event
from time import monotonic

import pytest
from pydantic import ValidationError

from agentic_ai.clients import ollama_vision_client as module
from agentic_ai.clients.ollama_vision_client import OllamaVisionClient, _json_object
from agentic_ai.schemas.vision_inference import RawVisionResponse
from agentic_ai.tools.image_input import preprocess_image
from agentic_ai.vision_runtime_config import VisionRuntimeSettings
from agentic_ai.vision_runtime_errors import VisionRuntimeError
from .test_image_input import write_image


RAW = {"status": "needs_confirmation", "groups": [{"location": "center", "labels": ["banana"],
       "uncertainty_reasons": []}], "uncertainty_reasons": ["identity_unconfirmed"]}
DIGEST = "a" * 64


def envelope(content=None):
    return {"model": "qwen3-vl:2b", "done": True, "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(RAW) if content is None else content}}


def responses(chat=None):
    tags = {"models": [{"name": "qwen3-vl:2b", "model": "qwen3-vl:2b", "digest": DIGEST}]}
    return [{"version": "0.40.16"}, tags, {"capabilities": ["completion", "vision"]},
            envelope() if chat is None else chat, tags]


def transport(monkeypatch, replies):
    """Patch the connection itself; existing vision fixture blocks real sockets."""
    calls = []
    queue = iter(replies)
    class Response:
        def __init__(self, value):
            if isinstance(value, Exception):
                raise value
            if isinstance(value, dict) and "_status" in value:
                self.status = value["_status"]
                self.headers = value.get("_headers", {})
                self.data = BytesIO(value.get("_body", b""))
            else:
                self.status, self.headers = 200, {}
                self.data = BytesIO(value if isinstance(value, bytes) else json.dumps(value).encode())
        def getheader(self, key, default=None):
            return self.headers.get(key, default)
        def read1(self, limit):
            return self.data.read1(limit)
        def __enter__(self): return self
        def __exit__(self, *args): self.data.close()
    class Connection:
        def __init__(self, host, port, timeout):
            self.host, self.port, self.timeout, self.sock = host, port, timeout, None
        def connect(self): self.sock = self
        def request(self, method, path, body, headers):
            calls.append({"host": self.host, "port": self.port, "timeout": self.timeout,
                          "method": method, "path": path,
                          "payload": json.loads(body) if body else None, "headers": headers})
        def getresponse(self): return Response(next(queue))
        def shutdown(self, how): pass
        def close(self): pass
    monkeypatch.setattr(module, "HTTPConnection", Connection)
    return calls


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://[::1]:11434/", "http://127.0.0.2:11435"])
def test_loopback_origins_accepted(url):
    assert VisionRuntimeSettings(base_url=url).base_url.startswith("http://")


@pytest.mark.parametrize("url", [
    "https://127.0.0.1:11434", "http://localhost:11434", "http://example.com", "http://0.0.0.0",
    "http://192.168.1.2:11434", "http://169.254.169.254", "http://127.0.0.1.evil.invalid",
    "http://2130706433", "http://0177.0.0.1", "http://127.1", "http://[::ffff:127.0.0.1]",
    "http://user:pass@127.0.0.1", "http://127.0.0.1/path", "http://127.0.0.1?x=1", "http://127.0.0.1?",
    "http://127.0.0.1#fragment", "http://127.0.0.1#", "http://127.0.0.1:0", "http://127.0.0.1:65536",
    "http://127.0.0.1:", "http://127.0.0.1\n", " http://127.0.0.1", "file:///image.png",
])
def test_remote_ambiguous_and_credential_origins_rejected(url):
    with pytest.raises(ValidationError): VisionRuntimeSettings(base_url=url)


@pytest.mark.parametrize("kwargs", [
    {"model": "qwen3-vl:235b-cloud"}, {"model": "qwen3:4b-instruct"}, {"timeout_seconds": 181},
    {"timeout_seconds": 0}, {"timeout_seconds": True}, {"max_response_bytes": 1_048_577},
    {"max_model_output_bytes": 32769}, {"num_ctx": 4097}, {"num_predict": 2049},
    {"seed": -1}, {"cloud_fallback": True}, {"tools": []},
])
def test_configuration_is_strict_and_bounded(kwargs):
    with pytest.raises(ValidationError): VisionRuntimeSettings(**kwargs)


def test_model_construct_cannot_bypass_configuration():
    forged = VisionRuntimeSettings.model_construct(base_url="http://remote.invalid")
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient(forged)
    assert error.value.code == "invalid_configuration"


def test_complete_fresh_request_uses_processed_bytes_only(tmp_path, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://remote.invalid:8080")
    monkeypatch.setenv("ALL_PROXY", "http://remote.invalid:8080")
    calls = transport(monkeypatch, responses())
    path = write_image(tmp_path)
    image = preprocess_image(path)
    reply = OllamaVisionClient().analyze(image)
    assert reply.provenance.model_digest == "sha256:" + DIGEST
    assert reply.provenance.prompt_version == "vision-food-v1"
    assert reply.provenance.inference.temperature == 0
    assert reply.provenance.inference.seed == 0
    assert all(call["host"] == "127.0.0.1" and call["port"] == 11434 for call in calls)
    assert [call["path"] for call in calls] == ["/api/version", "/api/tags", "/api/show", "/api/chat", "/api/tags"]
    request = calls[3]["payload"]
    assert request["stream"] is False and request["think"] is False and request["keep_alive"] == 0
    assert "tools" not in request
    assert request["format"] == RawVisionResponse.model_json_schema()
    assert len(request["messages"]) == 2
    assert base64.b64decode(request["messages"][1]["images"][0]) == image.processed_bytes
    assert str(path) not in json.dumps(request)
    assert "content=" not in repr(reply)
    assert all(0 < call["timeout"] <= 120 for call in calls)
    assert [c["timeout"] for c in calls] == sorted((c["timeout"] for c in calls), reverse=True)


def test_missing_model_does_not_reach_show_or_chat(monkeypatch):
    calls = transport(monkeypatch, [{"version": "0.40.16"}, {"models": []}])
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().check_ready()
    assert error.value.code == "model_missing"
    assert [c["path"] for c in calls] == ["/api/version", "/api/tags"]


@pytest.mark.parametrize("part,value,code", [
    (0, {"version": "0.12.6"}, "unsupported_runtime"), (0, {"version": "bad"}, "invalid_response"),
    (1, {"models": [{"name": "qwen3-vl:2b", "digest": "bad"}]}, "invalid_response"),
    (1, {"models": [{"name": "qwen3-vl:2b", "digest": DIGEST, "remote_host": "cloud.invalid"}]}, "unsafe_model"),
    (1, {"models": [{"name": "qwen3-vl:2b", "model": "other", "digest": DIGEST}]}, "invalid_response"),
    (1, {"models": None}, "invalid_response"),
    (2, {"capabilities": ["completion"]}, "vision_unavailable"),
    (2, {"capabilities": ["vision"]}, "vision_unavailable"),
    (2, {"capabilities": ["completion", "vision"], "remote_model": "other-cloud"}, "unsafe_model"),
])
def test_model_readiness_safeguards(monkeypatch, part, value, code):
    values = responses(); values[part] = value
    calls = transport(monkeypatch, values)
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().check_ready()
    assert error.value.code == code
    assert not any(c["path"] == "/api/chat" for c in calls)


def test_duplicate_model_entries_rejected(monkeypatch):
    values = responses()
    values[1] = {"models": [{"name": "qwen3-vl:2b", "digest": DIGEST}]*2}
    transport(monkeypatch, values)
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().check_ready()
    assert error.value.code == "invalid_response"


def test_error_cannot_be_hidden_in_valid_metadata(monkeypatch):
    transport(monkeypatch, [{"version": "0.40.16", "error": "PRIVATE"}])
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().check_ready()
    assert error.value.code == "invalid_response" and "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("change", ["model", "done", "done_reason", "error", "role", "content", "tool_calls", "thinking", "images"])
def test_untrusted_inference_envelope_rejected(tmp_path, monkeypatch, change):
    value = envelope()
    if change == "model": value["model"] = "other:2b"
    elif change == "done": value["done"] = 1
    elif change == "done_reason": value["done_reason"] = "length"
    elif change == "error": value["error"] = "PRIVATE_MODEL_ERROR"
    else: value["message"][change] = {"role": "user", "content": "", "tool_calls": [{}], "thinking": "PRIVATE", "images": ["PRIVATE"]}[change]
    transport(monkeypatch, responses(value))
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().analyze(preprocess_image(write_image(tmp_path)))
    assert error.value.code == "invalid_response"
    assert "PRIVATE" not in str(error.value)


def test_tag_change_after_inference_is_rejected(tmp_path, monkeypatch):
    values = responses(); values[-1] = {"models": [{"name": "qwen3-vl:2b", "digest": "b"*64}]}
    transport(monkeypatch, values)
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().analyze(preprocess_image(write_image(tmp_path)))
    assert error.value.code == "model_changed"


@pytest.mark.parametrize("value", [b'{"version":"a","version":"b"}', b'{"n":NaN}', b'{"n":1e999}', b'[]', b'null', bytes([255]), b'{' + b'"a":['*25 + b'0' + b']'*25+b'}'])
def test_strict_json_envelopes(value):
    with pytest.raises(VisionRuntimeError): _json_object(value, 1_048_576)


@pytest.mark.parametrize("response,code", [
    ({"_status": 302, "_headers": {"Location": "https://remote.invalid"}}, "service_unavailable"),
    ({"_status": 401}, "service_unavailable"),
    ({"_status": 500, "_body": b'PRIVATE'}, "service_unavailable"),
    ({"_status": 200, "_headers": {"Content-Length": "1048577"}}, "response_limit"),
    ({"_status": 200, "_headers": {"Content-Length": "bad"}}, "invalid_response"),
    ({"_status": 200, "_headers": {"Content-Length": "99"}, "_body": b'{}'}, "invalid_response"),
    ({"_status": 200, "_headers": {"Content-Encoding": "gzip"}}, "invalid_response"),
    (TimeoutError("PRIVATE"), "timeout"), (OSError("PRIVATE"), "service_unavailable"),
])
def test_bounded_transport_errors(monkeypatch, response, code):
    calls = transport(monkeypatch, [response])
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().check_ready()
    assert error.value.code == code and "PRIVATE" not in str(error.value)
    assert len(calls) == 1


def test_body_cap_without_content_length(monkeypatch):
    transport(monkeypatch, [b"x"*1025])
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient(VisionRuntimeSettings(max_response_bytes=1024)).check_ready()
    assert error.value.code == "response_limit"


def test_output_content_cap(tmp_path, monkeypatch):
    transport(monkeypatch, responses(envelope("x"*1025)))
    with pytest.raises(VisionRuntimeError) as error:
        OllamaVisionClient(VisionRuntimeSettings(max_model_output_bytes=1024)).analyze(preprocess_image(write_image(tmp_path)))
    assert error.value.code == "response_limit"


def test_mutated_processed_bytes_rejected_without_http(tmp_path, monkeypatch):
    calls = transport(monkeypatch, [])
    image = preprocess_image(write_image(tmp_path))
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient().analyze(replace(image, processed_bytes=image.processed_bytes+b"extra"))
    assert error.value.code == "invalid_image" and not calls


def test_total_deadline_interrupts_blocked_headers(monkeypatch):
    released = Event()
    class Connection:
        sock = None
        def __init__(self, *args, **kwargs): pass
        def connect(self): self.sock = self
        def request(self, *args, **kwargs): pass
        def getresponse(self):
            released.wait(3)
            raise OSError("PRIVATE")
        def shutdown(self, how): released.set()
        def close(self): released.set()
    monkeypatch.setattr(module, "HTTPConnection", Connection)
    started = monotonic()
    with pytest.raises(VisionRuntimeError) as error: OllamaVisionClient(VisionRuntimeSettings(timeout_seconds=1)).check_ready()
    assert error.value.code == "timeout" and released.is_set()
    assert monotonic()-started < 2.5
