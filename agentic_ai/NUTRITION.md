# NutriAI Milestone 2: source-backed nutrition and portions

Milestone 2 composes the existing Food Understanding Agent with deterministic
nutrition tools. All code, records, tests and evidence are inside `agentic_ai/`.
The original food-understanding schemas, implementation, CLI and tests are unchanged.
No new Python dependencies are required in the existing environment.

## Run from the repository root (PowerShell)

Offline demonstration, with curated extraction inputs and authentic USDA records:

```powershell
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --offline-examples
```

This mode needs no Ollama server, API key, internet, backend or database. Its output
explicitly says that extraction inputs are curated, not model inference.

Actual local Qwen3 food understanding followed by offline USDA nutrition:

```powershell
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --examples
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --text "I ate 100 g boiled eggs and 150 g cooked white rice."
```

`--examples` runs six descriptions: eggs/rice, small rotis/rice, a medium banana,
whole milk in ml, a partially unresolved paneer meal, and ambiguous apples.
Ollama must already be running with `qwen3:4b-instruct`; no model download occurs.

To confirm an ambiguous source and portion explicitly (zero-based item index):

```powershell
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --text "I ate 2 bananas." --select 0:173944:93515
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --text "I ate 2 rotis." --select 0:2707713 --grams 0:70
```

The first command explicitly chooses USDA's medium-banana portion. The second
supplies **70 total edible grams for both rotis**, not 70 grams per roti. The user
weight is labeled user-provided; USDA supplies nutrient composition, not that weight.
`--select INDEX:FDC_ID[:PORTION_ID]` and `--grams INDEX:TOTAL_EDIBLE_GRAMS` may be
repeated for different items. They are supported for one request, not batch examples.
A selected source/portion must remain compatible with the food, preparation and unit.

You may pass an existing Milestone 1 result with `--input-json PATH` to skip inference.
Each output line is one JSON object. Clarification and partial results exit with 0;
input/provider/model failures exit with 1. Invalid CLI arguments exit with 2.

## Providers and credentials

Snapshot is the explicit default. `--provider live` uses USDA FoodData Central:

```powershell
# Put your own USDA_API_KEY in the process environment or ignored agentic_ai/.env.
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --text "I ate 100 g boiled eggs and 150 g cooked white rice." --provider live --select 0:173424 --select 1:168878
```

