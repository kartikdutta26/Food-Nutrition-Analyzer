# Milestone 4: Nutrition Recommendation Agent

M4 is a separate, deterministic interpretation layer over existing M2 `NutritionResult` and M3 `SessionResponse` values. It does not run extraction, a model, USDA retrieval, an orchestrator action, or persistence. Existing M1-M3 contracts and code are unchanged. No dependency, environment variable, paid API, or running service is required beyond the existing Python environment.

## Public interface

```python
from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent
from agentic_ai.recommendation_errors import RecommendationError

agent = NutritionRecommendationAgent()
result = agent.recommend(nutrition_result)
result = agent.recommend_session(session_response,
    expected_revision=session_response.revision)

# Typed objects or their JSON-shaped dictionaries are accepted above.
# The versioned envelope also accepts a JSON string/bytes or a dictionary:
result = agent.recommend_request({
    "schema_version": "1.0",
    "source": {"kind": "nutrition", "result": nutrition_result.model_dump(mode="json")},
    "context": {"preferences": [], "targets": []}
})
```

`RecommendationRequest` and `RecommendationResult` live in `schemas/recommendation.py`. Schema and ruleset versions are both `1.0`. Extra envelope/context fields are rejected. Use `model_dump_json()` for Decimal-safe JSON; nutrition and target Decimals serialize as strings. M1's public food quantity remains its original strict float contract; exact M3 clarification quantities remain Decimal evidence and are used when reconstructing the original calculation.

`recommend_session` also preserves accepted clarification evidence, including request IDs, actions and their revisions. Current questions, rather than historical extraction questions, determine actionable next steps. Returned question IDs, item IDs, indices and allowed actions refer to existing M3 questions. They do not authorize actions or modify a session.

The optional expected revision is checked against the supplied response. M4 cannot discover a newer server revision. A future authenticated adapter must retrieve the latest owner-scoped session, supply an expected revision, and discard results if account/session/revision changes. M4 has no ownership, authentication or storage responsibilities.

## Output contract and interpretation

| Field | Meaning |
| --- | --- |
| `status` | `ready`, `limited` or `unavailable`; never a health or nutrition score |
| `generation_mode` | Always `deterministic` |
| `validation_scope` | Always `supplied_record_consistency_only` |
| `input_ref` | SHA-256 of normalized input, source kind, session ID/revision/status/expiry when supplied |
| `context` | Explicit preferences and targets, preserved without inferred goals |
| `nutrition_status`, `complete_totals`, `known_subtotals`, `coverage` | Independent copies of validated upstream values |
| `facts` | Meal and per-item nutrient amounts, units, coverage, basis and source references |
| `observations` | Controlled composition statements and eligible arithmetic comparisons |
| `suggestions` | Evidence review, missing-data clarification and optional benchmark interpretation |
| `next_steps` | Existing clarification actions, retry/new-analysis/expiry/terminal guidance |
| `limitations` | Explicit scope, uncertainty, missing context and source-quality notices |
| `citations` | Supplied USDA provenance, original nutrient evidence/basis, portion, scale and raw source issues |
| `session_evidence` | Copied accepted M3 clarification actions; empty for M2 input |
| `comparisons` | Target scope, relation, reason and supporting fact reference |

`ready` means complete usable supplied nutrition without source-quality limitations or skipped target comparisons. It does not establish a healthy meal, recipe accuracy, target suitability, or independent USDA verification. Missing optional targets do not make a complete result unavailable.

`limited` retains usable known information while identifying partial coverage, source notes, incomplete session processing or ineligible target comparisons. A terminal session with retained usable facts is limited: no further reply/retry is proposed. A waiting-for-retry session can retain already known facts, while offering only the upstream retry operation.

`unavailable` means no nutrient amounts are usable, or the supplied session has expired. Expired evidence remains visible for inspection, but current observations and suggestions are suppressed. Empty meals and unknown nutrients remain unknown, not zero.

Facts use stable IDs such as `meal-calories` and `item-0-fiber`; citations use `source-0`. Message `evidence_refs` link to these IDs, or the explicit `input`/`context` boundary. Citations are source attributions, not scientific guideline citations. Food names and complete extraction context remain in the supplied M2/M3 input; consumers can join by item index. Source descriptions/issues and preference labels are untrusted metadata, never instructions or recommendation prose. Any future renderer must escape them as plain text.

## Explicit targets and preferences

```python
result = agent.recommend(nutrition_result, context={
    "preferences": ["vegetarian"],
    "targets": [{
        "nutrient": "protein", "value": "20", "unit": "g", "scope": "meal"
    }]
})
```

The five supported nutrients are `calories` (kcal), `protein`, `carbs`, `fats`, `fiber` (g). Targets must be positive, finite, no greater than 1,000,000,000, with at most 12 decimal places. Supply at most one target per nutrient. A scope is required; no BMR, daily allowance, remaining intake, default target or goal is inferred.

