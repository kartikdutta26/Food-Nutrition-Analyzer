# M5.1: Food image recognition contracts and safe confirmation handoff

M5.1 implements **metadata contracts and a confirmation boundary only**. It does not decode an image, load a model, call Ollama, recognize food, fetch USDA data, or start an M3 session. No real image-recognition accuracy or performance has been tested or claimed by this stage.

A future vision agent may propose likely food identities. A photograph does not establish what was consumed, edible grams, hidden ingredients, preparation, nutrition, allergens or dietary suitability. All image hypotheses remain unverified, including after a person confirms their own meal description.

## Public API

```python
from agentic_ai.adapters.vision_handoff import (
    validate_recognition_result,
    recognition_fingerprint,
    prepare_confirmation,
    to_m3_start_request,
)
from agentic_ai.vision_errors import VisionContractError

# declared_result_json is supplied by a future trusted vision adapter.
# M5.1 does not generate it or attest that its metadata describes a real inference.
result = validate_recognition_result(declared_result_json)
digest = recognition_fingerprint(result)

# This example is explicit user input, not an amount inferred from an image.
confirmation = {
    "expected_result_id": result.result_id,
    "expected_revision": result.revision,
    "expected_image_sha256": result.image.original_sha256,
    "expected_result_sha256": digest,
    "user_confirmed": True,
    "confirmed_meal_text": "100 g banana",
    "acknowledged_question_ids": [q.question_id for q in result.questions],
    "decisions": [{
        "group_id": "group-a",
        "action": "accept_candidate",
        "candidate_id": "candidate-a",
        "text_span": {"start": 0, "end": 12},
    }],
}
# Example IDs/label must exist in the supplied result. An application must collect
# actual explicit confirmation; it must not automatically accept all questions.
handoff = prepare_confirmation(result, confirmation)
request = to_m3_start_request(handoff, provider="snapshot")

# Only the calling application can choose to execute this separate operation:
# session = existing_orchestrator.start(request, owner=trusted_owner)
```

The four adapter functions accept JSON-shaped dictionaries, JSON strings/bytes or Pydantic instances. They revalidate nested instances, including mutated or model-constructed objects, and return detached validated objects. Callers must use these bounded entry points for untrusted data rather than raw Pydantic constructors. `model_dump_json()` produces a serializable audit record. Standalone strict Pydantic `model_validate` expects tuples for tuple fields; the adapter's JSON boundary accepts ordinary JSON arrays.

Nothing in these functions invokes M1, M2, M3 or M4. `to_m3_start_request` returns a fresh existing `StartRequest`, with exactly the explicitly confirmed text and caller-chosen provider. The provider defaults to `snapshot`; `live` is permitted only as an explicit caller choice and still triggers no request here. Pass this request object directly to M3; converting it to a differently escaped JSON dictionary may change the size charged by M3. Match `max_m3_request_bytes` to any lower configured downstream limit.

## Versioned recognition schema

`schemas/vision.py` defines frozen, strict, extra-forbidding Pydantic contracts, version `1.0`:

| Model | Contents and restrictions |
| --- | --- |
| `ImageFoodRecognitionResult` | Result ID/revision; one of three statuses; mandatory confirmation; image and model provenance; groups; uncertainty; controlled questions; fixed limitations |
| `ImageReference` | Image ID, original SHA-256, JPEG/PNG media type, declared byte size/dimensions; `verification_scope=declared_metadata_only` |
| `PreprocessingMetadata` | Processed hash/type/dimensions, original EXIF orientation, RGB conversion, metadata-removal declaration and fit-without-upscale policy |
| `VisionModelProvenance` | Local Ollama provider, explicit model tag, full digest, Ollama version, prompt version, timezone-aware declared timestamp and inference configuration |
| `VisionInferenceConfiguration` | Temperature zero, bounded context/output/seed; streaming, thinking, tool execution and cloud fallback disabled |
| `CandidateFoodGroup` | Unique group ID, optional coarse location, one to three ranked alternatives and uncertainty reasons |
| `FoodHypothesis` | Unique candidate ID, consecutive rank and plain identity label; quantity, edible grams, nutrition, FDC ID and confidence are null-only |
| `ConfirmationQuestion` | Stable group/global reference, kind and exact controlled wording; no generated advice |

The provenance is a declaration. Digest/hash syntax checks do not verify weights, image bytes, actual preprocessing, installed model availability, local inference, the timestamp, or model vision capability. Those checks belong to a future image/transport stage. M5.1 accepts no image bytes, paths, URLs or base64 fields and makes no filesystem/service lookup while validating a record.

