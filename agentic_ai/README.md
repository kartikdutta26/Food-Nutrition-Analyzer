# NutriAI: Food Understanding Agent (Milestone 1)

This package reads a meal description using **local Ollama + qwen3:4b-instruct**
and returns validated food items. It does not retrieve nutrition, estimate
calories, recommend diets, analyze images, or write to the backend/database.
All implementation and test files are contained in `agentic_ai/`.

## Setup and demonstration (Windows PowerShell)

Run commands from the repository root. The existing virtual environment already
contains the required packages. For a fresh environment, install them with:

```powershell
& .\agentic_ai\.venv\Scripts\python.exe -m pip install -r agentic_ai/requirements-dev.txt
```

Start the installed Ollama application and ensure `qwen3:4b-instruct` is available.
No model download is triggered by this package. Run a meal or all five examples:

```powershell
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.demo --text "I ate 2 boiled eggs and 150 g cooked rice"
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.demo --examples
```

The examples cover roti/dal/rice, dosa/sambar, eggs/bananas/milk,
chicken/broccoli, and unspecified paneer curry/rice. Each printed JSON object
includes the original input, exact model tag, result, and elapsed seconds.
A clarification or no-food result exits successfully; configuration/model/input
errors print a JSON error and exit with code 1. Invalid CLI syntax exits with 2.
The examples command continues after a failed example and exits with 1 if any failed.

Optional settings are documented in `.env.example`. Copy it to `agentic_ai/.env`
if needed; that file is already excluded by the repository's existing ignore rules.
Only this package's .env is read; environment variables override it. Nothing reads
backend secrets. Defaults: local port 11434, model qwen3:4b-instruct, 120-second
socket timeout, at most two validation attempts, and a 4,000-character input limit.
A second validation attempt can make total request time approach twice the timeout;
the timeout is per blocking socket operation, not an overall request deadline.

## How the files work together

- `agents/food_agent.py`: asks Qwen3 to identify foods and exact evidence, validates
  its answer, normalizes units, and builds the final result/clarification questions.
  `FoodUnderstandingAgent.analyze(text)` is the main Python interface.
- `clients/ollama_client.py`: sends JSON Schema to Ollama's `/api/chat` endpoint,
  checks completed responses, and translates network/model failures into clear errors.
  It uses Python's built-in HTTP client; an Ollama SDK is not required.
- `schemas/food.py`: Pydantic contracts for model output and public output. Unknown
  fields (including invented nutrients), bad types, overlapping/fabricated source
  spans, and partial decimal/signed/mixed-fraction matches are rejected.
- `schemas/units.py`: defines allowed units, checks measurement words against the
  source, and normalizes explicit counts of common foods to pieces when needed.
- `schemas/quantity.py`: converts explicit decimal/fraction/English-number amounts
  to numbers using Python. Ambiguous or unsupported amounts remain unknown.
- `config.py`: validates environment settings without modifying process environment.
- `errors.py`: provides stable error codes for callers.
- `demo.py`: command-line entry point and realistic sample descriptions.
- `tests/`: offline tests plus a fixed, opt-in live Qwen3 evaluation.
- `requirements.txt`, `requirements-dev.txt`: runtime and development dependencies.
- `pytest.ini`, `.gitignore`: limit test collection to this package and ignore its
  temporary test artifacts. `__init__.py` files make directories Python packages.

The architecture is an explicit workflow: input validation -> model extraction ->
Pydantic/source checks -> Python quantity conversion -> structured result.
It is one specialized agent; multi-agent orchestration is a later milestone.

## Python and JSON contract

```python
from agentic_ai.agents.food_agent import FoodUnderstandingAgent

result = FoodUnderstandingAgent().analyze("I ate 2 boiled eggs")
print(result.model_dump_json(indent=2))
```

Illustrative result (actual model food naming may vary):

```json
{
  "schema_version": "1.0",
  "status": "success",
  "foods": [{
    "name": "egg",
    "quantity": 2.0,
    "quantity_text": "2",
    "unit": "piece",
    "preparation": "boiled",
    "source_text": "2 boiled eggs",
    "issues": []
  }],
  "questions": []
}
```

