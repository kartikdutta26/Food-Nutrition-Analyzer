# Milestone 1 validation

Validated on 2026-10-31 (user's Asia/Calcutta date).

Milestone 1 is complete: the package extracts foods using a real local Qwen3
model, validates its output with Pydantic, normalizes explicit quantities, and
returns clarification questions for missing/invalid amounts. Nutrition lookup,
recommendations, images, and multi-agent orchestration are not part of this milestone.

## Environment

- Python 3.14.0 in agentic_ai/.venv
- Pydantic 2.14.2, python-dotenv 1.2.4, pytest 9.2.0
- Ollama 0.40.13 at http://127.0.0.1:11434
- Model qwen3:4b-instruct
- Model digest: 0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0
- Temperature 0; thinking disabled; JSON Schema supplied to /api/chat
- No additional packages or models were installed during this implementation.

## Final test run

**136 passed; zero failures/errors/skips**, in 131.29 seconds:

- 124 offline tests: input validation, quantities, schema/evidence checks, repeated
  foods, preparation/unit grounding, configuration, CLI behavior, bounded retries,
  and simulated connection/timeout/HTTP/malformed-response failures.
- 12 actual Ollama inference acceptance tests: Indian roti/dal/rice, dosa/sambar,
  decimal breakfast, chicken/broccoli, missing/ambiguous amounts, repeated apples,
  mixed fractions, Unicode fractions, negative quantities, quantity ranges,
  non-food input, and an embedded instruction attempt.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUTRIAI_RUN_LIVE_TESTS = '1'
& .\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q --basetemp=agentic_ai/.test-tmp-final --junitxml=agentic_ai/validation/test-results.xml -o junit_logging=system-out
```

Evidence:

- [test-results.xml](test-results.xml): final complete test results and captured live output.
- [live-results.json](live-results.json): actual structured output from all 12 passing live cases.
- [initial-live-tests.xml](initial-live-tests.xml): an earlier development run with
  two omitted-count-unit failures. These were fixed and rerun in the final report;
  this file is retained as development evidence, not the current test status.

## Final command-line demonstration

The actual CLI was also run successfully on all five built-in examples, using
qwen3:4b-instruct. Four complete descriptions returned success. The deliberately
underspecified paneer/rice example correctly requested clarification. CLI exit: 0.

```powershell
& .\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.demo --examples
```

Full output is in [demo-results.json](demo-results.json).
A question mark below means unknown, not zero.

| Input | Extracted quantities/units/foods | Status | Seconds |
| --- | --- | --- | --- |
| For lunch I ate 2 rotis, 1/2 cup dal tadka and 150 g cooked rice. | 2.0 piece roti, 0.5 cup dal tadka, 150.0 g rice | success | 21.47 |
| I had one masala dosa and half a cup of sambar. | 1.0 piece masala dosa, 0.5 cup sambar | success | 14.66 |
| Breakfast was 2 boiled eggs, 1.5 bananas and 250 ml milk. | 2.0 piece boiled eggs, 1.5 piece bananas, 250.0 ml milk | success | 21.63 |
| Dinner was 120 g grilled chicken and one and a half cups of steamed broccoli. | 120.0 g grilled chicken, 1.5 cup steamed broccoli | success | 17.55 |
| I ate paneer curry and some rice. | ? ? paneer curry, ? ? rice | needs_clarification | 9.65 |

## Interpretation and remaining limits

These results establish behavior on the fixed acceptance set, not a general
accuracy percentage. The five CLI examples overlap that set and are not five
additional independent evaluation cases. Error-path tests use simulated failures;
they did not require shutting down the user's Ollama server.

During development, actual model output sometimes included units in quantity_text,
omitted count units, or supplied unstated preparation. The final implementation
handles measured quantity phrases, uses a conservative common-food count normalizer,
and clears preparation/measurement labels without matching source evidence.

The model can still omit foods or misinterpret their meaning. Source checks do
not prove semantic correctness or extraction completeness. English/common Indian
dish names were evaluated; other languages were not. Unfamiliar quantities and
units require clarification. Counts/cups/bowls/katoris do not imply gram weights.
No nutrition data or recommendations are generated. Cold model startup may be
slower than these warm-run timings.

All changes and evidence are inside agentic_ai/. backend/, src/, the repository
README, and teammates' files were not edited. The pre-existing root .gitignore
change was left untouched. No commit or push was performed.

Next milestone: verified nutrition lookup and deterministic portion calculations,
with source attribution and food-specific serving weights. Agree on the backend
adapter contract with the backend teammate before modifying backend interfaces.