Declared image bounds are 10 MiB and 20 megapixels. Declared processed dimensions must fit the orientation-adjusted source without upscaling, with a 1,024-pixel longest edge and one-pixel rounding tolerance. Validation checks metadata arithmetic only; it does not inspect EXIF or pixels. Metadata removal must be declared true, but no metadata is actually removed by this stage.

Labels are bounded to 120 characters and a conservative plain-text identity syntax. Numeric characters, percentages, common English quantities and measurement/evidence terms are rejected. This can exclude legitimate numeric brand/dish names; use a nonnumeric identity or a separate human correction. These lexical checks do not prove that arbitrary text is a food name, detect every language's quantity expression, or establish that a label is advice-free. Labels remain untrusted data, never confirmation prompts or instructions. No calibrated likelihood or confidence score is supplied; rank is ordering only.

## Status and uncertainty rules

- `needs_confirmation`: at least one candidate group, unconfirmed identities, and no declared hard ambiguity/visibility reason.
- `uncertain`: a declared reason such as ambiguous identity, mixed dish, occlusion, blur, poor lighting or unrecognized content; candidates may be absent.
- `no_food_detected`: no candidate groups and only the no-food-identified reason. This means the model did not identify food, not that the image is proven food-free.

Groups and candidates have unique IDs. Alternatives are consecutively ranked and distinct after Unicode normalization/case folding. Multiple groups require the multiple-foods reason. Group uncertainty must also be represented globally. No status may waive confirmation, remove the fixed limitations or imply verified recognition.

Every group requires controlled questions about identity/correction/exclusion, known preparation and the absence of an image-derived consumed amount. Results without groups require a food-presence question. All results require confirmation of a user-supplied meal description. `required_confirmation_questions(groups, status)` builds these fixed records; validation rejects altered, missing or obsolete questions. Model labels and free-form source text are never interpolated into question wording.

Acknowledging a question means explicitly accepting the uncertainty and handoff conditions. It does **not** assert that an unknown amount or preparation has been resolved. M3 must still ask for missing details. A future UI must present these questions and collect actual user input, not populate acknowledgements automatically.

## Explicit confirmation binding

`ImageMealConfirmation` requires a true strict boolean `user_confirmed`, nonempty user meal text, the expected result ID/revision, original image hash, canonical result hash, every current question ID, and one decision per group:

- `accept_candidate`: name an existing candidate in that group and a span in the confirmed text containing that label.
- `correct_identity`: supply a separate plain identity label and a matching confirmed-text span. The original image hypothesis is retained.
- `exclude_group`: explicitly exclude it from the image-supported handoff; no candidate, correction or span is permitted.

Spans use Python Unicode code-point indices, start-inclusive/end-exclusive, within the exact user text. They cannot overlap or cut through words. Label matching is Unicode-normalized and case-insensitive, but not a semantic/paraphrase or plural matcher. If the candidate is `banana` and the user says `bananas`, they can explicitly correct the label or use matching wording. Frontend UTF-16 offsets would need an explicit conversion in a future integration.

User text is preserved exactly, including supplied quantities; the adapter neither inserts selected labels nor repairs descriptions nor derives amounts. Additional details in the text are user input, not image evidence. No general semantic verification of the whole description is claimed. A person may write an independent description even when no food was detected, or exclude every group and describe eating nothing. Original hypotheses/status/provenance are still retained separately.

`ConfirmedImageMeal` contains the original validated recognition record, explicit confirmation, normalized result hash and `description_origin=explicit_user_confirmation`. `image_contents_verified` remains false. Any changed hypothesis, model/image reference, question or revision changes the hash and invalidates an old confirmation. Serialized handoffs are revalidated before generating an M3 request; arbitrary caller edits cannot bypass this binding.

The hash covers canonical ASCII JSON including schema defaults. It is a binding mechanism, **not a signature, authentication, replay receipt, proof of human interaction or proof of genuine inference**. A future application must retrieve trusted server-side results, enforce account/session ownership, collect explicit confirmation through its UI, invalidate confirmations after image/result changes, and retain the separate audit record. Self-consistently forged metadata cannot be identified by this pure offline contract layer.

There is no automatic M3 execution or receipt storage. Calling the adapter twice is pure preparation; a caller that starts M3 twice still creates two sessions unless its application adds appropriate request sequencing/idempotency. M3 owns its existing session revisions, authenticated owner context and clarification behavior.

## Bounds, errors and dependencies

`VisionContractSettings` can lower, but not expand, these maxima:

| Bound | Maximum |
| --- | ---: |
| Recognition metadata | 65,536 bytes |
| Confirmation metadata | 32,768 bytes |
| Complete handoff metadata | 131,072 bytes |
| Food groups / alternatives per group | 8 / 3 |
| User meal text | 4,000 characters |
| M3 request object JSON | 16,384 UTF-8 bytes |
| Input nodes / nesting depth | 10,000 / 20 |
| Any metadata list or dictionary | 256 entries |
| Any metadata string | 4,000 characters, with tighter per-field limits |