`status` is `success`, `needs_clarification`, or `no_food`. Missing quantities and
preparations use JSON null. Issues are `missing_quantity`, `unresolved_quantity`,
`invalid_quantity`, or `missing_unit`. Zero/negative/over-limit quantities become
null and require clarification. Repeated foods stay separate in input order.
Each source_text is an exact, non-overlapping input substring. The model supplies
quantity_text as source evidence; Python derives the numeric quantity from it.
If Qwen quotes a measured amount such as 'half a cup', the parser removes only
the suffix matching its validated unit before converting the number. Unstated
measurement units are cleared, and preparation labels must match a complete
word/phrase in the item's original source text.
Counting eggs/rotis as pieces is unit normalization, not a weight estimate.
When Qwen leaves units unknown, a small explicit-count normalizer covers common
eggs, fruit, roti/chapati, dosa/idli, pancakes, sandwiches and cookies. Other foods
remain the model's responsibility; unfamiliar count phrases require clarification.

`recognize_food(text)` remains as a convenience function, but its old prototype
list return value has intentionally changed to `FoodUnderstandingResult`.
Call `.model_dump()` for a dictionary. No backend integration uses this function yet.
The public JSON Schema is available from `FoodUnderstandingResult.model_json_schema()`.

Errors raise a subclass of `FoodUnderstandingError`. CLI errors use:
`{"status":"error","error":{"code":"ollama_timeout","message":"..."}}`.
Codes: `invalid_input`, `configuration_error`, `ollama_unavailable`,
`ollama_timeout`, `model_not_found`, `invalid_model_response`, `ollama_service_error`.
Only malformed model responses get a bounded repair attempt. Connection/service
failures are returned immediately, without a hidden regex or sample-data fallback.
Raw upstream error bodies are not exposed.

## Testing

Offline tests require no Ollama, API key, database, or internet:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q --basetemp=agentic_ai/.test-tmp
```

The explicit base temp directory keeps pytest's configuration-test files inside
`agentic_ai/`. Use that directory only for pytest; pytest manages its contents.
Caching is disabled in pytest.ini. Integration tests are skipped by default.
To run only actual model inference tests:

```powershell
$env:NUTRIAI_RUN_LIVE_TESTS = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/test_live_ollama.py -q -s
Remove-Item Env:NUTRIAI_RUN_LIVE_TESTS
```

`tests/live_cases.json` records the inputs and expected quantities/units/statuses.
These are fixed acceptance examples, not evidence of general accuracy. Live
results can change with model weights, Ollama version, or hardware. Offline tests
check program behavior; live tests separately check the installed language model.

Validation evidence and measured live results are recorded in `validation/REPORT.md`.

## Limits and next milestone

- This is primarily English meal extraction; common Indian dish names are supported
  by the model, but Hindi/Hinglish or other languages have not been evaluated.
- Supported quantity normalization includes decimals, ordinary/mixed/Unicode
  fractions, basic English numbers up to ninety-nine, and common fraction words.
  Ranges, approximate amounts, large number-word expressions and unfamiliar wording
  require clarification. Scientific notation and decimal commas are not assumed.
- Schema/source validation cannot prove that every food was found or that a
  normalized name, unit, preparation, or quantity phrase is semantically correct.
  Prompt-injection instructions are treated as data, but this is not a guarantee
  against all model mistakes. Review the extracted result before later calculations.
- A successful extraction does not mean a portion is ready for nutrition lookup:
  cups, bowls, katoris, pieces, and recipes still need verified food-specific weights.
  The package never invents those weights, ingredients, or nutritional values.
- Input/output/item limits bound requests. Long or complex descriptions may fail
  validation or hit the model token limit. No conversation memory or clarification
  continuation is implemented yet; resubmit a more specific description.

Next: implement verified nutrition lookup and deterministic portion calculations,
with source IDs, unknown-food handling, and explicit portion clarification. Agree
on the backend adapter contract before any teammate-owned code changes.

References: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[Ollama chat API](https://docs.ollama.com/api/chat),
[Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/).
