# Standalone local setup and offline demonstration

Run from the repository root in Windows PowerShell. No Supabase, MongoDB, frontend,
backend, USDA key, `.env`, Ollama or downloaded model is required for the final
offline demo or default tests. Do not copy application credentials into this package.

## Existing environment

The M5.6 environment inspected on 2026-11-12 is Windows AMD64, CPython 3.14.0,
Pydantic 2.14.2, python-dotenv 1.2.4, pytest 9.2.0 and Pillow 13.0.0. This is an
observed working setup, not a guarantee for other platforms or future dependency
resolutions. No dependency was installed during M5.6.

```powershell
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.final_demo --help
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.final_demo
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.final_demo --scenario complete
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.final_demo --scenario partial
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.final_demo --json
```

The default prints both cases with disclosures, explicit scripted DEMO USER text
and replies, session IDs/revisions, nutrient totals/subtotals, item coverage, M4
interpretation and USDA citations. JSON retains existing full M3/M4 contracts and
nulls. IDs, hashes containing timestamps and timestamps vary; nutrition/choices
are deterministic. Temporary synthetic images are removed automatically. No real
photo, model or provider option is accepted. The command returns 0 on success,
1 on dependency/workflow/local-I/O failure and 2 on invalid arguments. Failure
output has safe codes/disclosures on stderr; it omits exception bodies and private
paths and emits no partial success report. It does not repair a failed environment.

## Fresh environment (instructions only; not performed during M5.6)

With an installed compatible Windows Python, create a new package-local virtual
environment **only if `agentic_ai/.venv` does not already exist**:

```powershell
py -3.14 -m venv agentic_ai/.venv
& agentic_ai/.venv/Scripts/python.exe -m pip install -r agentic_ai/requirements-dev.txt -r agentic_ai/requirements-vision.txt
& agentic_ai/.venv/Scripts/python.exe -m pip check
```

Do not recreate or overwrite an existing environment. Requirements-dev includes
runtime requirements; vision adds only pinned Pillow 13.0.0. No Torch, Transformers,
cloud SDK or Ollama Python SDK is needed. Package installation requires a package
index/network or an independently prepared compatible offline wheelhouse; runtime
does not. Broad existing Pydantic/dotenv/pytest ranges are not a full lockfile.
The exact versions above record this validation environment. A fresh install and
other Python/OS combinations have not been reproduced during this milestone.

## Deterministic tests

Explicitly disable opt-in service tests; do not rely on inherited flags. Use a new
temporary directory for each run (pytest manages only its designated directory).

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUTRIAI_RUN_LIVE_TESTS = '0'
$env:NUTRIAI_RUN_NUTRITION_LIVE = '0'
$env:NUTRIAI_RUN_USDA_LIVE = '0'
$m56Temp = 'agentic_ai/.test-tmp-m56-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests/final_demo -q -rs --basetemp=$m56Temp
$m56FullTemp = 'agentic_ai/.test-tmp-m56-' + [guid]::NewGuid().ToString('N')
& agentic_ai/.venv/Scripts/python.exe -B -m pytest -c agentic_ai/pytest.ini agentic_ai/tests -q -rs --basetemp=$m56FullTemp
```

New final-demo tests block network connections and real model transports. The
full suite includes deterministic synthetic fault injections; these do not
establish live service behavior. See [FINAL_VALIDATION.md](FINAL_VALIDATION.md)
for current counts and the twenty intentional external/model skips.

## Other existing offline commands

```powershell
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.nutrition_demo --offline-examples
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.orchestration_demo --offline-examples
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.recommendation_demo --offline-examples
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.image_workflow_demo --scenario all
```

These use curated/scripted extraction and saved authentic USDA data, not live
recognition or live USDA. In contrast, `agentic_ai.demo --examples`,
`nutrition_demo --examples` and `orchestration_demo --text ...` invoke actual
text Qwen3. They are **not** substitutes for the offline commands above.

Real text inference requires a running local Ollama and the configured text model
(`qwen3:4b-instruct` by default). Live USDA requires explicit live-provider use
and a separately configured key/quota. Real vision requires `qwen3-vl:2b`, compatible
Ollama and adequate free memory; it is postponed, not needed for this setup, and
must be evaluated separately. No model download or live inference is authorized
or performed as part of M5.6.
