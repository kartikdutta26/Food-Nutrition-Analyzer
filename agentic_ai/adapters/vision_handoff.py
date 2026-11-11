"""M5.1: validate hypotheses and explicit confirmation, without invoking M3.

A caller must supply a trusted recognition record and explicit user confirmation.
A fingerprint binds metadata; it is not authentication or proof of user intent.
"""
from pydantic import ValidationError
from agentic_ai.schemas.orchestration import StartRequest
from agentic_ai.schemas.vision import (
    ImageFoodRecognitionResult, ImageMealConfirmation, ConfirmedImageMeal,
    canonical_result_sha256,
)
from agentic_ai.vision_config import VisionContractSettings
from agentic_ai.vision_errors import VisionContractError
from agentic_ai.vision_validation import parse_metadata, safe_boundary, serialized_metadata_size


def _settings(settings):
    if settings is None:
        return VisionContractSettings()
    try:
        return VisionContractSettings.model_validate_json(settings.model_dump_json(warnings=False))
    except (AttributeError, ValidationError, ValueError, TypeError):
        raise VisionContractError("invalid_handoff") from None


def _result_bounds(result, settings):
    if len(result.groups) > settings.max_groups or any(len(group.candidates) > settings.max_candidates_per_group for group in result.groups):
        raise VisionContractError("input_limit")


@safe_boundary
def validate_recognition_result(value, *, settings=None):
    settings = _settings(settings)
    result = parse_metadata(value, ImageFoodRecognitionResult, settings,
        limit=settings.max_result_bytes, code="invalid_recognition")
    _result_bounds(result, settings)
    if serialized_metadata_size(result) > settings.max_result_bytes:
        raise VisionContractError("output_limit")
    return result


@safe_boundary
def recognition_fingerprint(value, *, settings=None):
    return canonical_result_sha256(validate_recognition_result(value, settings=settings))


@safe_boundary
def prepare_confirmation(result, confirmation, *, settings=None):
    settings = _settings(settings)
    recognized = validate_recognition_result(result, settings=settings)
    confirmed = parse_metadata(confirmation, ImageMealConfirmation, settings,
        limit=settings.max_confirmation_bytes, code="invalid_confirmation")
    if len(confirmed.confirmed_meal_text) > settings.max_meal_text_chars:
        raise VisionContractError("input_limit")
    raw = {"recognition":recognized.model_dump(mode="json"),
           "confirmation":confirmed.model_dump(mode="json"),
           "result_sha256":canonical_result_sha256(recognized)}
    return _validated_handoff(raw, settings)


def _validated_handoff(value, settings):
    handoff = parse_metadata(value, ConfirmedImageMeal, settings,
        limit=settings.max_handoff_bytes, code="invalid_handoff")
    _result_bounds(handoff.recognition, settings)
    if (serialized_metadata_size(handoff.recognition) > settings.max_result_bytes
        or serialized_metadata_size(handoff.confirmation) > settings.max_confirmation_bytes
        or len(handoff.confirmation.confirmed_meal_text) > settings.max_meal_text_chars):
        raise VisionContractError("input_limit")
    if serialized_metadata_size(handoff) > settings.max_handoff_bytes:
        raise VisionContractError("output_limit")
    return handoff


@safe_boundary
def to_m3_start_request(handoff, *, provider="snapshot", settings=None):
    """Return a fresh existing M3 request; never start a session or infer text.

    The existing caller remains responsible for owner identity, user interaction,
    session creation and retaining the separate image-hypothesis audit record.
    """
    settings = _settings(settings)
    confirmed = _validated_handoff(handoff, settings)
    try:
        request = StartRequest.model_validate({"text":confirmed.confirmation.confirmed_meal_text, "provider":provider})
        if len(request.model_dump_json().encode("utf-8")) > settings.max_m3_request_bytes:
            raise VisionContractError("output_limit")
        return request
    except (ValidationError, ValueError, TypeError):
        raise VisionContractError("invalid_handoff") from None
