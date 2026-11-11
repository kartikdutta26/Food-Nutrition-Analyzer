"""M5.1 v1 contracts for declared hypotheses, not actual image recognition.

No field proves that inference occurred or that an image contains a named food.
There are no image-derived amounts, nutrition values, USDA IDs or probabilities.
"""
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from agentic_ai.vision_errors import VisionContractError

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,31}$", max_length=32)]
QuestionIdentifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,99}$", max_length=100)]
Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$", max_length=64)]
MediaType = Literal["image/jpeg", "image/png"]
UncertaintyReason = Literal[
    "identity_unconfirmed", "unknown_preparation", "multiple_foods", "ambiguous_identity",
    "mixed_dish", "occluded", "blurred", "poor_lighting", "unrecognized_content", "no_food_identified",
]
HARD_UNCERTAINTY = {"ambiguous_identity", "mixed_dish", "occluded", "blurred", "poor_lighting", "unrecognized_content"}
QUESTION_TEXT = {
    "confirm_food_identity": "Confirm or correct this food identity, or exclude this group. Alternatives are hypotheses, not separate foods.",
    "confirm_preparation": "Confirm preparation only if you know it; otherwise leave it unknown for later clarification.",
    "acknowledge_unknown_amount": "The image establishes no consumed amount. Supply an amount only if known; otherwise allow M3 to clarify it.",
    "confirm_food_presence": "Confirm whether food is present. You may provide your own description even when the model identified none.",
    "confirm_meal_description": "Explicitly confirm your own meal description. No hypothesis will be inserted into it automatically.",
}
LIMITATIONS = (
    "unverified_visual_hypotheses", "amounts_and_nutrients_unknown", "not_ingredient_or_allergen_verification",
    "metadata_is_not_inference_attestation", "user_confirmation_required",
)


def checked_text(value, *, multiline=False):
    if not value.strip() or (not multiline and value != value.strip()):
        raise ValueError("Text must be meaningful and bounded")
    for char in value:
        if unicodedata.category(char) in {"Cc", "Cf", "Cs"} and not (multiline and char in "\t\n\r"):
            raise ValueError("Unsupported control character")
    return value


class VisionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False,
                             revalidate_instances="always", hide_input_in_errors=True)


class FoodHypothesis(VisionModel):
    candidate_id: Identifier
    rank: int = Field(ge=1, le=3)
    label: str = Field(min_length=1, max_length=120)
    # Explicit nulls are permitted, but not even a numeric zero is evidence here.
    quantity: None = None
    edible_grams: None = None
    nutrition: None = None
    fdc_id: None = None
    confidence: None = None

    @field_validator("label")
    @classmethod
    def identity_only(cls, value):
        checked_text(value)
        normalized = unicodedata.normalize("NFKC", value)
        if any(char.isnumeric() for char in normalized):
            raise ValueError("Food labels cannot contain numeric claims")
        if any(not (unicodedata.category(char)[0] in {"L", "M"} or char in " -'()") for char in normalized):
            raise ValueError("Use a plain food identity label")
        forbidden = r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|dozen|couple|few|some|several|half|quarter|grams?|kilograms?|milligrams?|kcal|calories?|percent(?:age)?|confidence|servings?|fdc|usda)\b"
        if re.search(forbidden, normalized, re.I) or not any(char.isalpha() for char in normalized):
            raise ValueError("Food labels cannot contain amounts or numeric evidence claims")
        return value


class CandidateFoodGroup(VisionModel):
    group_id: Identifier
    location: Literal["unknown", "top_left", "top", "top_right", "left", "center", "right", "bottom_left", "bottom", "bottom_right"] = "unknown"
    candidates: tuple[FoodHypothesis, ...] = Field(min_length=1, max_length=3)
    uncertainty_reasons: tuple[UncertaintyReason, ...] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct_alternatives(self):
        labels = [unicodedata.normalize("NFKC", c.label).casefold() for c in self.candidates]
        if len(labels) != len(set(labels)) or [c.rank for c in self.candidates] != list(range(1, len(labels)+1)):
            raise ValueError("Alternatives must be distinct and ranked consecutively")
        if len(set(self.uncertainty_reasons)) != len(self.uncertainty_reasons) or "identity_unconfirmed" not in self.uncertainty_reasons or "no_food_identified" in self.uncertainty_reasons:
            raise ValueError("A candidate group must declare unconfirmed identity")
        return self


