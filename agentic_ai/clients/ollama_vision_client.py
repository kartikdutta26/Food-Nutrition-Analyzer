"""Isolated numeric-loopback Ollama vision transport, with no proxies/redirects.

Only the four named local API paths below are reachable. No pulls, URLs in image
fields, tools, cloud fallback, credentials, or previous conversation are sent.
"""
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from http.client import HTTPConnection, HTTPException
import json
import math
import re
import socket
from threading import Event, Timer
from time import monotonic
from urllib.parse import urlsplit

from pydantic import ValidationError

from agentic_ai.schemas.vision import VisionModelProvenance
from agentic_ai.schemas.vision_inference import PROMPT_VERSION, SYSTEM_PROMPT, RawVisionResponse
from agentic_ai.tools.image_input import ProcessedImage
from agentic_ai.vision_runtime_config import VisionRuntimeSettings
from agentic_ai.vision_runtime_errors import VisionRuntimeError


@dataclass(frozen=True, slots=True)
class LocalVisionModel:
    model_tag: str
    model_digest: str
    ollama_version: str


@dataclass(frozen=True, slots=True)
class VisionInferenceReply:
    content: str = field(repr=False)
    provenance: VisionModelProvenance


def _json_object(body, limit):
    """Reject duplicate keys, nonfinite numbers, excessive nesting and nodes."""
    try:
        if len(body) > limit:
            raise VisionRuntimeError("response_limit")
        def pairs(entries):
            result = {}
            for key, value in entries:
                if key in result:
                    raise ValueError("Duplicate key")
                result[key] = value
            return result
        def constant(_):
            raise ValueError("Nonfinite JSON")
        raw = json.loads(body, object_pairs_hook=pairs, parse_constant=constant)
        count = 0
        def scan(value, depth=0):
            nonlocal count
            count += 1
            if count > 10_000 or depth > 20:
                raise ValueError("Metadata bounds")
            if isinstance(value, dict):
                if len(value) > 256 or any(len(key) > 100 for key in value):
                    raise ValueError("Object bounds")
                for child in value.values():
                    scan(child, depth+1)
            elif isinstance(value, list):
                if len(value) > 256:
                    raise ValueError("Array bounds")
                for child in value:
                    scan(child, depth+1)
            elif isinstance(value, str) and len(value) > 65_536:
                raise ValueError("String bounds")
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Nonfinite JSON")
            elif type(value) is int and len(str(value)) > 20:
                raise ValueError("Integer bounds")
        if not isinstance(raw, dict):
            raise ValueError("Object required")
        scan(raw)
        return raw
    except VisionRuntimeError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise VisionRuntimeError("invalid_response") from None


