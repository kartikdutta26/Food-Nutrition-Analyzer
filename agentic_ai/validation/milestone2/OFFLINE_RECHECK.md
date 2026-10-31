# Milestone 2 offline recheck

Rechecked on 2026-10-31 (Asia/Calcutta user date).

## Scope and results

- All Milestone 2 implementation, test and evidence changes are inside agentic_ai/.
- The sole changed path outside that directory is the pre-existing root .gitignore
  modification. It was preserved; its diff still removes agentic_ai/.pytest_cache/.
- Milestone 1 Python implementations, schemas and existing tests are unchanged.
- backend/ and src/ have no changes. No commit, push or merge was performed.
- Complete offline suite: **257 passed, 20 opt-in live cases skipped**, no failures,
  in **5.66 seconds**. All Milestone 1 offline regression tests were included.
- Live Ollama, full-workflow and USDA opt-in flags were explicitly disabled for
  this offline run. No fresh live USDA verification is claimed.
- The actual six-example offline CLI exited successfully. Its extraction inputs
  are manually curated fixtures; its nutrient records are authentic snapshots.
- No failed offline tests required implementation changes in this recheck.

## Independent calculation and attribution checks

The raw foods.json was loaded independently from the calculation tools. Its checksum
was recomputed and all ten IDs, descriptions, data types and publication dates were
compared with manifest.json. All matched.

For all six resolved food-item occurrences in the demonstration, the check derived
calories/protein/carbohydrates/fat/fiber directly from raw USDA nutrient IDs and
values. It independently verified the source portions, edible grams, 100-g bases,
scale factors, calculated values, totals and food-item coverage. It also checked
provider labels, FDC URLs, retrieval timestamps and snapshot checksum attribution.

Examples:

- Egg 173424: 100 g * 155 kcal / 100 g = 155 kcal.
- Cooked rice 168878: 150 g * 130 kcal / 100 g = 195 kcal.
- Combined egg/rice meal = 350 kcal, 16.615 g protein, 43.375 g carbs,
  11.03 g fat and 0.6 g fiber.
- Small roti portion 299422: 2 * 27 g = 54 g. Half rice cup portion 83928:
  0.5 * 158 g = 79 g. Combined = 264.16 kcal.
- Medium banana portion 93515: 118 g, yielding 105.02 kcal.
- Banana plus unresolved paneer curry: known subtotal 89 kcal; full total null;
  calorie coverage 1 of 2 food items. This is not a complete meal estimate.
- Generic apples and whole milk request clarification. No milk density is assumed.

The passing automated tests also check conflicting preparations, ambiguous source
matches, user-selected IDs/portions, missing nutrients versus true zero, unsupported
weights/units, fractional and multi-piece portions, and backend per-serving values
scaled exactly once.

## Authentic USDA snapshot inventory

These ten records are saved in ../../data/usda/foods.json, with traceability in
../../data/usda/manifest.json. They were acquired from USDA during implementation;
this recheck verifies the saved records and integrity, not their current live versions.

| FDC ID | Authentic stored description | Data type |
| --- | --- | --- |
| 173424 | Egg, whole, cooked, hard-boiled | SR Legacy |
| 173423 | Egg, whole, cooked, fried | SR Legacy |
| 168878 | Rice, white, long-grain, regular, enriched, cooked | SR Legacy |
| 168877 | Rice, white, long-grain, regular, raw, enriched | SR Legacy |
| 173944 | Bananas, raw | SR Legacy |
| 171688 | Apples, raw, with skin (Includes foods for USDA's Food Distribution Program) | SR Legacy |
| 171689 | Apples, raw, without skin | SR Legacy |
| 171265 | Milk, whole, 3.25% milkfat, with added vitamin D | SR Legacy |
| 172217 | Milk, whole, 3.25% milkfat, without added vitamin A and vitamin D | SR Legacy |
| 2707713 | Bread, chappatti or roti | Survey (FNDDS) |

## Mocked/synthetic fixtures

These are **test-only**, not authentic USDA records or verified serving conversions:

- HTTP bodies, errors, timeouts, rate limits and fake clients in test_provider_and_client.py.
- The synthetic backend response in test_analysis_and_backend.py. It reuses the real
  rice ID but is a constructed contract payload, not a captured backend/API response.
- Copies of authentic records altered to remove nutrients, change units, introduce
  duplicate/invalid values, simulate limits of quantification, or change completeness.
- synthetic-two: two pieces weighing 100 g, solely to verify division by source amount.
- synthetic-ml: 100 ml weighing 103 g, solely to test a documented-volume code path.
  **This is not verified milk density and is not available to the snapshot provider.**
- synthetic-overflow: an extreme invalid portion used to verify safe numeric errors.
- Synthetic candidate ID 999001 used for name-matching tests, not a claimed USDA lookup.
- data/demo_extractions.json contains curated meal extraction inputs, not USDA records
  and not output from actual model inference.

None of these synthetic mutations or invented test portions is packaged in foods.json.

## Evidence and reproduction

- offline-recheck-tests.xml: current complete offline test results.
- offline-recheck-demo.json: output captured from the actual offline CLI command.
- offline-recheck-verification.json: independent arithmetic/provenance/scope checks.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUTRIAI_RUN_LIVE_TESTS = '0'
$env:NUTRIAI_RUN_NUTRITION_LIVE = '0'
$env:NUTRIAI_RUN_USDA_LIVE = '0'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q --basetemp=agentic_ai/.test-tmp-m2-recheck
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --offline-examples
```

Earlier live verification remains partial: two source detail checks passed; two
USDA checks returned HTTP 429 with the restricted public demonstration key. No live
request was retried during this offline recheck. See REPORT.md for that separate run.
