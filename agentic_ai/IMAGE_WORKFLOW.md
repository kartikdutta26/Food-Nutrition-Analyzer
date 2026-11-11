# M5.5: standalone image-to-nutrition coordination

`ImageNutritionWorkflow` composes unchanged M5.2 preprocessing, the M5.3 image
candidate agent, M5.1 explicit confirmation, M3 stateful orchestration (including
M1 extraction and M2 calculations), and M4 deterministic recommendations.
No model installation, actual vision inference, application integration,
authentication, database or dependency change is required for the offline demo.

## Interfaces and files

| New file | Responsibility |
| --- | --- |
| `image_workflow.py` | Bounded owner-scoped workflow records, one-time confirmation, delegation to M3/M4 |
| `image_workflow_config.py` | Strict metadata/output/capacity/TTL ceilings |
| `image_workflow_errors.py` | Fixed safe workflow errors |
| `schemas/image_workflow.py` | Additive `ImageWorkflowSnapshot` envelope around existing contracts |
| `image_workflow_demo.py` | Clearly labeled offline simulation and authentic snapshot demonstrations |
| `tests/image_workflow/__init__.py` | Test package |
| `tests/image_workflow/conftest.py` | Generated pixels, scripted clients, authentic snapshot fixtures, blocked network |
| `tests/image_workflow/test_confirmation.py` | Exact result binding, explicit text, replay and concurrent confirmation |
| `tests/image_workflow/test_workflow.py` | Complete/partial nutrition, clarification, unknowns, provenance and revisions |
| `tests/image_workflow/test_guards.py` | Ownership, TTL, quotas, failure/retry and nonmutation safeguards |
| `tests/image_workflow/test_demo.py` | Complete/partial CLI and disclosure checks |
| `IMAGE_WORKFLOW.md` | Usage, trust boundaries and validation |

All files are additive under `agentic_ai/`; M1-M5.3 code and public contracts are
unchanged. There is no new nutrition formula, caption extractor, default target,
medical guidance, hidden ingredient inference or image-derived serving weight.

```python
from agentic_ai.image_workflow import ImageNutritionWorkflow

# Existing trusted components: explicitly inject both. The coordinator does not
# silently create a model client or choose a different extraction implementation.
workflow = ImageNutritionWorkflow(
    vision_agent=image_food_agent,      # Existing ImageFoodRecognitionAgent
    orchestrator=agent_orchestrator,    # Existing AgentOrchestrator
)
pending = workflow.begin(local_image_path, owner=trusted_owner)

# STOP: present pending.recognition, its alternatives, uncertainties and questions.
# Collect an independent user description, explicit choices and acknowledgments.
started = workflow.confirm(pending.workflow_id, user_confirmation, owner=trusted_owner)

# Preserve M3 questions and allowed actions. User actions are existing ReplyRequest
# objects/dicts with expected_revision, request_id, question_id, item_id and action.
updated = workflow.respond(pending.workflow_id, user_reply, owner=trusted_owner)
interpreted = workflow.recommend(
    pending.workflow_id, owner=trusted_owner,
    expected_revision=updated.session.revision,
    context=explicit_user_context,  # Optional; never automatically populated.
)
current = workflow.get(pending.workflow_id, owner=trusted_owner)
workflow.close(pending.workflow_id, owner=trusted_owner)
```

The constructor also accepts an existing `NutritionRecommendationAgent` as
`recommendation_agent=` and validated `ImageWorkflowSettings` as `settings=`.
Dependencies are trusted Python code. Normal vision use must follow the existing
M5.3 readiness and resource checks; this stage does not run that model.
`retry(workflow_id, retry_request, owner=...)` delegates an unchanged M3
`RetryRequest` for a session in `waiting_for_retry`. It does not rerun vision or
reconfirm a different caption. M3 decides which failed stage must be retried.

Each returned `ImageWorkflowSnapshot` has schema version `1.0`, workflow ID,
expiry, phase (`awaiting_confirmation`, `session_started`, `start_failed`), the
original M5.1 recognition, optional `ConfirmedImageMeal`, current M3
`SessionResponse` and optional M4 `RecommendationResult`. Actual M3 status and
nutrition completeness remain in `session`; `session_started` is not a claim of
completed or complete nutrition. Nested M3 models retain their original mutable
contract but are independent copies, never references to stored state.

## Confirmation and ownership

- `begin()` performs the existing preprocessing and vision-candidate path only.
  It stores bounded serialized recognition metadata, not original/processed
  pixels, base64, private paths or raw model replies. M1/M3 are not called yet.
- `confirm()` retrieves the workflow's own stored recognition. It never accepts
  a replacement recognition result, nutrition payload or client-chosen M3 ID.
  Existing `prepare_confirmation` checks exact recognition ID/revision, original
  image hash, canonical result fingerprint, question acknowledgments, group
  choices, corrections/exclusions and confirmed-text spans. All quantities and
  preparation must come from independent explicit text or later M3 replies.