Input wire bytes and conservative canonical ASCII JSON sizes are bounded, including schema-default expansion on output. Warnings and provenance are never truncated to fit. Duplicate JSON keys, nonfinite numbers, unsupported numeric coercions, recursive/oversized objects and inconsistent data are rejected. No strings are interpreted as filenames, commands, URLs or tools.

Public adapter failures raise `VisionContractError` with a fixed code/message: `invalid_recognition`, `invalid_confirmation`, `invalid_handoff`, `stale_result`, `confirmation_mismatch`, `input_limit`, `output_limit`, or `handoff_failed`. Returned errors do not echo raw metadata, paths, model text or credentials. Raw Pydantic errors remain developer-facing; do not expose their structured error objects to users. Top-level and nested M5.1 models use immutable fields/tuples. The returned existing M3 request remains independently mutable under its unchanged contract.

Only existing Pydantic and Python standard-library dependencies are used. No package, model, dependency declaration or environment configuration is added. In particular, Pillow, PyTorch, Transformers, an Ollama SDK, cloud APIs, actual image validation/decoding and vision transport are absent. M1-M4, their contracts, frontend/backend and `local_preview/` are unchanged.

## Reproduction and validation

Run from the repository root using the existing Python environment:

```powershell
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -q agentic_ai/tests/vision
$m51Temp = Join-Path (Get-Location) ('agentic_ai\.test-tmp-m51-' + [guid]::NewGuid().ToString('N'))
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -q agentic_ai/tests -rs --basetemp=$m51Temp
```

The unique ignored temporary directory avoids the inaccessible shared Windows pytest temp directory observed earlier. M5.1 tests block TCP connections. Test metadata is explicitly synthetic, including placeholder hashes/model identity; it is not an actual image, model output or recognition benchmark. The compatibility test uses scripted M1 extraction plus the existing authentic USDA snapshot through unchanged M3/M4. It is not live Qwen3 or vision inference.

Tests cover all statuses, alternative/group bounds, forbidden numeric/nutrition/confidence fields, provenance/preprocessing declarations, required prompts, malformed metadata, controlled wording, stale confirmation, candidate selection/correction/exclusion, source-span boundaries, missing quantities, manual override after no-food detection, immutability, size/depth/node limits, safe failures and unchanged M3/M4 compatibility.

The next stage needs separate approval: bounded image decoding/preprocessing and a local vision transport, followed by an explicitly approved vision-model download and real-photo accuracy/resource evaluation. M5.1 is entirely offline and requires neither Supabase/MongoDB nor USDA/Ollama services.

## New files

- `schemas/vision.py`: versioned immutable hypotheses, provenance, questions, confirmation and handoff schemas.
- `vision_config.py`: explicit hard metadata/request limits.
- `vision_errors.py`: stable safe errors.
- `vision_validation.py`: bounded JSON parsing, duplicate-key rejection, size accounting and exception boundary.
- `adapters/vision_handoff.py`: pure validation, fingerprints, preparation and explicit M3 request conversion.
- `tests/vision/__init__.py`, `conftest.py`, `test_contracts.py`, `test_handoff.py`, `test_bounds_and_safety.py`: deterministic synthetic-metadata and compatibility tests.
- `VISION.md`: this stage's public interface, limitations and validation report.


## Recorded M5.1 validation

- New M5.1 tests: **192 passed, 0 failed, 0 skipped** (standalone run: 1.15 seconds).
- Existing M1-M4 tests within the full run: **514 passed, 0 failed, 20 skipped**.
- Full combined run: **706 passed, 0 failed, 20 skipped** (final run: 20.13 seconds).
- Skips are the pre-existing opt-in checks: 16 actual-Qwen3 checks and four live USDA checks. They were not run or replaced with simulated live results.
- No warnings were emitted in successful final runs. Testing found and corrected a text-span boundary issue that could otherwise match `banana` by cutting the final letter from `bananas`. Invalid-model serializer warnings were also suppressed at the safe parsing boundary while preserving strict revalidation.
- SHA-256 checks confirm all 249 pre-existing tracked/untracked files are unchanged, including the 73 pre-existing local-preview files and the two existing ignore-file modifications. All 11 new files are under `agentic_ai/`. Only M5.1 source, documentation and tests were added; no dependencies or configuration files changed.
- Generated test directories were removed. No image decoding, model execution/download, installation, service startup, frontend/backend change, Git staging, commit or remote operation occurred.
- Branch remains `agentic-ai`; HEAD remains `2af8b39791bf92c6bff14ad7957572d0ae926f21`. All M5.1 additions remain uncommitted for review.
