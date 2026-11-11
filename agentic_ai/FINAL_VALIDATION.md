# Final validation ledger — M5.6

Workspace: original `Food-Nutrition-Analyzer`, branch `agentic-ai`.
Starting checkpoint: `3a25873c720383d294329a3866bb1b99a16fc2d4` (M5.5).
Evaluation date: 2026-11-12. M5.4 live vision testing remains postponed.

## Current deterministic validation

| Run | Passed | Failed | Errors | Skipped | Duration |
| --- | ---: | ---: | ---: | ---: | --- |
| New M5.6 final-demo tests | 25 | 0 | 0 | 0 | 3.86 s |
| Complete M1–M5.6 regression suite | 1119 | 0 | 0 | 20 | 37.75 s |

The full total includes the 25 new tests and all 1094 previous deterministic
passes; it is not an additional 1119 tests. No warnings were emitted. All three
live opt-in flags were explicitly zero. Initial development failures in the new
wrapper's JSON decoding and new test field/help assertions were corrected only
in the new files before these final runs; existing contracts needed no fixes.

Executed successfully with exit 0 and no stderr: default final demo, each final
scenario, JSON output, help, and the four other offline commands listed in
LOCAL_SETUP. `pip check` reported no broken requirements; no install was performed.
All 23 relative documentation links resolved to existing files. Fresh environment
creation/installation instructions were inspected but deliberately not executed.

| Actual final-demo result | Complete scenario | Partial scenario |
| --- | --- | --- |
| M3 state/revision | completed / 4 | completed / 2 |
| Nutrition status; M4 status | complete; ready | partial; limited |
| Complete calories | 244.0000 kcal | unknown (`null`) |
| Known calorie subtotal | 244.0000 kcal | 89.0000 kcal, banana only |
| Per-nutrient item coverage | 2/2 | 1/2 |
| Offline USDA FDC citations | 173944, 173424 | 173944 |

Both reports explicitly separated simulated vision/M1 and scripted confirmation
from actual preprocessing, source-consistent M2/M3 and deterministic M4. All five
complete meal nutrient totals remained null in the partial case. Source bytes
passed the existing manifest integrity check; no new nutrition dataset was added.

Commands are in [LOCAL_SETUP.md](LOCAL_SETUP.md). Default service flags must be
zero. No installation, network service or model inference is required. The final
demo blocks misleading complete totals and mismatched M4 revisions in its report;
it reuses the existing confirmed workflow, not new nutrition calculations.

## Capability checklist

| Capability | Evidence and classification |
| --- | --- |
| Offline contracts, confirmation, replay, ownership/revisions, partial results and source-consistent calculations | Deterministic regression tests; synthetic fault injections are labeled tests, not live incidents. |
| Complete and partial image-to-nutrition demonstrations | Synthetic pixels + SIMULATED vision/M1 + scripted DEMO USER confirmation; actual preprocessing, M3/M2/M4 and integrity-checked USDA snapshots. |
| Actual text Qwen3 | Previously observed, separately recorded below; not rerun for M5.6 and not counted as current offline passes. |
| Actual Qwen3-VL recognition, accuracy, latency, memory peaks | Postponed/unverified. `qwen3-vl:2b` was missing and free RAM insufficient in the earlier readiness check. No live vision run is claimed. |
| Current live USDA availability/comprehensive provider verification | Not rechecked. Earlier limited success and HTTP 429 failures must not be presented as an all-passing live verification. |
| Real Supabase login, MongoDB persistence, team API/frontend and account switching | Outside this standalone milestone; unverified here. Owner-context tests do not prove authentication. |
| Durable restart recovery/shared multi-worker replay and concurrency | Not implemented by process-local stores; requires integration design. |
| Fresh setup on another machine, deployment, medical validity or production readiness | Not verified or claimed. Setup commands are instructions, not evidence of a new install. |

The twenty default skips are twelve M1 local-Qwen cases, four Qwen-to-nutrition
cases and four live-USDA cases. They are intentional opt-in tests, not passing
checks. M5 vision fault/transport tests use deterministic doubles, not real vision.

## Previously recorded live text and USDA evidence

- [M1 report](validation/REPORT.md), [JUnit](validation/test-results.xml) and
  [captured live results](validation/live-results.json): 12 actual local Qwen3
  acceptance cases passed on the recorded 2026-10-31 run; the report's total was
  136 tests including 124 offline tests. Model `qwen3:4b-instruct`, Ollama 0.40.13.
- [M2 report](validation/milestone2/REPORT.md), [M1 rerun XML](validation/milestone2/m1-live-tests.xml)
  and [mixed live XML](validation/milestone2/live-tests.xml): 12 text cases rerun;
  four actual text-Qwen-to-offline-USDA workflows passed. Two live USDA detail
  checks passed; roti/search checks failed with HTTP 429. These are historical
  failures retained as evidence, not current passes or skips.
- [M3 report](validation/milestone3/REPORT.md) and
  [actual Qwen snapshot demo](validation/milestone3/actual-qwen-snapshot-demo.json):
  one actual text inference followed by explicit scripted clarification, using
  offline USDA roti/rice records. No live USDA check in that run.

These finite examples do not measure general food extraction/recognition accuracy.
They establish recorded behavior at those checkpoints; they are not evidence of
the currently installed server/model state. No secrets or live credentials are
required to inspect the saved evidence.

## Provenance and review boundaries

The production offline catalog is the existing ten-record `data/usda/foods.json`,
manifest retrieval `2026-10-31T09:29:54.430152+00:00`, CC0-1.0; SHA-256
`c3fde77650f6b10f4fa2f568a800464b34808cacb7bef239e40ea38a7c768937`.
No fixture values were invented for the demonstration. Corrupt-catalog tests edit
temporary copies only. M4 validates supplied-record consistency, not a USDA signature
or medical safety. Unknowns stay null, known subtotals stay separate from totals.

All eight additions are under `agentic_ai/`: `final_demo.py`, this ledger,
`FINAL_ARCHITECTURE.md`, `LOCAL_SETUP.md`, `VIVA_GUIDE.md` and three files in
`tests/final_demo/` (`__init__.py`, `conftest.py`, `test_final_demo.py`).
All 287 pre-existing tracked/nonignored untracked files match the starting SHA-256
audit, including both pre-modified ignore files and all 73 untracked
`local_preview/` source/evidence files. No existing file was edited; ignored
preview dependencies were not operated on. No credentials, generated artifacts
or dependency changes are included. New Python files parse successfully, and the
Git index remains empty. No installation, database change, application edit, live
inference or Git commit is part of M5.6. See [architecture](FINAL_ARCHITECTURE.md) and
[viva guide](VIVA_GUIDE.md) for integration boundaries and evaluation wording.