- `to_m3_start_request` is called only after successful explicit confirmation;
  the coordinator fixes `provider="snapshot"`. Only the user's confirmed text
  becomes `StartRequest.text`. Model hypotheses remain separate in recognition
  and handoff records. Uncertain/no-food results still require explicit manual
  confirmation and can be corrected or overridden using M5.1's existing rules.
- A valid confirmation is consumed **before** invoking M3. One process-local
  lock prevents concurrent/replayed confirmation from making multiple M3 starts
  for a workflow. Malformed confirmation does not consume the workflow. If M3
  start raises an exception, phase becomes `start_failed`; further confirmation
  is rejected even when it is uncertain whether M3 created a session. No silent
  rollback or blind start retry is attempted. A deliberate new workflow may be
  needed after resolving the failure.
- Every method requires owner context out of band. Owner hashes are compared
  before access; M3 receives the same trusted owner for start/get/respond/retry/
  close. Unknown and foreign workflow IDs have the same error. No owner is taken
  from confirmation or request-body fields. A local string is **not login**;
  future authenticated adapters must derive it from their verified identity.
- Bindings and fingerprints are not signatures or proof of a real human action.
  M5.1 cannot establish human intent, vision correctness or secret-key-backed
  authenticity. Caller-generated altered hashes, mismatched revisions/choices,
  stale results and replay after consumption are rejected within these bounds.

The offline demo's `demo_confirmation` helper represents a **scripted DEMO
USER** choosing known fixture labels and supplying separately scripted text.
It is never called by the coordinator. Do not use it as an automatic production
confirmation builder for model-generated captions. Real application code must
collect explicit independent user actions.

## Clarification, nutrition and recommendations

The coordinator does not interpret or fill M3 questions. Existing M3 actions
handle quantities, user-measured grams, preparation, offered USDA food/portion
selection, refinement and leaving an item unresolved. M3 preserves original
extraction and clarification evidence, request IDs, revision increments and
cached checkpoints. A reply/retry with stale revision, duplicate request ID,
wrong item/question or invalid offered choice is rejected by M3.

Only existing M2/M3 computes nutrition. The default snapshot provider verifies
`data/usda/foods.json` against its existing manifest, retains FDC IDs, source
descriptions, URLs, retrieval time, nutrient evidence, reference basis and snapshot
hash, and never queries live USDA. Unknown nutrients remain `None`, not zero.
Incomplete items produce known subtotals and item coverage, not complete meal
totals. Homemade paneer curry has no matching verified record in the small offline
catalog; its recipe or nutrients are not invented.

`recommend()` requires an explicit expected M3 revision. It retrieves an
owner-scoped current session, passes a detached copy to the unchanged M4
`recommend_session`, and checks that neither the copy nor the current session
changed during generation. M4 validates nutrient arithmetic and source/portion
evidence, and retains its `supplied_record_consistency_only` validation scope.
Invalid evidence raises an error instead of yielding fabricated recommendations.
M4 limitations, unknown facts, coverage, citations and `ready`/`limited`/
`unavailable` status are preserved. Explicit preferences/targets are optional;
none are inferred from the image. Daily targets are not reinterpreted as meal
targets.

There is **no recommendation cache**. `get`, `respond` and `retry` return
`recommendations=None`. A caller must request guidance at the current revision
and discard an older displayed result after a session changes. Previously
returned snapshots are historical copies; they are not mutated behind the
caller's back. Final revision/read checks cannot provide a cross-process atomic
snapshot when callers mutate an externally shared orchestrator immediately after
the check. Durable application integration needs a shared transaction design.

## Bounded lifetime and failure behavior

| Setting | Default | Hard maximum |
| --- | ---: | ---: |
| `max_workflows` | 20 | 100 |
| `ttl_seconds` | 1800 | 86400 |
| `max_metadata_bytes` per workflow | 262144 | 262144 |
| `max_store_bytes` serialized recognition/handoff data | 4194304 | 16777216 |
| `max_output_bytes` full response | 8388608 | 8388608 |

Settings are strict/frozen and can be lowered. No .env file is read. The count
bound applies before vision calls; metadata/output failures return no truncated
result. Existing M5.1/M5.2/M5.3 and M3/M4 limits still apply independently.
Owner strings are bounded to 256 UTF-8 bytes. One global `RLock` serializes
workflow operations, including dependencies, matching the simple existing M3
store's concurrency model. This is a standalone correctness-first implementation,
not a scalable web service or hard CPU/memory sandbox.

Workflow TTL starts after recognition and is shortened to M3's session expiry
after confirmation. Slow operations cannot resurrect expired workflow records.
Expiry purges workflow metadata; underlying M3 sessions also have their own
bounded TTL and store limits. Explicit `close()` closes an attached owner-scoped
M3 session and drops the workflow. Expired workflow metadata can leave a session
until its native M3 TTL, and an ambiguous start exception can leave an unlinked
session; there is no distributed transaction across the two stores. Restarting
the process loses workflow/replay state. There is no cross-process/durable replay
ledger, recovery of a lost workflow by a client-supplied session ID, or database
migration in this stage.

