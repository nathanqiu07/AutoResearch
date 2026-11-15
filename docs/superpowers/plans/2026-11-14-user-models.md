# User Models Implementation Plan

> Execute task-by-task with test-first verification and scoped commits.

**Goal:** Deliver Gio's eight-method user-model track with reproducible evaluation.
**Architecture:** A label-free prediction contract, strict data adapter and immutable
split manifest feed interchangeable user models and a separate fidelity runner.
**Tech Stack:** Python 3.9+, standard library, existing LLM backends.
**Spec:** `docs/user-models/design.md` and `PLAN.md` §§6,12.1,12.6.

## Global constraints

Only WS A files. Preserve all teammate changes. Full unittest suite before pushes.
No live model experiments until provider and budget are agreed. No fabricated metrics.

## Review focus

1. Target labels or upstream judge artifacts entering prediction prompts.
2. Same user or conversation crossing a partition boundary.
3. Invalid/empty model output silently converted into a successful prediction.
4. Test reuse through another output directory or a second method invocation.
5. Calibration fitting on labels already used for method selection.

### Task 1: Interface, fixed splits and M0/M1

Files: `taste/usermodel.py`, `taste/prefdata.py`, `taste/methods/{__init__,m0_none,m1_history}.py`;
tests: `tests/test_usermodel.py`, `tests/test_prefdata.py`.

Interfaces: `Choice(user_id,context,a_text,b_text,chosen,...)`;
`Prediction(choice,confidence,rationale,probabilities,calibrated)`;
`UserModel.fit(history,val)`, `predict(context,options)`, `artifacts()`, `cost`.
Adapter: `normalize_row(row,dataset,outer_split,seed) -> PreferenceRecord`;
`build_manifest(records,seed) -> dict`, `write_manifest(path,manifest)`.

- [x] Write tests for no-history isolation, seeded raw history, invalid probabilities,
  multi-option prediction, fit-user/overlap checks, source metadata stripping,
  deterministic A/B mapping, user/group partitions and immutable manifests.
- [x] Run tests and confirm missing behavior fails.
- [x] Implement contract, adapter and baselines. Download/pin public dataset only.
- [x] Run targeted tests and full suite; inspect manifest counts; commit/push.

### Task 2: Fidelity runner and module CLI

Files: `taste/fidelity.py`, `taste/__main__.py`, `tests/test_fidelity.py`.
Interfaces: runner consumes records, manifest and model factories; emits per-case
predictions, per-user summaries, artifacts, failures, costs and paired comparisons.

- [x] Test dev-user isolation, error accounting, report statistics, single final
  marker across output paths and no final predictions without explicit launch.
- [x] Observe failure, implement runner and CLI, verify with scripted models.
- [x] Run full suite; commit/push. Explain runnable baseline workflow to Gio.

### Task 3: Bounded M2–M6

Files: `taste/methods/m2_synthesizeme.py` through `m6_verified.py` and shared utilities;
tests: `tests/test_taste_methods.py`.

- [x] Test useful-rule selection, duplicate clustering, label-blind feature mapping,
  retrieval ordering, validation filtering, empty histories and bounded call counts.
- [x] Implement each core-stage adaptation with source/adaptation metadata.
- [x] Keep export/load predictions stable; include `TasteProfile` adapter.
- [x] Run full suite and commit/push working units.

### Task 4: M7, schema search and handoff

Files: `taste/methods/m7_confident.py`, `scripts/schema_search.py`, docs and method tests.

- [x] Test separate tuning/calibration conversations, finite probabilities and
  conservative uncalibrated fallback with too little calibration data.
- [x] Implement regularized Platt scaling and bounded dev-only schema search (schema search removed 2026-11-14).
- [x] Run full suite, fresh review, commit/push. Report actual live-run status.

### Task 5: Live development and final comparison (Gio's decision gate)

- [ ] Confirm backend and usage cap; time one smoke test before choosing sample size.
- [ ] Run development comparison, document hypothesis and counterevidence, freeze config.
- [ ] Launch the registered final comparison only after Gio approves the concrete run.
- [ ] Export chosen method and disclose uncertainty, failures and transfer limits.