Only live mode needs a [data.gov/FoodData Central key](https://fdc.nal.usda.gov/api-key-signup/).
USDA documents a restricted public DEMO_KEY for small experiments; routine usage
should use a personal key. No backend secrets are read and no keys are stored in
snapshots, results or exceptions. The API origin is fixed to USDA's HTTPS endpoint.
`.env.example` documents timeout/retry settings. Nutrition settings are separate
from Milestone 1 settings, and use only agentic_ai/.env plus process variables.

Search uses the documented JSON dataType array for Foundation, SR Legacy and FNDDS.
Branded-label formats are deliberately unsupported. Responses are size-limited;
authentication, missing IDs, timeout, connection, malformed JSON and rate-limit
errors have distinct codes. Server retries are bounded. A short numeric Retry-After
may be honored; long or unparseable delays return a rate-limit error instead of
retrying before the server's requested wait. The timeout is per socket operation.
There is no silent switch from live lookup to snapshot data.

Searches/details are cached in memory for the current provider/client instance.
Nothing automatically refreshes or rewrites the packaged snapshot. A truncated
search cannot be treated as a unique match: refine it or explicitly select an ID.

## Authentic offline data

`data/usda/foods.json` preserves a complete USDA API response containing ten records.
`data/usda/manifest.json` records its SHA-256 checksum, retrieval timestamp, source
endpoint, FDC IDs, descriptions, data types and publication dates. Loading verifies
the checksum, IDs and descriptions. This detects accidental changes; it is not a
USDA digital signature. Provenance links point back to FoodData Central.

The snapshot includes boiled/fried eggs, cooked/raw white rice, bananas, apples
with/without skin, two whole-milk variants, and FNDDS chappatti/roti. It is a small,
explicit catalog, not a claim to cover all foods or all USDA matches. Its search
scope is included in results. It must never be extended with invented nutrient values.
The roti record represents USDA's reference recipe, not every homemade roti.

`data/demo_extractions.json` contains manually prepared extraction inputs, not
nutrition records. Tests may mutate copies of authentic records to simulate failures;
those mutations never enter the snapshot or demonstration nutrition provider.

## How the modules fit together

- `schemas/nutrition.py`: validates records, nutrient values, portions, per-item
  source selections and analysis results. It does not change FoodItem or the
  original FoodUnderstandingResult schema.
- `nutrition_config.py`, `nutrition_errors.py`: separate environment settings and
  stable nutrition error codes. Secrets are excluded from settings serialization.
- `clients/usda_client.py`: bounded HTTP, authentication, retries and per-run caching.
- `providers/usda.py`: interchangeable live/snapshot providers and snapshot integrity.
- `tools/usda_normalization.py`: reads full USDA details, nutrient IDs, energy-method
  precedence, units, missing data and portion metadata.
- `tools/food_matching.py`: conservative food-name/preparation/qualifier matching.
  Synonyms such as chapati/chappatti/roti are explicit; similarity scores do not
  decide ambiguous matches. Original source text retains size, skin and other clues.
- `tools/portion_calculator.py`: explicit edible mass or documented compatible portions.
- `tools/nutrition_calculator.py`: Decimal arithmetic and per-nutrient completeness.
- `agents/nutrition_agent.py`: coordinates these tools; it never asks an LLM for values.
- `adapters/backend_nutrition.py`: consumes an existing backend USDA response as data,
  without importing backend code or making backend/database requests.
- `nutrition_demo.py`: composes food understanding and nutrition, or reads labeled inputs.
- `tests/nutrition/`: offline tests and separately gated live verification.
- `validation/milestone2/`: execution evidence, results and the final validation report.

## Portion and calculation rules

Grams and kilograms are exact mass conversions. All other units require compatible
food-specific portion records. Millilitres/litres are supported only when a record
explicitly supplies a volume-to-weight portion; milk is not assumed to have water's
density. Cups do not become ml without documented measurement context. Bowl, plate,
katori, handful and unfamiliar units remain unresolved without supporting evidence.
Mass ounces are never confused with fluid ounces.

Portion size/form must be stated or explicitly selected. A generic banana does not
silently become medium; a cup of banana does not silently become mashed or sliced.
A generic roti does not silently receive the 'quantity not specified' serving.
FNDDS portions without a numeric amount are used only when the amount is stated
explicitly in their description. Uninterpretable portions are skipped and noted.

For a compatible source portion:

```text
requested edible grams = requested quantity * source gramWeight / source amount
```

For every nutrient:

```text
requested nutrient = source nutrient * requested grams / source basis grams
```

Direct supported USDA records use a 100 g edible-food basis. The backend adapter
uses its returned serving.gram_weight as the basis because those values are already
per serving. It does not multiply the serving factor twice or treat sample presets
as verified data. The adapter retains the backend's claim of attribution; it does
not independently verify caller-supplied backend values against USDA.

Calories are kcal; protein/carbohydrates/fat/fiber are grams. The normalizer uses
nutrient IDs, validates supported units and prefers energy IDs 2048, 2047, 1008, then
1062 (specific Atwater, general Atwater, conventional kcal, energy kJ). It never adds
multiple energy estimates or reconstructs missing calories using guessed factors.
Conflicting duplicates, unsupported units and positive LOQ qualifiers remain unknown
with source notes. A genuinely reported zero remains zero. Unreported fields are null.

Python Decimal is used throughout. Unrounded item contributions are summed before
rounding public values to four decimal places. Decimal fields serialize as JSON
**strings**, preserving decimal values; missing fields serialize as null. This is
intentional in the separate nutrition contract; Milestone 1 numeric types are unchanged.
Database precision does not imply that a person's meal was measured that precisely.

## Result contract and coverage

NutritionResult has schema_version 1.0, items, complete_totals, known_subtotals,
coverage, total_items, resolved_items and questions. Each item retains FoodItem,
compatible candidates, search scope, selected record, basis, portion evidence,
scale factor, calculated nutrients, source notes and unresolved issues.

- `complete`: all five nutrients are known for every food item.
- `partial`: at least one contribution is known, but some item/nutrient is unresolved.
- `needs_clarification`: nothing can yet be calculated and the input needs resolution.
- `no_food`: no food items; totals remain unknown rather than implying zero consumption.
- `error`: all item lookups failed. An error on one item can coexist with partial data.

Each complete total is available only if that nutrient is known for **every** item.
Known subtotals sum only available contributions and never masquerade as full totals.
Coverage reports known_items/total_items for each nutrient; it is **item-count**
coverage, not a percentage of calories, food weight or meal completeness by mass.
Missing fiber need not hide complete calorie totals, but makes the overall result partial.

Common issue codes include ambiguous_food, food_not_found, search_incomplete,
preparation_required, ambiguous_portion, missing_quantity, missing_unit,
incompatible_food_selection, incompatible_portion_selection and missing_nutrients.
Provider errors include usda_credentials_missing, usda_authentication_failed,
usda_rate_limited, usda_timeout, usda_unavailable and invalid_usda_response.

## Tests and separate verification modes

Default tests perform no external USDA calls or real Qwen3 inference:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q --basetemp=agentic_ai/.test-tmp-m2
```

All pre-existing Milestone 1 tests are included. Authentication, rate limits, retries,
malformed responses, missing nutrients, conversions, ambiguity, totals and the backend
adapter are tested using authentic offline records and explicitly synthetic fault cases.
The temporary directory stays inside agentic_ai/ and is owned/managed by pytest.

Opt-in flags are independent:

- NUTRIAI_RUN_LIVE_TESTS=1: the existing twelve actual local Qwen3 regression cases.
- NUTRIAI_RUN_NUTRITION_LIVE=1: actual Qwen3-to-offline-snapshot nutrition cases.
- NUTRIAI_RUN_USDA_LIVE=1 plus USDA_API_KEY: actual external USDA details/search checks.

The USDA checks compare a few current record nutrients/portions against the snapshot;
a legitimate USDA update may require review rather than a code fix. These checks do
not prove the correctness of every record or the match for every possible meal.
See [the validation report](validation/milestone2/REPORT.md) for the actual run status,
including any upstream limitations. Marker names: integration, nutrition_integration,
usda_live. No credential, service or network is needed to run default tests.

## Data gaps and Milestone 3

The snapshot is deliberately small. Unknown Indian recipes and meal components
need another properly documented source or recipe data, not an invented substitute.
The implementation does not estimate cooking yields, edible refuse, container size,
portion density or ingredient recipes. Users must supply edible weights when needed.
Matching is English lexical matching with a small alias set; it can conservatively
reject valid matches. It is not a general semantic food ontology. The extraction agent
can still omit/misinterpret foods; nutrition calculations cannot detect all such omissions.

Milestone 3 should implement a bounded orchestrator and clarification/resubmission
workflow: collect food/portion selections, retain item identity, call tools and expose
an explainable trace. Agree on backend integration before any teammate-owned changes.

References: [USDA API guide](https://fdc.nal.usda.gov/api-guide/),
[Foundation Foods portions and energy documentation](https://fdc.nal.usda.gov/Foundation_Foods_Documentation/),
[USDA API specification](https://fdc.nal.usda.gov/api-spec/fdc_api.html).
