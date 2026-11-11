# NutriAI M1–M5: standalone Agentic AI handoff

This is the current cross-milestone guide. The older milestone documents describe
their individual delivery checkpoints. Start with [local setup](LOCAL_SETUP.md),
the [evaluation guide](VIVA_GUIDE.md) and the [validation ledger](FINAL_VALIDATION.md).
This package does not require the team application, Supabase or MongoDB.

## Responsibilities and interfaces

| Module | Input → public output | Responsibility and boundary |
| --- | --- | --- |
| M1 `agents/food_agent.py` | `FoodUnderstandingAgent.analyze(text)` → `FoodUnderstandingResult` | Local Qwen3 text extraction, Pydantic/source-span validation and explicit quantity normalization. Unknown amounts remain unknown. No nutrition retrieval. |
| M2 `agents/nutrition_agent.py` | `NutritionAnalysisAgent(provider).analyze(extraction, selections=None)` → `NutritionResult` | Conservative food/portion matching and Decimal nutrient scaling from supplied USDA records. No invented weights, densities or recipes. |
| M3 `orchestration.py` | `AgentOrchestrator.start(StartRequest, owner=...)`, `get`, `respond`, `retry`, `close` → `SessionResponse` | Stateful clarification, source/portion selection, bounded retries, IDs, revisions and request replay checks. Calls M1/M2. |
| M4 `agents/recommendation_agent.py` | `NutritionRecommendationAgent.recommend(nutrition, context=None)` or `recommend_session(session, expected_revision=..., context=None)` → `RecommendationResult` | Deterministic evidence-linked observations and eligible suggestions. Validates supplied-record consistency; does not retrieve USDA or run Qwen3. |
| M5.1 `schemas/vision.py`, `adapters/vision_handoff.py` | `ImageFoodRecognitionResult` + `ImageMealConfirmation` → `ConfirmedImageMeal`; `to_m3_start_request(...)` | Bounded food-identity hypotheses and explicit user-confirmed text. The adapter alone does not start M3. |
| M5.2 `tools/image_input.py` | `preprocess_image(local_path)` → `ProcessedImage` | JPEG/PNG validation, orientation normalization, RGB conversion, metadata stripping, original/processed SHA-256 and dimensions. Default limits: 10 MiB, 20 megapixels, 1024-pixel output edge. |
| M5.3 `agents/image_food_agent.py`, `clients/ollama_vision_client.py` | `ImageFoodRecognitionAgent.analyze(local_path)` → `ImageFoodRecognitionResult` | Invokes preprocessing and strictly validates untrusted local vision replies. Numeric-loopback HTTP only, bounded deadlines and model metadata checks. Actual vision inference remains postponed. |
| M5.5 `image_workflow.py` | `ImageNutritionWorkflow.begin(path, owner=...)`, `confirm`, `get`, `respond`, `retry`, `recommend(expected_revision=...)`, `close` → `ImageWorkflowSnapshot` | Composes preprocessing, recognition, confirmation, M3 and M4. Only explicit confirmed text reaches M3. Owner required on every operation. |
| M5.6 `final_demo.py` | `build_report(scenario='all')`, CLI `main(argv=None)` | Presentation-only wrapper around existing M5.5 `run_example`; no new AI contract or nutrition logic. |

The source schemas, not this overview, define exact fields. Relevant contracts:
`schemas/food.py`, `nutrition.py`, `orchestration.py`, `recommendation.py`,
`vision.py`, `image_workflow.py`. See [M2](NUTRITION.md), [M3](ORCHESTRATION.md),
[M4](RECOMMENDATIONS.md), [M5.1](VISION.md), [M5.2](IMAGE_INPUT.md),
[M5.3](VISION_RUNTIME.md) and [M5.5](IMAGE_WORKFLOW.md) for detailed bounds/errors.

## Data flow and confirmation

```text
Local image → M5.2 preprocessing → M5.3 untrusted identity hypotheses
          → M5.1 explicit user confirmation → confirmed meal text
          → M3 / M1 validated extraction → structured clarification
          → M2 USDA matching + verified portion basis + Decimal calculation
          → M3 revisioned nutrition → M4 consistency checks + interpretation
```

