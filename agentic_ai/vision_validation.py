"""Bounded metadata parsing; no image bytes, paths or inference are accepted."""
import json
import math
from functools import wraps
from pydantic import BaseModel, ValidationError
from agentic_ai.vision_errors import VisionContractError


def _scan(value, settings, *, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    if count[0] > settings.max_nodes or depth > settings.max_depth:
        raise VisionContractError("input_limit")
    if isinstance(value, dict):
        if len(value) > 256:
            raise VisionContractError("input_limit")
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 100:
                raise VisionContractError("input_limit")
            _scan(child, settings, depth=depth+1, count=count)
    elif isinstance(value, (list, tuple)):
        if len(value) > 256:
            raise VisionContractError("input_limit")
        for child in value:
            _scan(child, settings, depth=depth+1, count=count)
    elif isinstance(value, str):
        if len(value) > 4000:
            raise VisionContractError("input_limit")
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int):
        if len(str(value)) > 20:
            raise VisionContractError("input_limit")
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Nonfinite metadata")
    else:
        raise ValueError("Unsupported metadata")


def parse_metadata(value, model, settings, *, limit, code):
    try:
        if isinstance(value, (str, bytes)):
            if len(value.encode("utf-8") if isinstance(value, str) else value) > limit:
                raise VisionContractError("input_limit")
            def pairs(entries):
                result = {}
                for name, child in entries:
                    if name in result:
                        raise ValueError("Duplicate key")
                    result[name] = child
                return result
            def constant(_):
                raise ValueError("Nonfinite JSON")
            raw = json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
        else:
            raw = value.model_dump(mode="python", warnings=False) if isinstance(value, BaseModel) else value
        _scan(raw, settings)
        encoded = json.dumps(raw, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > limit:
            raise VisionContractError("input_limit")
        return model.model_validate_json(encoded)
    except VisionContractError:
        raise
    except (ValidationError, ValueError, TypeError, OverflowError, RecursionError):
        raise VisionContractError(code) from None


def serialized_metadata_size(model):
    """Conservative canonical ASCII JSON size, including all default fields."""
    return len(json.dumps(model.model_dump(mode="json"), ensure_ascii=True,
                          separators=(",", ":")).encode("utf-8"))


def safe_boundary(operation):
    """Do not expose unexpected implementation/dependency exceptions to callers."""
    @wraps(operation)
    def wrapped(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except VisionContractError:
            raise
        except Exception:
            raise VisionContractError("handoff_failed") from None
    return wrapped