Only a meal-scoped target with complete coverage for its nutrient is compared. A complete calorie value can be compared even if fiber is missing. Known subtotals are never compared as though complete. Daily targets are preserved but explicitly not compared to a single meal. The arithmetic terms `below`, `equal` and `above` describe the supplied benchmark, not clinical adequacy or a recommendation to eat more/less.

Preferences are retained and acknowledged. This foundation does not prescribe foods, quantities or substitutions, and does not assert allergen safety or that a meal satisfies a dietary restriction. There is no personalized diet plan, medical advice, diagnosis, treatment, supplement advice, nutrition score or weight-loss promise. Evidence-linked practical suggestions concern completing clarification, checking contributing records and interpreting explicitly supplied benchmarks.

## Deterministic consistency and safety

1. Bound and revalidate the entire input, including nested Pydantic instances. Reject nonfinite/negative nutrient values, booleans in numeric evidence, excessive precision, unsupported fields, duplicate JSON keys, excessive depth/size and stale expected revisions.
2. Require sequential item indices, coherent session state/questions, unique accepted request IDs and valid accepted revision ranges.
3. Check canonical USDA FDC links, source metadata, snapshot hash shape, source IDs, candidate/record consistency, nutrient IDs, known/missing nutrient evidence and unit conversions. Backend-attributed records explicitly retain their delegated trust boundary.
4. Reconstruct portion arithmetic using the existing pure M2 resolver and documented source portions. Check quoted quantities against M1 source text, except accepted exact M3 quantity replies, which intentionally retain original extraction text. M3 measured-gram resolutions require matching accepted measurement evidence. No new quantity is generated.
5. Recalculate item values with Decimal from the supplied source record. Recreate unrounded contributions, then use M2's existing sum-before-rounding behavior. Compare all public item values, scale factors, complete totals, known subtotals, coverage, counts, status and questions. M4 does not alter those upstream values.
6. Build facts/citations from validated copies. Unknown stays `None`/JSON `null`; a documented zero remains zero. Coverage counts items, not mass, certainty or dietary adequacy.
7. Apply an allowlisted local rule catalog and fixed templates. Only validated amounts, units, nutrient names, relation enums and question indices are interpolated. Raw descriptions, model text, error strings, source notes and preference text cannot become advice. Audit every generated message against the controlled template and validate references before returning a full output.
8. Return a stable `RecommendationError.code` and fixed safe message on failure. Do not return partial/truncated output after a safety or output-limit failure. The CLI emits structured errors without source contents, file paths or tracebacks.

These are internal consistency checks, not proof that a client supplied genuine USDA records or genuine user measurements. A self-consistently forged entire input cannot be detected by a pure offline interpreter with no independent trusted source. Snapshot hashes are preserved provenance, not signatures; M4 does not reread or attest the upstream snapshot. M2 standalone measured grams are declared upstream user input, not independently verified measurements. Public M3 evidence does not expose a private item-ID mapping for every completed item, so matching accepted quantities/measurements is a consistency check, not independent attribution proof. Future integration must use trusted, server-owned M2/M3 outputs and authorization outside M4.

The agent does not make an Atwater 4/4/9 equality check: USDA energy may use different factors, and no unsupported energy calculation is substituted for supplied evidence. No generalized nutrient-deficiency thresholds or clinical guidance is introduced. Future dietary/clinical rules would need separately reviewed evidence, population/context boundaries and acceptance tests.

## Bounds and safe errors

Defaults in `RecommendationSettings` can be lowered, not expanded beyond their hard maxima:

| Bound | Default maximum |
| --- | ---: |
| Serialized input | 4 MiB |
| Serialized complete output | 2 MiB |
| Meal items | 40 |
| Generated messages across all categories | 128 |
| Traversed input nodes / depth | 100,000 / 32 |
| Any input list / string | 1,000 / 4,000 characters |
| Portions per record | 200 |
| Preference labels | 30, each 1-80 characters |
| Explicit targets | 5 |

Numeric precision/exponents are bounded before Decimal arithmetic. Fixed error codes are `invalid_input`, `inconsistent_nutrition`, `invalid_evidence`, `stale_revision`, `input_limit`, `output_limit`, `invalid_rules`, and `recommendation_failed`. Invalid inputs raise errors rather than being mislabeled as an ordinary unavailable meal. Large valid upstream sessions may exceed M4's limits and require a separately approved bounded adapter; evidence/warnings are never silently removed.

The output is detached from its inputs. Top-level M4 schemas are frozen, but nested existing M2/M3 models retain their original mutability; callers can change returned copies without changing the input or orchestrator state. The agent stores no session history and has no mutable recommendation cache.

## CLI demonstration

From the repository root in PowerShell, using the existing environment:

```powershell
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.recommendation_demo --offline-examples
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.recommendation_demo --input-json path/to/m2-result.json
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.recommendation_demo --input-json path/to/m3-response.json --kind session --expected-revision 2
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.recommendation_demo --input-json path/to/request.json --kind request
```

For M2/M3 input, `--context-json` accepts a context object like the example above. A complete request already contains context/revision; additional CLI context/revision arguments are rejected. The CLI only reads requested input files and writes stdout. Exit 0 means a valid ready/limited/unavailable result; exit 1 means a safe structured error. Argparse usage errors retain its normal exit 2 behavior.

