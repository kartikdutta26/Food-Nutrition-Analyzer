# M5.3: local food image hypotheses with Qwen3-VL 2B

M5.3 adds a separate `ImageFoodRecognitionAgent` and `OllamaVisionClient`.
It uses M5.2 preprocessing and returns the unchanged M5.1
`ImageFoodRecognitionResult`. It does not invoke M1/M2/M3/M4, fetch USDA data,
save meals, estimate portions, calculate nutrients, or integrate any application
screen. Recognition is a proposal of food identities, not verified food presence,
ingredient/allergen identification, a nutrition result, or medical advice.

## Local readiness at implementation

On 2026-11-12 the original `agentic-ai` workspace was at
`5046150b840c214288527d57443eb20cfc45fc51`, with the two expected modified
ignore files and untracked `local_preview/` preserved.

- Windows reported 15.73 GiB physical RAM, **1.33 GiB available**, 91% memory load.
  CIM inspection was denied; the read-only Windows `GlobalMemoryStatusEx` API
  provided these figures instead.
- The loopback Ollama API was running, version **0.40.16**.
- `/api/tags` listed only **qwen3:4b-instruct**. That text model is not used as a
  substitute for image inference. `/api/ps` listed no loaded models.
- **qwen3-vl:2b was not installed. No model was downloaded or run.** No unrelated
  process was terminated or unloaded. Real-photo accuracy is not validated by
  deterministic tests.