class OllamaVisionClient:
    def __init__(self, settings=None):
        try:
            self.settings = VisionRuntimeSettings() if settings is None else VisionRuntimeSettings.model_validate(settings)
        except (ValidationError, ValueError, TypeError):
            raise VisionRuntimeError("invalid_configuration") from None

    def _request(self, method, path, payload, deadline):
        if (method, path) not in {("GET", "/api/version"), ("GET", "/api/tags"),
                                  ("POST", "/api/show"), ("POST", "/api/chat")}:
            raise VisionRuntimeError("invalid_configuration")
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise VisionRuntimeError("timeout")
        origin = urlsplit(self.settings.base_url)
        connection = HTTPConnection(origin.hostname, origin.port, timeout=remaining)
        expired, connected_socket = Event(), None
        def abort():
            expired.set()
            if connected_socket is not None:
                try:
                    connected_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            connection.close()
        timer = Timer(remaining, abort)
        timer.daemon = True
        body = None if payload is None else json.dumps(payload, ensure_ascii=True, allow_nan=False,
                                                        separators=(",", ":")).encode("utf-8")
        if body is not None and len(body) > 6_291_456:
            raise VisionRuntimeError("invalid_image")
        timer.start()
        try:
            # Direct HTTPConnection ignores HTTP_PROXY/ALL_PROXY and never follows redirects.
            connection.connect()
            connected_socket = connection.sock
            if expired.is_set():
                raise VisionRuntimeError("timeout")
            connection.request(method, path, body=body,
                               headers={"Content-Type": "application/json", "Accept": "application/json"})
            with connection.getresponse() as response:
                if response.status != 200:
                    code = "model_missing" if response.status == 404 and path in {"/api/show", "/api/chat"} else "service_unavailable"
                    raise VisionRuntimeError(code)
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise VisionRuntimeError("invalid_response")
                length = response.getheader("Content-Length")
                if length is not None and (not length.isascii() or not length.isdigit()):
                    raise VisionRuntimeError("invalid_response")
                if length is not None and int(length) > self.settings.max_response_bytes:
                    raise VisionRuntimeError("response_limit")
                chunks, size = [], 0
                while True:
                    if expired.is_set() or monotonic() >= deadline:
                        raise VisionRuntimeError("timeout")
                    chunk = response.read1(min(65_536, self.settings.max_response_bytes + 1-size))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > self.settings.max_response_bytes:
                        raise VisionRuntimeError("response_limit")
                if length is not None and size != int(length):
                    raise VisionRuntimeError("invalid_response")
            if expired.is_set() or monotonic() >= deadline:
                raise VisionRuntimeError("timeout")
            value = _json_object(b"".join(chunks), self.settings.max_response_bytes)
            if value.get("error"):
                raise VisionRuntimeError("invalid_response")
            return value
        except VisionRuntimeError:
            if expired.is_set():
                raise VisionRuntimeError("timeout") from None
            raise
        except TimeoutError:
            raise VisionRuntimeError("timeout") from None
        except (OSError, HTTPException, ValueError):
            code = "timeout" if expired.is_set() or monotonic() >= deadline else "service_unavailable"
            raise VisionRuntimeError(code) from None
        finally:
            timer.cancel()
            connection.close()

    def _installed_digest(self, deadline):
        response = self._request("GET", "/api/tags", None, deadline)
        models = response.get("models")
        if not isinstance(models, list):
            raise VisionRuntimeError("invalid_response")
        matches = [entry for entry in models if isinstance(entry, dict)
                   and entry.get("name", entry.get("model")) == self.settings.model]
        if not matches:
            raise VisionRuntimeError("model_missing")
        if len(matches) != 1:
            raise VisionRuntimeError("invalid_response")
        entry = matches[0]
        if "model" in entry and entry["model"] != self.settings.model:
            raise VisionRuntimeError("invalid_response")
        if any(entry.get(key) for key in ("remote_host", "remote_model")):
            raise VisionRuntimeError("unsafe_model")
        digest = entry.get("digest")
        if not isinstance(digest, str) or re.fullmatch(r"[a-f0-9]{64}", digest) is None:
            raise VisionRuntimeError("invalid_response")
        return "sha256:" + digest

    def _check_ready(self, deadline):
        version = self._request("GET", "/api/version", None, deadline).get("version")
        if not isinstance(version, str) or re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[a-z0-9.-]{1,32})?", version) is None:
            raise VisionRuntimeError("invalid_response")
        if tuple(map(int, version.split("-")[0].split("."))) < (0, 12, 7):
            raise VisionRuntimeError("unsupported_runtime")
        digest = self._installed_digest(deadline)
        details = self._request("POST", "/api/show", {"model": self.settings.model, "verbose": False}, deadline)
        if any(details.get(key) for key in ("remote_host", "remote_model")):
            raise VisionRuntimeError("unsafe_model")
        capabilities = details.get("capabilities")
        if not isinstance(capabilities, list) or "vision" not in capabilities or "completion" not in capabilities:
            raise VisionRuntimeError("vision_unavailable")
        return LocalVisionModel(self.settings.model, digest, version)

    def check_ready(self):
        """Read local metadata only. Does not download, load or run a model."""
        try:
            return self._check_ready(monotonic() + self.settings.timeout_seconds)
        except VisionRuntimeError:
            raise
        except Exception:
            raise VisionRuntimeError("inference_failed") from None

    def analyze(self, image):
        """Use a fresh single-image request; never include the source filename."""
        try:
            if (not isinstance(image, ProcessedImage) or type(image.processed_bytes) is not bytes
                    or not 0 < len(image.processed_bytes) <= 4_194_304
                    or not image.processed_bytes.startswith(b"\x89PNG\r\n\x1a\n")
                    or image.preprocessing.media_type != "image/png"
                    or hashlib.sha256(image.processed_bytes).hexdigest() != image.preprocessing.processed_sha256):
                raise VisionRuntimeError("invalid_image")
            deadline = monotonic() + self.settings.timeout_seconds
            selected = self._check_ready(deadline)
            schema = RawVisionResponse.model_json_schema()
            payload = {"model": self.settings.model, "stream": False, "think": False, "keep_alive": 0,
                       "format": schema, "options": {"temperature": 0, "num_ctx": self.settings.num_ctx,
                                                        "num_predict": self.settings.num_predict, "seed": self.settings.seed},
                       "messages": [{"role": "system", "content": SYSTEM_PROMPT + "\nJSON Schema:\n" + json.dumps(schema)},
                                    {"role": "user", "content": "Propose visible food identities; all require confirmation.",
                                     "images": [base64.b64encode(image.processed_bytes).decode("ascii")]}]}
            envelope = self._request("POST", "/api/chat", payload, deadline)
            message = envelope.get("message")
            if (envelope.get("error") or envelope.get("model") != selected.model_tag
                    or envelope.get("done") is not True or envelope.get("done_reason") != "stop"
                    or not isinstance(message, dict) or message.get("role") != "assistant"
                    or message.get("tool_calls") or message.get("thinking") or message.get("images")):
                raise VisionRuntimeError("invalid_response")
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise VisionRuntimeError("invalid_response")
            if len(content.encode("utf-8")) > self.settings.max_model_output_bytes:
                raise VisionRuntimeError("response_limit")
            if self._installed_digest(deadline) != selected.model_digest:
                raise VisionRuntimeError("model_changed")
            provenance = VisionModelProvenance(model_tag=selected.model_tag, model_digest=selected.model_digest,
                                               ollama_version=selected.ollama_version, prompt_version=PROMPT_VERSION,
                                               inference=self.settings.inference_configuration(),
                                               declared_at=datetime.now(timezone.utc).isoformat())
            return VisionInferenceReply(content, provenance)
        except VisionRuntimeError:
            raise
        except Exception:
            raise VisionRuntimeError("inference_failed") from None