class ImageReference(VisionModel):
    image_id: Identifier
    original_sha256: Sha256
    media_type: MediaType
    byte_size: int = Field(ge=1, le=10_485_760)
    width: int = Field(ge=1, le=20_000)
    height: int = Field(ge=1, le=20_000)
    verification_scope: Literal["declared_metadata_only"] = "declared_metadata_only"

    @model_validator(mode="after")
    def pixel_limit(self):
        if self.width * self.height > 20_000_000:
            raise ValueError("Declared image exceeds the pixel limit")
        return self


class PreprocessingMetadata(VisionModel):
    policy_version: Literal["1.0"] = "1.0"
    processed_sha256: Sha256
    media_type: MediaType
    width: int = Field(ge=1, le=1024)
    height: int = Field(ge=1, le=1024)
    original_exif_orientation: int = Field(ge=1, le=8)
    metadata_removed: bool
    color_mode: Literal["RGB"] = "RGB"
    resize_policy: Literal["fit_no_upscale"] = "fit_no_upscale"

    @field_validator("metadata_removed")
    @classmethod
    def removal_required(cls, value):
        if value is not True:
            raise ValueError("Transmitted-image metadata must be declared removed")
        return value


class VisionInferenceConfiguration(VisionModel):
    temperature: int = Field(ge=0, le=0)
    num_ctx: int = Field(ge=1024, le=4096)
    num_predict: int = Field(ge=64, le=2048)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    stream: bool = False
    thinking: bool = False
    tool_execution: bool = False
    cloud_fallback: bool = False

    @model_validator(mode="after")
    def disabled_features(self):
        if any((self.stream, self.thinking, self.tool_execution, self.cloud_fallback)):
            raise ValueError("Only bounded local, non-tool inference is represented")
        return self


