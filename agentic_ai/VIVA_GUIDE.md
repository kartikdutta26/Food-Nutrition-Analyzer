# NutriAI viva / evaluation guide

## A short demonstration

From the repository root, run:

```powershell
& agentic_ai/.venv/Scripts/python.exe -B -m agentic_ai.final_demo
```

Begin by stating the boundary: **vision and text-model transports are simulated;
confirmation/replies are scripted DEMO USER actions; preprocessing, validation,
M3 orchestration, M2 calculations on authentic offline USDA records and M4 rules
are actual implementation execution.** Synthetic pixels do not depict the foods.
This is not a visual-accuracy demonstration or live USDA verification.

1. In the complete case, point to unconfirmed banana/plantain and egg hypotheses.
   Show the independent confirmed text, followed by explicit banana 100 g, boiled
   preparation and egg 100 g replies. M3 completes at revision 4; M4 is `ready`.
2. In the partial case, show `100 g banana and paneer curry`, with curry explicitly
   left unresolved. M3 completes at revision 2; nutrition stays `partial`; M4 is
   `limited`. Complete totals remain unknown. The banana subtotal is not the meal.
3. Show FoodData Central IDs, URLs, retrieval time and snapshot checksum. Then show
   the twenty live-service/model checks skipped in the default test suite.

The observed complete result is 244.0000 kcal, 13.6700 g protein, 23.9600 g carbs,
10.9400 g fat and 2.6000 g fiber, from FDC 173944 and 173424. The partial case has
only FDC 173944: known subtotal 89.0000 kcal, 1.0900 g protein, 22.8400 g carbs,
0.3300 g fat and 2.6000 g fiber; coverage is one of two food items. These values
come from existing M2 calculations, not hardcoded demo nutrition or image estimates.

## Architecture points to explain

- **Why several agents?** M1 proposes structured text extraction; M2 owns source
  lookup/arithmetic; M3 owns clarification/session state; M4 interprets validated
  evidence; M5 proposes image identities behind a confirmation boundary. These
  are explicit Python components, not autonomous chatbots or hidden tool loops.
- **Why Qwen3 and Ollama?** Existing M1 uses local `qwen3:4b-instruct` for structured
  extraction without paid API calls. M5 targets the smaller local `qwen3-vl:2b`
  vision model. This is a resource/locality choice, not a benchmark claim. Vision
  is untested live because the model was missing and available RAM insufficient.
- **Why not use an LLM for nutrient numbers?** Numbers and portions must be grounded
  in USDA records/user evidence; Python Decimal arithmetic computes contributions.
  A model guess about grams, hidden ingredients or calories is not acceptable evidence.
- **Why confirmation?** A photograph can suggest identities but cannot establish
  consumption, preparation, quantity or hidden ingredients. User-confirmed text
  is separate from hypotheses. Fingerprints/revisions bind it to the exact result;
  confirmation is consumed before M3 starts. Demo actions are scripts, not humans.
- **Why revisions and request IDs?** Replies must match the current question/item
  and revision. Duplicate/stale actions cannot silently update a different state.
  M4 is requested against the current session revision and old guidance is discarded.
- **Why distinguish completion from completeness?** A user can finish clarification
  while leaving food unresolved. `completed` is a conversation state, not proof that
  all nutrient contributions are known. Coverage counts items, not weight or accuracy.
- **What does M4 verify?** Consistency of supplied records, portion arithmetic and
  evidence links. It does not independently authenticate USDA or validate health
  outcomes. It has controlled deterministic wording, no inferred targets and no
  diagnosis/treatment advice.
- **What does ownership mean locally?** A trusted caller supplies owner context;
  it is checked on every operation. This is not login/authentication. The team
  server must derive ownership from verified credentials, never a browser user ID.

## Evidence to present and limits to acknowledge

Show [FINAL_VALIDATION.md](FINAL_VALIDATION.md) for exact current test counts and
links to historical actual text-Qwen evidence. Fixed acceptance examples do not
establish general model accuracy. Offline tests with injected failures do not
prove live availability, deployment, concurrency at production scale or security
against every adversarial model/image. Snapshots cover ten records, not all meals.

State that stores/replay ledgers are bounded and process-local, not durable or
multi-worker. No fresh-environment installation, live vision, live USDA recheck,
medical validation or end-to-end team application validation was done for M5.6.
The package is ready for review and separately approved integration/testing;
no production-readiness claim follows from deterministic tests.