New `ImageWorkflowError.code` values are `invalid_configuration`, `invalid_owner`,
`workflow_not_found`, `workflow_limit`, `metadata_limit`, `output_limit`,
`confirmation_required`, `confirmation_consumed`, `stale_revision`,
`invalid_revision`, `dependency_mutation` and `operation_failed`. Existing safe
vision/image/confirmation/M4 error classes and allowlisted M3 error codes remain
distinguishable; unexpected dependency messages are not exposed. M3's structured
retry/terminal errors remain in its session response. A failure after a real M3
side effect (for example an output-size error) does not roll back nutrition or
make confirmation reusable. The caller can inspect/close the workflow where its
bounds/lifetime permit. No module logs private paths, pixels or model replies.

## Offline CLI and provenance

```powershell
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.image_workflow_demo --scenario complete
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.image_workflow_demo --scenario partial
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.image_workflow_demo --scenario all
```

The CLI generates a small synthetic RGBA PNG in an ignored temporary directory
under `agentic_ai/`, uses actual M5.2 stripping/RGB conversion/hash generation,
and cleans up that directory. Simulated vision yields declared candidate groups
unrelated to the synthetic pixels. M1's transport supplies finite scripted raw
JSON keyed by the explicit demo-user text; the real FoodUnderstandingAgent still
validates source spans, quantities and units. No visual accuracy or live Qwen3
extraction is implied. Placeholder vision digest (`sha256:` plus 64 zeroes) and
Ollama version (`0.0.0`) are labeled synthetic, never observed installed identity.
Each JSON report includes an explicit component-by-component `disclosure`.

Both demonstrations run real existing M3, M2 and M4 with authentic snapshot
records, **not live USDA validation**. Snapshot source: USDA FoodData Central;
existing retrieval timestamp `2026-10-31T09:29:54.430152+00:00`, CC0-1.0,
`foods.json` SHA-256
`c3fde77650f6b10f4fa2f568a800464b34808cacb7bef239e40ea38a7c768937`.
These are database reference values, not laboratory verification of a photograph.

| Demonstration | Explicit demo-user input and clarification | Actual result |
| --- | --- | --- |
| Complete, two foods | Confirms `banana and eggs`; later supplies 100 g banana, boiled preparation and 100 g eggs | M3 completed at revision 4; nutrition complete; M4 ready; 244.0000 kcal, 13.6700 g protein, 23.9600 g carbs, 10.9400 g fat, 2.6000 g fiber |
| Partial, two foods | Confirms `100 g banana and paneer curry`; explicitly leaves the unsupported curry unresolved | M3 completed at revision 2; nutrition partial; M4 limited; **all complete meal totals null**; known subtotal 89.0000 kcal, 1.0900 g protein, 22.8400 g carbs, 0.3300 g fat, 2.6000 g fiber; coverage 1 of 2 items |

Complete-case citations are FDC **173944** (`Bananas, raw`) and **173424** (`Egg,
whole, cooked, hard-boiled`). Partial-case nutrition cites FDC **173944** only.
Neither serving amount comes from the image or the vision candidate response.
CLI output includes transitions, separate recognition and confirmed text, the
actual session/evidence, nutrition and M4 result. CLI user actions are scripts,
not interactive login or a real human confirmation. No Supabase/MongoDB or
application credentials are used.

## Deterministic tests

```powershell
$m55Temp = 'agentic_ai/.test-tmp-m55-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/image_workflow -q -rs --basetemp=$m55Temp
$m55FullTemp = 'agentic_ai/.test-tmp-m55-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q -rs --basetemp=$m55FullTemp
```

New tests block socket connections and use generated pixels, explicitly simulated
vision/M1 clients and authentic snapshot calculations. The missing-fiber test
uses an explicitly marked synthetic omission of fiber **and its evidence** on a
detached provider record; it never alters fixture files or claims that the
original snapshot lacks fiber. Provider outage and inconsistent-evidence tests
are also labeled fault injections, not live service behavior. Tests cover exact
confirmation, correction/override, concurrency/replay, ownership, expiry/limits,
multi-food quantities/preparation/portions, unknown and partial nutrition,
source provenance, retries/duplicate/stale replies, revision-aware nonmutating
M4 output, explicit target scope, and complete/partial CLI disclosures.

Real vision inference, photo accuracy, latency, resource peaks, live USDA
availability, real authentication, persistence across restart and team frontend/
backend integration remain unverified/out of scope. None are needed for the
deterministic standalone workflow.

### Validation checkpoint

| Suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| New M5.5 workflow tests | 87 | 0 | 0 |
| Existing M1-M5.3 regression tests | 1007 | 0 | 20 |
| Full combined suite | 1094 | 0 | 20 |

The final full run took 21.30 seconds and emitted no test warnings. The existing
skips are four opt-in live USDA checks and sixteen opt-in local Qwen3 checks;
no live inference or USDA request was made. Complete and partial demo commands
run successfully with the explicitly labeled simulation described above.

All 275 pre-existing tracked/untracked source files match the starting SHA-256
fingerprints, including both modified ignore files and 73 untracked
`local_preview` files. Twelve M5.5 files are new, with no existing source or
contract modifications. No dependencies were installed, models downloaded,
external services started, database changes made, or Git changes staged/committed.