The six offline examples use the **existing authentic USDA snapshot** and existing curated extraction fixtures. Only the explicit demo fixture builder invokes M2 to construct inputs. The recommendation agent itself does not retrieve USDA data. Every example is labeled as curated extraction, snapshot-backed nutrition and deterministic interpretation; it is not a real Qwen3 inference run or live USDA verification.

Observed snapshot demo results:

| Example | M4 status | Complete calories (kcal) | Known subtotal (kcal) | Coverage |
| --- | --- | ---: | ---: | --- |
| Eggs and cooked rice | ready | 350.0000 | 350.0000 | 2/2 |
| Small rotis and cooked rice | limited | 264.1600 | 264.1600 | 2/2; source-quality notes retained |
| Medium banana | ready | 105.0200 | 105.0200 | 1/1 |
| Milk requiring clarification | unavailable | unknown | unknown | 0/1 |
| Banana and unresolved paneer curry | limited | unknown | 89.0000 | 1/2 |
| Ambiguous apple | unavailable | unknown | unknown | 0/1 |

## Validation and implementation files

Run all M1-M4 tests from the repository root:

```powershell
$m4TestTemp = Join-Path (Get-Location) ('agentic_ai\.test-tmp-m4-' + [guid]::NewGuid().ToString('N'))
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -q agentic_ai/tests -rs --basetemp=$m4TestTemp
```

The unique ignored temporary directory avoids the existing inaccessible shared Windows pytest temp directory. Test artifacts are not source or committed data. Live integrations remain opt-in under existing M1-M3 markers; M4 tests block network access. Fixtures use authentic committed snapshots, with explicitly labeled in-memory synthetic mutations for failure/precision tests. Snapshot files themselves are unchanged.

Tests cover complete/partial/empty nutrition, all-unknown and true-zero values, missing fiber, unrounded summation, unit conversions, delegated backend evidence, changed totals/coverage/portions/source metadata, fabricated quantities, stale revisions, exact M3 replies, measured grams, expiry, failure/retry states, input/output limits, immutability, target scope, preference preservation, prompt injection, unauthorized rule wording, malformed catalogs and CLI successes/failures.

Verified in the existing Python 3.14 / Pydantic 2.14.2 / pytest 9.2.0 environment:

- Full M1-M4 suite: **514 passed, 0 failed, 20 skipped** (10.78 seconds).
- New M4 suite: **137 passed, 0 failed, 0 skipped** (7.73 seconds).
- The unchanged M1-M3 portion accounts for **377 passed, 20 skipped** within the full run.
- Skips: 4 opt-in live USDA checks and 16 opt-in actual local Qwen3 checks. No real Qwen3 check was needed for this model-free foundation; none was run or claimed.
- The real CLI subprocess completed all six labeled snapshot examples, exit 0, empty stderr.
- No pytest warnings were emitted by the successful final runs. Earlier attempts exposed an inaccessible shared pytest temp directory; the unique ignored test-directory command above resolved it without permissions or source changes.
- SHA-256 checks confirmed all 229 pre-existing tracked/untracked files were byte-for-byte unchanged, including all 73 pre-existing local-preview files. The pre-existing two ignore-file edits were preserved. All 20 additions are M4 source, schemas, rules, tests or this document under `agentic_ai/`; generated test directories were removed after validation.
- Branch remains `agentic-ai`, HEAD remains `bc352f3bf4f78db0f641511cd82b87b78dc1cbf7`. Nothing is staged or committed.

New implementation files only:

- `agents/recommendation_agent.py`: public stateless API and output safety audit.
- `schemas/recommendation.py`: versioned request/result/context/fact/citation/message/target contracts.
- `recommendation_config.py`, `recommendation_errors.py`: bounded settings and safe errors.
- `recommendation/__init__.py`, `validation.py`, `evidence.py`, `rules.py`, `rendering.py`: consistency validation, evidence extraction, deterministic eligibility and controlled wording.
- `data/recommendation_rules.json`: versioned allowlist; no default nutrition values or clinical thresholds.
- `recommendation_demo.py`: existing-result JSON CLI and labeled authentic snapshot examples.
- `tests/recommendation/__init__.py`, `conftest.py`, `test_facts.py`, `test_validation.py`, `test_targets_and_safety.py`, `test_sessions.py`, `test_cli.py`, `test_source_boundaries.py`: offline regression coverage.
- `RECOMMENDATIONS.md`: interfaces, examples, evidence boundaries and validation report.

No M1-M3, local_preview, frontend, backend, authentication, database or dependency files are modified. No model ranking, onboarding, API adapter, database migration, service startup, commit or remote operation is part of M4.

Future work requires separate approval: a trusted application adapter with ownership/revision checks; any reviewed dietary suggestion catalog; and optional Qwen3 ranking constrained to approved deterministic candidates. Qwen3 ranking must not become a source of nutrition facts or unrestricted recommendation text.
