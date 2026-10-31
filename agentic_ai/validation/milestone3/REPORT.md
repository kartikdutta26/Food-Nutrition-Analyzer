# Milestone 3 implementation and validation report

All six approved implementation stages are implemented inside `agentic_ai/`. The existing M1/M2 interfaces, schemas and demonstrations are retained. No dependencies were added. No Git commit, push or merge was performed.

## Validation results

Final full offline regression run: **377 passed, 20 skipped, 0 failed, 0 errors** in 8.55 seconds using the existing virtual environment.

| Suite | Passed | Skipped | Failed | Errors |
| --- | ---: | ---: | ---: | ---: |
| Milestone 1 | 124 | 12 | 0 | 0 |
| Milestone 2 | 133 | 8 | 0 | 0 |
| Milestone 3 | 120 | 0 | 0 | 0 |
| **Total** | **377** | **20** | **0** | **0** |

The 20 skips are intentional: 12 original Ollama integration cases, four Qwen3-to-nutrition integration cases and four live USDA cases require explicit opt-in. All three live-test environment flags were set to `0` for the offline run. The separately recorded actual Qwen3 demonstration is not counted as an automated offline test. M3 tests additionally block TCP connections.

Evidence: [pytest log](offline-tests.log), [JUnit XML](offline-tests.xml), [machine-readable counts](test-summary.json).

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:NUTRIAI_RUN_LIVE_TESTS='0'
$env:NUTRIAI_RUN_NUTRITION_LIVE='0'
$env:NUTRIAI_RUN_USDA_LIVE='0'
.\agentic_ai\.venv\Scripts\python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q -rs --basetemp=agentic_ai/.test-tmp-m3-final-complete --junitxml=agentic_ai/validation/milestone3/offline-tests.xml
```

Two development-only test failures were corrected: an initial quota test used an input that actually fitted within its limit, and a new HTTP mock read the optional `Request.method` attribute instead of calling `get_method()`. The quota checks now use genuinely oversized initial state and authentic record payloads. Neither issue required changes to teammates' code. The final suite has no failed tests.

## Demonstrations actually performed

1. **Scripted offline M3 CLI:** eight JSON output rows. Missing rice quantity resolved to an explicit half-cup; two rotis resolved using the real small-roti portion. Ambiguous apple skin and banana size were selected explicitly. An invalid food ID left state unchanged. A simulated detail-fetch outage recovered using its cached search. Three scenarios ended with complete nutrition results. Output: [offline-demo.jsonl](offline-demo.jsonl).
2. **Existing M2 offline CLI:** all six original example rows ran successfully, including intentional unresolved/partial results. Output: [legacy-nutrition-demo.jsonl](legacy-nutrition-demo.jsonl).
3. **Actual local Qwen3:** `qwen3:4b-instruct` extracted roti and cooked white rice from ?I ate 2 rotis and cooked white rice.? Explicit predefined demonstration replies confirmed USDA small rotis and measured 150 g rice. Final workflow and nutrition status were both `completed`/`complete`, using **one actual Ollama HTTP request**, in **45.09 seconds**. Final calories were **356.4600 kcal**, with USDA IDs **2707713** and **168878**. The stored per-item masses were 54 g for two source-documented small rotis and user-declared 150 g rice. Output: [actual-qwen-snapshot-demo.json](actual-qwen-snapshot-demo.json).

**No live USDA verification was performed for M3.** Actual-Qwen demonstration nutrition came from the existing offline USDA snapshot. A mocked live-provider retry test is not live verification.

```powershell
.\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.orchestration_demo --offline-examples
.\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.orchestration_demo --text "I ate 2 rotis and cooked white rice."
.\agentic_ai\.venv\Scripts\python.exe -B -m agentic_ai.nutrition_demo --offline-examples
```

## Completed behavior

- Secure 256-bit random session IDs with separate server-supplied owner checks on every operation.
- Fixed TTL, active-session capacity, serialized state/global storage quotas, byte-limited requests, bounded turns, steps, tool calls, HTTP attempts and safe trace events.
- Atomic typed replies checked against revision, question, item and offered selections. Invalid/stale/duplicate/cross-item/cross-session requests cannot alter prior results.
- One original extraction, independent checkpoints per food occurrence, targeted source/error recovery and no unnecessary analysis of completed unrelated items.
- Source-identified matching, conservative portions, explicit user evidence and preserved unknown nutrients/coverage.
- Unrounded Decimal checkpoints and non-mutating meal summaries; exact clarification quantities are retained separately from the unchanged M1 float contract.
- Safe, structured execution traces with source IDs, calculation bases and reuse events, excluding prompts, raw tool bodies, exception strings, credentials and private reasoning.
- Pydantic JSON contracts and a storage protocol for a later authenticated FastAPI adapter; no FastAPI/backend changes in this milestone.

[ORCHESTRATION.md](../../ORCHESTRATION.md) explains each major file, the state machine, atomicity, configuration limits and future integration.

## Snapshot and mock classification

Authentic production snapshots are the unchanged ten records in `data/usda/foods.json`: **173424, 173423, 168878, 168877, 173944, 171688, 171689, 171265, 172217, 2707713**. Their source URLs/descriptions/retrieval time are in `data/usda/manifest.json`; the SHA-256 remains `c3fde77650f6b10f4fa2f568a800464b34808cacb7bef239e40ea38a7c768937`.

Scripted raw-food JSON, fault exceptions, edited in-memory nutrients/descriptions, synthetic search envelopes and simulated HTTP responses are test doubles. The mocked HTTP test reuses an authentic saved banana record but performs no network call. No mock nutrient values, weights, densities or recipes were added to production data.

## Limitations and next integration work

- The session store is in memory, loses state on restart and serializes transactions across sessions. It is not a shared multi-worker store or an authentication implementation.
- Memory quotas measure serialized state/cache bytes, with bounded tool response buffers. Python object overhead and the separate Ollama process need deployment-level memory limits.
- The offline catalog has only ten records. Homemade recipes, unknown foods and unsupported volume/portion conversions remain unresolved; no ingredient composition is inferred.
- Structured JSON clarification replies are supported. Arbitrary conversational replies, recommendations and images remain future work.
- Existing M1 float precision is preserved. Explicit clarification quantities use bounded Decimal precision; all intermediate nutrition calculations remain unrounded until public display.
- Live USDA operation still needs credentials/network access and can be rate limited. Live verification remains unperformed in this milestone.

Recommended next step: integrate these contracts through an authenticated backend adapter and durable shared session storage, preserving source evidence and deterministic calculations. Backend modifications would require separate authorization.

## File scope and changed-file list

The only outside-directory Git modification is the **pre-existing** root `.gitignore` change. Its starting and ending SHA-256 are identical: `e62dbd83da4c69dc27a165c14da9130cb37fa48b8a537f626813e771808daeb1`. `backend/` and `src/` were not modified. Snapshot files are unchanged. [scope-audit.json](scope-audit.json) records the branch/HEAD, hashes and checks; [changed-files.json](changed-files.json) lists every new/modified M3 file.

- `agentic_ai/.env.example`
- `agentic_ai/ORCHESTRATION.md`
- `agentic_ai/README.md`
- `agentic_ai/agents/nutrition_agent.py`
- `agentic_ai/clients/ollama_client.py`
- `agentic_ai/clients/usda_client.py`
- `agentic_ai/orchestration/__init__.py`
- `agentic_ai/orchestration/budget.py`
- `agentic_ai/orchestration/clarifications.py`
- `agentic_ai/orchestration/orchestrator.py`
- `agentic_ai/orchestration/state.py`
- `agentic_ai/orchestration/store.py`
- `agentic_ai/orchestration/tracing.py`
- `agentic_ai/orchestration_config.py`
- `agentic_ai/orchestration_demo.py`
- `agentic_ai/orchestration_errors.py`
- `agentic_ai/schemas/orchestration.py`
- `agentic_ai/tests/orchestration/conftest.py`
- `agentic_ai/tests/orchestration/test_atomicity_and_limits.py`
- `agentic_ai/tests/orchestration/test_boundaries.py`
- `agentic_ai/tests/orchestration/test_cli_and_config.py`
- `agentic_ai/tests/orchestration/test_recovery_and_transports.py`
- `agentic_ai/tests/orchestration/test_workflow.py`
- `agentic_ai/tools/nutrition_calculator.py`
- `agentic_ai/tools/portion_calculator.py`
- `agentic_ai/validation/milestone3/REPORT.md`
- `agentic_ai/validation/milestone3/actual-qwen-snapshot-demo.json`
- `agentic_ai/validation/milestone3/changed-files.json`
- `agentic_ai/validation/milestone3/legacy-nutrition-demo.jsonl`
- `agentic_ai/validation/milestone3/offline-demo.jsonl`
- `agentic_ai/validation/milestone3/offline-tests.xml`
- `agentic_ai/validation/milestone3/scope-audit.json`
- `agentic_ai/validation/milestone3/test-summary.json`
