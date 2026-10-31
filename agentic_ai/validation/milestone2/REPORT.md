# Milestone 2 validation and delivery

Latest offline recheck: [OFFLINE_RECHECK.md](OFFLINE_RECHECK.md) records 257 passing tests, the six-example offline demonstration, independent arithmetic checks and the authentic-versus-synthetic fixture inventory.

User-facing date: 2026-10-31, Asia/Calcutta.

**Implementation and offline/local-model validation are finished. Live USDA
validation is partial, not an all-passing live verification.** The remaining live
checks hit the public DEMO_KEY quota. No personal key was available in the process
or agentic_ai configuration. No automatic provider fallback was used.

## Test results

| Check | Actual outcome |
| --- | --- |
| Entire default offline suite | 257 passed, 20 opt-in tests skipped, 0 failures; 2.99 s |
| Original Milestone 1 actual Qwen3 regression suite | 12 passed, 0 failures; 164.36 s |
| Actual Qwen3 -> offline USDA nutrition acceptance cases | 4 passed |
| Live USDA details for rice 168878 and egg 173424 | 2 passed, matching snapshot nutrients and portions |
| Live USDA roti 2707713 and provider search checks | 2 failed with HTTP 429 rate limiting; not verified |
| Six-example offline CLI | Exit 0; expected complete/clarification/partial outcomes |
| Six-example actual Qwen3 + snapshot CLI | Exit 0; expected complete/clarification/partial outcomes |

The live-tests.xml run contains six passing cases (four Qwen3 workflows and two
USDA detail checks), plus the two rate-limited USDA failures. These failures are
retained as evidence rather than relabeled as passes or skips. The default test
suite does not call USDA or Ollama and passes with no credentials or internet.
The CLI examples overlap acceptance tests and are not independent accuracy samples.

## Authentic records and provenance

The ten-record snapshot was actually obtained from USDA's live search/bulk-details
API using the documented public demonstration key. The raw bulk response is saved
unchanged, together with IDs, descriptions, data types, publication dates, retrieval
time, source URLs and a checksum. No nutrient values or serving weights were invented.

- Snapshot file: ../../data/usda/foods.json
- Manifest: ../../data/usda/manifest.json
- Source: https://fdc.nal.usda.gov/
- Retrieval timestamp: 2026-10-31T09:29:54.430152+00:00
- SHA-256: c3fde77650f6b10f4fa2f568a800464b34808cacb7bef239e40ea38a7c768937
- License: USDA FoodData Central CC0-1.0

Records include cooked/raw rice, boiled/fried egg, banana, apples with/without skin,
two whole-milk variants and an FNDDS chappatti/roti reference. This is an explicitly
limited offline catalog, not the full USDA database. The source retrieval succeeded;
that is separate from later validation of the implemented live provider. Provider
GET checks passed for two IDs before the restricted public quota returned HTTP 429.
The roti/search provider checks still need a valid personal key or quota reset.

## Demonstrated actual Qwen3-to-nutrition results

These rows come from the actual --examples CLI run, not manually constructed output.
Nutrient amounts in full JSON are decimal strings; null/None means unknown.

| Meal input | Status | Complete calories (kcal) | Known calorie subtotal (kcal) | Seconds |
| --- | --- | --- | --- | --- |
| I ate 100 g boiled eggs and 150 g cooked white rice. | complete | 350.0000 | 350.0000 | 16.42 |
| I ate 2 small rotis and 1/2 cup cooked white rice. | complete | 264.1600 | 264.1600 | 15.32 |
| I ate 1 medium banana. | complete | 105.0200 | 105.0200 | 5.71 |
| I drank 250 ml whole milk. | needs_clarification | None | None | 6.78 |
| I ate 100 g bananas and one bowl of paneer curry. | partial | None | 89.0000 | 15.1 |
| I ate 100 g apples. | needs_clarification | None | None | 6.14 |

The 264.16-kcal example uses USDA's small roti reference (27 g each) and half of
its 158-g cooked-rice cup. It does not assert the recipe or weight of any other roti.
The paneer meal's 89-kcal subtotal includes only the banana; the meal total remains
unknown. Generic apples/milk are ambiguous. No milk density was assumed.

## Evidence files

- offline-tests.xml: final combined M1 + M2 offline tests and expected opt-in skips.
- m1-live-tests.xml: unchanged original twelve actual Qwen3 cases rerun successfully.
- live-tests.xml: actual USDA and Qwen3 nutrition checks, including quota failures.
- live-results.json: captured results and per-check verification status.
- offline-demo.json: six CLI outputs using explicitly labeled curated extraction inputs.
- qwen-demo.json: six CLI outputs using real qwen3:4b-instruct food understanding.

## Reproduction commands (repository root, PowerShell)

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q --basetemp=agentic_ai/.test-tmp-m2
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --offline-examples
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --examples
```

For independent verification modes, enable only the intended flag:

```powershell
# Original actual local-model regression tests:
$env:NUTRIAI_RUN_LIVE_TESTS = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/test_live_ollama.py -q

# Actual local-model nutrition workflows with offline USDA data:
$env:NUTRIAI_RUN_NUTRITION_LIVE = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/nutrition/test_live_verification.py -m nutrition_integration -q

# Actual external USDA checks: configure your personal USDA_API_KEY first.
$env:NUTRIAI_RUN_USDA_LIVE = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/nutrition/test_live_verification.py -m usda_live -q
```

## Implemented guarantees and limits

- Matching never silently chooses between compatible candidates. Truncated live
  searches request refinement/explicit source selection instead of claiming uniqueness.
- Numeric units, weights, densities and preparation are not supplied by an LLM.
  Missing sizes/forms/volume-to-mass records require clarification or measured mass.
- Portions use gramWeight / amount. The backend adapter retains its per-serving
  gram basis, preventing double-scaling. Sample presets are rejected as verified data.
- Unknown nutrients stay null. Real source zeroes remain zero. Known subtotals and
  per-nutrient food-item coverage are separate from complete meal totals.
- Decimal contributions are summed before public four-place rounding. The original
  food quantity precision is inherited from the unchanged Milestone 1 contract.
- Matching is conservative English lexical matching with limited aliases. The ten
  snapshot foods do not cover paneer curry, dal, arbitrary brands or recipes.
- Generic reference recipes cannot establish a homemade meal's exact composition.
  Edible weights are required; raw/cooked yields, refuse, container volume and density
  are not inferred. Other languages and broad catalog accuracy remain unevaluated.
- The live provider's remaining roti/search checks are incomplete due to external
  rate limiting. No claim of complete live USDA verification is made.

All original Milestone 1 Python/schema/test files are unchanged. Only package
README.md, .env.example and pytest.ini received documentation/configuration additions.
New code, fixtures and evidence are entirely inside agentic_ai/. backend/, src/ and
teammate files were not edited. The pre-existing root .gitignore modification was
preserved. HEAD remains 489b8b1; no commit, push or merge was performed.

Milestone 3 recommendation: build a bounded orchestrator with clarification state,
per-item source/portion selections, tool error recovery and an explainable execution
trace. Agree on the backend adapter contract before changing teammate-owned interfaces.