The official [Qwen3-VL 2B page](https://ollama.com/library/qwen3-vl:2b) specifies
Ollama 0.12.7 or later. The client checks this minimum, exact installed tag,
64-character installed digest and declared `vision` plus `completion`
capabilities before sending image bytes. The model tag is deliberately limited
to `qwen3-vl:2b` in this stage; a different model needs a reviewed configuration
change. Missing models produce `model_missing`, never an automatic pull.

## Files and boundaries

| File | Responsibility |
| --- | --- |
| `vision_runtime_config.py` | Strict explicit runtime limits and numeric loopback HTTP origin validation |
| `vision_runtime_errors.py` | Fixed safe public errors |
| `schemas/vision_inference.py` | Narrow untrusted response schema and versioned controlled prompt |
| `clients/ollama_vision_client.py` | Local readiness, bounded HTTP, model identity checks and inference envelope validation |
| `agents/image_food_agent.py` | M5.2 preprocessing, hypothesis validation and unchanged M5.1 result assembly |
| `vision_demo.py` | Readiness/recognition CLI with RAM reporting and conservative memory guard |
| `tests/vision/test_vision_runtime_client.py` | Scripted HTTP, bounds, errors, loopback and provenance tests |
| `tests/vision/test_image_food_agent.py` | Candidate safety, uncertainty and confirmation handoff tests |
| `tests/vision/test_vision_demo.py` | CLI privacy, readiness and memory guard tests |
| `VISION_RUNTIME.md` | Usage, limitations and validation report |

No additional dependencies are needed. Use the existing Pydantic dependency and
optional Pillow dependency already isolated in `requirements-vision.txt` for
M5.2. No dependency installation or environment-file change is part of M5.3.
M1-M5.2 files and contracts remain unchanged.

## Interfaces

```python
from agentic_ai.agents.image_food_agent import ImageFoodRecognitionAgent
from agentic_ai.clients.ollama_vision_client import OllamaVisionClient
from agentic_ai.vision_runtime_config import VisionRuntimeSettings

settings = VisionRuntimeSettings()  # http://127.0.0.1:11434, qwen3-vl:2b
client = OllamaVisionClient(settings)
installed = client.check_ready()  # Metadata only, no model load or inference.
# Report available RAM first; prefer the guarded CLI for a local demonstration.
result = ImageFoodRecognitionAgent(settings=settings, client=client).analyze("my-local-photo.jpg")
```

`check_ready()` returns `LocalVisionModel(model_tag, model_digest,
ollama_version)`. `analyze()` on the client accepts an M5.2 `ProcessedImage` and
returns `VisionInferenceReply(content, provenance)`. The reply's repr hides raw
model content. Agent `analyze()` takes a local JPEG/PNG path, always uses the
default M5.2 1024-edge policy, and returns the validated M5.1 record. Neither
source paths nor original image bytes go to Ollama. Only the metadata-stripped
RGB PNG bytes are base64-encoded in the request's image array, as required by
the [Ollama vision REST API](https://docs.ollama.com/capabilities/vision).

Settings are explicit; M1's `.env`, `OLLAMA_BASE_URL`, proxies and cloud API
credentials are not consulted. Injected test clients are trusted Python code,
not an extension point for untrusted callers. The default transport is the one
enforcing loopback restrictions.

## Untrusted model output and uncertainty

The model can supply only:

```json
{
  "status": "uncertain",
  "groups": [{
    "location": "center",
    "labels": ["paneer", "tofu"],
    "uncertainty_reasons": ["ambiguous_identity"]
  }],
  "uncertainty_reasons": ["identity_unconfirmed", "ambiguous_identity"]
}
```

This example illustrates a schema, not a recorded inference result. Each of at
most eight groups has one to three distinct labels, at most 120 characters per
label, a coarse enum location and enum uncertainty reasons. JSON Schema is sent
in `format` and the prompt, following Ollama's
[structured-output interface](https://docs.ollama.com/capabilities/structured-outputs).
Schema generation does not replace local validation.

Extra fields are forbidden, including model-supplied IDs, hashes, provenance,
quantities, edible grams, nutrients and numeric confidence. Labels undergo M5.1
numeric/control/character checks plus conservative instruction/medical-claim
word filtering. Duplicate JSON keys, duplicate alternatives, invalid status
combinations, nonfinite values, oversized/nested data and unknown reasons fail
closed. Visible text, labels, QR codes and prompt-injection attempts are data,
never instructions. No tool executor or OCR action exists.

The application assigns ranks and group IDs, adds unconfirmed identity and
unknown preparation to every group, aggregates uncertainty and marks multiple
groups. Multiple alternatives automatically add ambiguous identity and downgrade
ordinary confirmation to `uncertain`. Any hard uncertainty also forces this
status. Uncertain images may have no candidates. `no_food_detected` requires
empty groups and only `no_food_identified`, and still asks the user whether food
is present. It means the model identified no food, not proven absence.

This is syntactic safety, not a food ontology or accuracy guarantee. An ordinary
food label can still be wrong; a small local VLM may hallucinate, miss foods or
confuse dishes. Instruction-word filtering is conservative and incomplete,
especially across languages. It is not a prompt-injection proof. Treat all labels
as untrusted text in a future frontend, never HTML, commands or tool inputs.

## Confirmation before M3

The agent generates fixed M5.1 questions and limitations and never creates an M3
request. Every inference has a fresh result ID and revision 1. Re-running does not
mutate an old result; stale confirmation fails against a different result ID,
revision, image hash or result fingerprint. Preserve the full original result
beside the user's independent confirmed description using existing M5.1 APIs:

```python
from agentic_ai.adapters.vision_handoff import prepare_confirmation, to_m3_start_request

# user_confirmation must explicitly bind the result/hash/revision, acknowledge
# the questions, and identify accepted/corrected/excluded groups and text spans.
handoff = prepare_confirmation(result, user_confirmation)
request = to_m3_start_request(handoff, provider="snapshot")
# Only an authorized caller may now explicitly pass request to existing M3.
# This example does not invoke M3 or fill missing portions/preparation.
```

No consumed amount is inferred. A confirmed description such as `banana` stays
`banana`; M3 must clarify amounts using its existing behavior. Users may correct
or exclude hypotheses or provide a manual description after no-food detection.
`VISION.md` documents the full confirmation shape. M5.3 adds no authenticated
session store, account ownership, web routes or meal persistence.

## Transport, provenance and bounds

- HTTP only to a canonical numeric IPv4 loopback address or IPv6 `::1`. No DNS
  hostnames (including `localhost`), external origins, HTTPS, credentials,
  URL paths, query strings, fragments, redirects or proxies. Only `/api/version`,
  `/api/tags`, `/api/show` and `/api/chat` are called. There is no model-pull API.
- Only an installed exact model tag with a valid digest is accepted. Entries
  declaring a remote host/model are rejected. Vision capability is checked.
  The installed digest is checked again after inference; a changed or removed
  tag yields no result. This cannot prevent an adversarial tag swap-and-restore
  or prove weight files independently. Trust the local Ollama daemon.
- The application supplies the observed digest/version, UTC time, prompt version
  and actual inference settings. M5.1's conservative
  `verification_scope=declared_metadata_only` is retained. Provenance is not a
  signature, physical image verification, or inference attestation.
- Fresh system/user messages with one processed image, `stream=false`,
  `think=false`, temperature 0, seed 0, context 4096 and at most 1024 generated
  tokens by default. Context can be 1024-4096, output 64-2048 tokens. There are no
  tools, history, model re-ranking or cloud fallbacks. `keep_alive=0` requests
  unloading only this vision model after the request; unrelated models/processes
  are not stopped by application code.
- The total client operation budget is 120 seconds, configurable 1-180 seconds,
  shared across readiness, inference and the final digest check. Direct socket
  timeouts and a deadline watchdog interrupt blocked headers/body reads. Request
  bodies are capped at 6 MiB, HTTP responses at 1 MiB, raw model output at 32 KiB
  and the final result by existing M5.1 bounds. Limits can only be lowered.
- HTTP errors, redirects, oversized or malformed envelopes, non-assistant/tool/
  thinking responses and incomplete generation (`done_reason` other than `stop`)
  are errors, not fabricated uncertainty or no-food results. No automatic retry
  or JSON repair occurs. A caller may explicitly retry with a fresh inference.
- `VisionRuntimeError.code` uses fixed messages: `invalid_configuration`,
  `service_unavailable`, `timeout`, `response_limit`, `invalid_response`,
  `model_missing`, `unsupported_runtime`, `vision_unavailable`, `unsafe_model`,
  `model_changed`, `invalid_model_output`, `invalid_image`, `insufficient_memory`,
  `memory_unavailable`, or `inference_failed`. M5.2 input errors are preserved.
  Errors never echo raw model content, base64, bytes, metadata or private paths.

The client does not log images or raw replies. Local daemon/system logging is
outside this module's control. Closing a timed-out HTTP request is not a proven
server-side cancellation guarantee. Concurrent callers still share Ollama's
model queue/RAM; a future application should bound concurrent inference. Fixed
seed/temperature do not promise reproducible recognition across hardware/builds.
No real-photo latency, memory peak or accuracy claim is made yet.

## CLI and future live demonstration

```powershell
# Safe read-only readiness check. It never pulls or loads a model.
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.vision_demo --check

# Run only AFTER separately approved local model installation and readiness.
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.vision_demo --image "C:\your-private-photo.jpg"
```

RAM is reported on stderr before inference. The CLI refuses recognition below
4 GiB available RAM, or if memory cannot be checked. This is a conservative demo
guard, not an empirically verified model requirement; GPU/VRAM and native runtime
overhead are not measured. It does not close other applications. The library API
does not implement a system-resource admission controller; callers must budget
RAM/concurrency themselves. CLI output is the bounded recognition metadata only,
not image bytes or source paths; failures return exit code 2 and a fixed code.

For an approved live check, use user-chosen non-sensitive photographs: a clearly
visible food, a mixed/ambiguous dish, multiple distinct foods, a non-food image and
a poor-quality image. Compare candidates with manual observation; never count
synthetic/scripted tests as model accuracy evidence. Confirm/correct each result
manually before any later M3 processing. The missing model and low available RAM
currently block that check. Once installed, recognition runs offline against the
local daemon; a subsequent M2 live USDA lookup remains an external service call.

## Deterministic validation

```powershell
$m53Temp = 'agentic_ai/.test-tmp-m53-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/vision/test_vision_runtime_client.py agentic_ai/tests/vision/test_image_food_agent.py agentic_ai/tests/vision/test_vision_demo.py -q -rs --basetemp=$m53Temp
$m53FullTemp = 'agentic_ai/.test-tmp-m53-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q -rs --basetemp=$m53FullTemp
```

Tests use generated pixels and scripted transport replies. The existing vision
test fixture blocks real network connections. They cover strict numeric loopback
configuration, no proxy/redirect/pull, model/capability/digest safeguards,
deadlines/bounds/failures, payload privacy, untrusted JSON/labels/claims, candidate
limits, uncertainty, confirmation, stale handoffs and CLI RAM/error behavior.
No new tests claim live Ollama or real-photo validation.

### Validation checkpoint

| Suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| New M5.3 deterministic tests | 163 | 0 | 0 |
| Existing M1-M5.2 regression tests | 844 | 0 | 20 |
| Full combined suite | 1007 | 0 | 20 |

The final full run took 41.84 seconds and emitted no test warnings. Existing
skips are four opt-in live USDA checks and sixteen opt-in local Qwen3 checks.
No live vision test is counted as passing or skipped within that suite: real
vision inference was not attempted because the approved model is missing.

The real, read-only CLI readiness check reached the running local service and
returned `model_missing`, exit code **2**. Its last RAM snapshot was **1.41 GiB
available** (memory availability fluctuates; an earlier check showed 1.58 GiB).
That is also below the CLI's conservative 4 GiB demo threshold. This confirms
truthful missing-model handling, not recognition accuracy or live M3 completion.
Model installation and a real-photo test require a later approved action; no
model/dependency download, service start/stop or unrelated app termination occurred.

Scope/preservation audit: all 265 pre-existing tracked/untracked source files
match their starting SHA-256 fingerprints. The two modified ignore files and
73 untracked `local_preview` files remain untouched. Only the ten files listed
above are new. Python syntax and credential-pattern checks passed, and nothing
was staged or committed. M1-M5.2, frontend/backend, databases and other branches
were not modified.