class VisionModelProvenance(VisionModel):
    provider: Literal["ollama_local"] = "ollama_local"
    model_tag: str = Field(min_length=3, max_length=160, pattern=r"^[a-z0-9][a-z0-9._/-]*:[a-z0-9][a-z0-9._-]*$")
    model_digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$", max_length=71)
    ollama_version: str = Field(pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}(?:-[a-z0-9.-]{1,32})?$", max_length=45)
    prompt_version: Identifier
    inference: VisionInferenceConfiguration
    declared_at: str = Field(min_length=1, max_length=40)
    verification_scope: Literal["declared_metadata_only"] = "declared_metadata_only"

    @field_validator("model_tag")
    @classmethod
    def local_tag(cls, value):
        if ".." in value or "cloud" in re.split(r"[:/._-]", value):
            raise ValueError("An explicit local model tag is required")
        return value

    @field_validator("declared_at")
    @classmethod
    def aware_timestamp(cls, value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Provenance time must include an offset")
        return value


class ConfirmationQuestion(VisionModel):
    question_id: QuestionIdentifier
    group_id: Identifier | None = None
    kind: Literal["confirm_food_identity", "confirm_preparation", "acknowledge_unknown_amount", "confirm_food_presence", "confirm_meal_description"]
    text: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def controlled_question(self):
        if self.text != QUESTION_TEXT[self.kind]:
            raise ValueError("Only controlled confirmation wording is supported")
        return self


def required_confirmation_questions(groups, status):
    """Pure template builder; never interpolate food labels or model prose."""
    questions = []
    for group in groups:
        for kind in ("confirm_food_identity", "confirm_preparation", "acknowledge_unknown_amount"):
            questions.append(ConfirmationQuestion(question_id=f"{group.group_id}-{kind}", group_id=group.group_id, kind=kind, text=QUESTION_TEXT[kind]))
    if not groups:
        questions.append(ConfirmationQuestion(question_id="global-food-presence", kind="confirm_food_presence", text=QUESTION_TEXT["confirm_food_presence"]))
    questions.append(ConfirmationQuestion(question_id="global-meal-description", kind="confirm_meal_description", text=QUESTION_TEXT["confirm_meal_description"]))
    return tuple(questions)


class ImageFoodRecognitionResult(VisionModel):
    schema_version: Literal["1.0"] = "1.0"
    result_id: Identifier
    revision: int = Field(ge=1, le=1_000_000_000)
    status: Literal["needs_confirmation", "uncertain", "no_food_detected"]
    confirmation_required: bool = True
    image: ImageReference
    preprocessing: PreprocessingMetadata
    model_provenance: VisionModelProvenance
    groups: tuple[CandidateFoodGroup, ...] = Field(default=(), max_length=8)
    uncertainty_reasons: tuple[UncertaintyReason, ...] = Field(min_length=1, max_length=10)
    questions: tuple[ConfirmationQuestion, ...] = Field(min_length=1, max_length=25)
    limitations: tuple[str, ...] = LIMITATIONS

    @model_validator(mode="after")
    def coherent_hypotheses(self):
        if self.confirmation_required is not True or self.limitations != LIMITATIONS:
            raise ValueError("Confirmation and declared limitations are mandatory")
        reasons = set(self.uncertainty_reasons)
        if len(reasons) != len(self.uncertainty_reasons):
            raise ValueError("Uncertainty reasons must be distinct")
        if self.status == "no_food_detected":
            if self.groups or reasons != {"no_food_identified"}:
                raise ValueError("No-food status must not contain candidate foods")
        else:
            if "no_food_identified" in reasons:
                raise ValueError("No-food reason conflicts with candidate/uncertain status")
            if self.status == "needs_confirmation" and (not self.groups or reasons & HARD_UNCERTAINTY):
                raise ValueError("Uncertain or absent candidates cannot imply ordinary confirmation")
            if self.status == "uncertain" and not reasons & HARD_UNCERTAINTY:
                raise ValueError("Uncertain status requires a declared uncertainty reason")
            if self.groups and "identity_unconfirmed" not in reasons:
                raise ValueError("Candidate identity cannot be treated as verified")
        ids = [g.group_id for g in self.groups]
        candidate_ids = [c.candidate_id for g in self.groups for c in g.candidates]
        if len(set(ids)) != len(ids) or len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("Food group and candidate references must be unique")
        if len(self.groups) > 1 and "multiple_foods" not in reasons:
            raise ValueError("Distinct food groups require multiple-food uncertainty")
        if any(set(g.uncertainty_reasons) - reasons for g in self.groups):
            raise ValueError("Group uncertainty must also be reported globally")
        if self.questions != required_confirmation_questions(self.groups, self.status):
            raise ValueError("Every current group and the meal description require confirmation")
        image, processed = self.image, self.preprocessing
        width, height = (image.height, image.width) if processed.original_exif_orientation >= 5 else (image.width, image.height)
        expected_scale = min(1, 1024 / max(width, height))
        if abs(processed.width-width*expected_scale) > 1 or abs(processed.height-height*expected_scale) > 1:
            raise ValueError("Declared preprocessing does not fit the source dimensions")
        return self


def canonical_result_sha256(result):
    """Fingerprint normalized metadata, not a signature or proof of image contents."""
    raw = json.dumps(result.model_dump(mode="json"), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class TextSpan(VisionModel):
    start: int = Field(ge=0, le=3999)
    end: int = Field(ge=1, le=4000)

    @model_validator(mode="after")
    def positive_span(self):
        if self.end <= self.start:
            raise ValueError("A text span must have positive length")
        return self


class GroupConfirmation(VisionModel):
    group_id: Identifier
    action: Literal["accept_candidate", "correct_identity", "exclude_group"]
    candidate_id: Identifier | None = None
    corrected_label: str | None = Field(default=None, min_length=1, max_length=120)
    text_span: TextSpan | None = None

    @field_validator("corrected_label")
    @classmethod
    def identity_only(cls, value):
        return FoodHypothesis.identity_only(value) if value is not None else None

    @model_validator(mode="after")
    def explicit_choice(self):
        if self.action == "accept_candidate":
            valid = self.candidate_id is not None and self.corrected_label is None and self.text_span is not None
        elif self.action == "correct_identity":
            valid = self.candidate_id is None and self.corrected_label is not None and self.text_span is not None
        else:
            valid = self.candidate_id is None and self.corrected_label is None and self.text_span is None
        if not valid:
            raise ValueError("Choose one explicit candidate, correction or exclusion")
        return self


class ImageMealConfirmation(VisionModel):
    schema_version: Literal["1.0"] = "1.0"
    expected_result_id: Identifier
    expected_revision: int = Field(ge=1, le=1_000_000_000)
    expected_image_sha256: Sha256
    expected_result_sha256: Sha256
    user_confirmed: bool
    confirmed_meal_text: str = Field(min_length=1, max_length=4000)
    acknowledged_question_ids: tuple[QuestionIdentifier, ...] = Field(min_length=1, max_length=25)
    decisions: tuple[GroupConfirmation, ...] = Field(default=(), max_length=8)

    @field_validator("confirmed_meal_text")
    @classmethod
    def meaningful_meal(cls, value):
        checked_text(value, multiline=True)
        if not any(char.isalpha() for char in value):
            raise ValueError("Provide a meal description in words")
        return value

    @model_validator(mode="after")
    def explicit_acknowledgement(self):
        if self.user_confirmed is not True:
            raise ValueError("Explicit user confirmation is required")
        if len(set(self.acknowledged_question_ids)) != len(self.acknowledged_question_ids):
            raise ValueError("Acknowledgement references must be distinct")
        return self


class ConfirmedImageMeal(VisionModel):
    schema_version: Literal["1.0"] = "1.0"
    recognition: ImageFoodRecognitionResult
    confirmation: ImageMealConfirmation
    result_sha256: Sha256
    description_origin: Literal["explicit_user_confirmation"] = "explicit_user_confirmation"
    image_contents_verified: bool = False

    @model_validator(mode="after")
    def bind_confirmed_text(self):
        result, confirmation = self.recognition, self.confirmation
        digest = canonical_result_sha256(result)
        if (self.result_sha256 != digest or confirmation.expected_result_sha256 != digest
            or confirmation.expected_result_id != result.result_id or confirmation.expected_revision != result.revision
            or confirmation.expected_image_sha256 != result.image.original_sha256):
            raise VisionContractError("stale_result")
        if self.image_contents_verified is not False:
            raise VisionContractError("confirmation_mismatch")
        if set(confirmation.acknowledged_question_ids) != {q.question_id for q in result.questions}:
            raise VisionContractError("confirmation_mismatch")
        decisions = {d.group_id:d for d in confirmation.decisions}
        if len(decisions) != len(confirmation.decisions) or set(decisions) != {g.group_id for g in result.groups}:
            raise VisionContractError("confirmation_mismatch")
        spans = []
        for group in result.groups:
            decision = decisions[group.group_id]
            if decision.action == "exclude_group":
                continue
            label = decision.corrected_label
            if decision.action == "accept_candidate":
                candidates = {c.candidate_id:c for c in group.candidates}
                if decision.candidate_id not in candidates:
                    raise VisionContractError("confirmation_mismatch")
                label = candidates[decision.candidate_id].label
            span = decision.text_span
            if span.end > len(confirmation.confirmed_meal_text):
                raise VisionContractError("confirmation_mismatch")
            meal_text = confirmation.confirmed_meal_text
            if ((span.start and re.match(r"\w", meal_text[span.start-1]) and re.match(r"\w", meal_text[span.start]))
                or (span.end < len(meal_text) and re.match(r"\w", meal_text[span.end-1]) and re.match(r"\w", meal_text[span.end]))):
                raise VisionContractError("confirmation_mismatch")
            quoted = meal_text[span.start:span.end]
            quoted = unicodedata.normalize("NFKC", quoted).casefold()
            label = unicodedata.normalize("NFKC", label).casefold()
            if not re.search(r"(?<!\w)"+re.escape(label)+r"(?!\w)", quoted):
                raise VisionContractError("confirmation_mismatch")
            spans.append((span.start, span.end))
        spans.sort()
        if any(right[0] < left[1] for left, right in zip(spans, spans[1:])):
            raise VisionContractError("confirmation_mismatch")
        return self