M5.6 substitutes scripted vision and M1 transports and scripted DEMO USER actions;
it still executes actual preprocessing, source validation, confirmation guards,
M3 orchestration, M2 calculations and M4 rules. Synthetic image pixels have no
relationship to the food hypotheses. Placeholder model provenance is not an
attestation of an installed model. No inference or network service is used.

Recognition statuses are `needs_confirmation`, `uncertain`, `no_food_detected`.
Up to eight food groups each contain at most three identity alternatives. Image
hypotheses supply no edible grams, nutrient values, USDA IDs or confidence
percentages. Confirmation binds result ID/revision, image hash, result fingerprint,
question acknowledgements and selected/corrected text spans. Explicit confirmation
is necessary even if there is only one candidate. Hash binding prevents accidental
substitution; it neither proves visual correctness nor proves a person clicked.

M3 asks for missing quantity, preparation or source/portion selection. Quantities
come from explicit user statements or source-documented serving weights, never the
image. The complete demo supplies banana 100 g and boiled egg 100 g through
scripted clarification. The partial demo confirms banana 100 g and leaves paneer
curry unresolved. A completed M3 conversation can still have partial nutrition.

## Evidence and unknown values

`data/usda/foods.json` contains ten authentic offline FoodData Central records.
`data/usda/manifest.json` records source IDs, URLs, retrieval time and CC0-1.0
attribution. `SnapshotProvider` checks the saved bytes against the manifest hash:
`c3fde77650f6b10f4fa2f568a800464b34808cacb7bef239e40ea38a7c768937`.
Retrieval was `2026-10-31T09:29:54.430152+00:00`. This detects local corruption
relative to the manifest; it is not a cryptographic USDA signature or live check.

Records retain per-100-g basis, nutrient IDs/units, portions, descriptions and
provenance. M2 uses Decimal arithmetic and reports complete totals separately from
known subtotals and per-nutrient food-item coverage. `null` means unknown; a genuine
source zero remains zero. Coverage is not a percentage of meal weight or accuracy.
An unsupported curry contributes unknowns, not an invented recipe or zero calories.
Database reference composition cannot establish a photographed meal's exact recipe.

M4 retains source citations, evidence references, subtotals, unknowns and M3
session/revision. Its `ready`, `limited`, `unavailable` statuses describe usable
evidence, not a health score. Generation is deterministic and its scope is
`supplied_record_consistency_only`. It infers no personal goals or targets; daily
targets are not silently interpreted as meal targets. It is not medical advice.

## Safe integration boundaries

These are Python library interfaces, not application endpoints. A future trusted
server must authenticate users, derive owner identities from verified credentials,
retrieve owner-scoped current sessions and require expected revisions. Never accept
frontend-submitted nutrition/provenance as authoritative or trust client user IDs.
Discard displayed recommendations after session changes and regenerate at the
current revision. Keep multi-item/partial results separate from the team's legacy
single-food meal-saving schema until a compatible format is approved.

Current stores and replay protection are process-local, bounded and expiring; they
are lost on restart and are not multi-worker persistence or authentication. M5.5
serializes operations with a lock and consumes confirmation before starting M3.
An ambiguous start failure can leave a bounded orphan session until native expiry;
there is no cross-store transaction. Recommendation generation checks revisions
before/after but is not a cross-process atomic snapshot. Integration requires
teammate review of ownership, persistence, lifecycle and error mappings.

M5.3 enforces numeric-loopback HTTP and rejects cloud/redirect/proxy use. Do not
generalize this to M1: its older configurable transport accepts other HTTP(S)
origins. The final offline demo injects clients and does not instantiate a live
transport. Source descriptions and image/model content remain untrusted data;
schemas and controlled wording reduce risk but cannot guarantee semantic accuracy.
Raw pixels/private paths should not enter application logs or durable session
metadata. No onboarding, database migration or application integration is included.
