# Task A handoff — November 14, 2026

## Supported first-draft path

PRISM preparation, a frozen split manifest, M0/M1 baselines, bounded SynthesizeMe
(M2), bounded ICAI (M3), save/load, held-out prediction, evaluation, portable export
and an artifact-backed HTML viewer. M4–M7 remain intact but are deferred per Gio’s
updated scope. No method is a winner yet.

Use [README.md](README.md) for copy-paste setup, smoke, live-run, export and prediction
commands. All output paths are relative to the repository root.

## Data and reproducibility

PRISM revision `a03cab5122c397f1307ed092423a05732cc2aa93` yields 16,693 unique pairs
from 723 users after 12 agreeing duplicate removals. There are 345 development users
and 378 final users. The shared manifest is `data/prefdata/prism-splits.json`, ID
`482e9c1cf1e723ff49527f17d4113c315fa71f2f088a813e2ea9aba5fc74b891`.

The manifest records removals, source file hashes and original partitions. User
partitions and conversation boundaries are preserved. Stored judge predictions,
reasoning and scores are excluded from model inputs. The canonical Parquet source
avoids the earlier row-service rate limit; Arena is not needed as fallback.

The final-test marker is shared across Git worktrees via the Git common directory.
Final use requires an explicit command and a pinned live model. Final users have
not been evaluated for this draft.

## Executed evidence

- `runs/taste-smoke-01/`: the deterministic synthetic fixture completed M0–M3,
  two held-out predictions each, without failures. The bundle includes save/load
  and a call through the team’s actual adviser interface. These outputs verify
  plumbing only; the fixture’s accuracy is not preference evidence.
- The local artifact viewer is `runs/taste-smoke-01/viewer.html`. Open it in a
  browser or load `bundle.json` in `docs/user-models/workbench.html`.
- **Live PRISM pilot completed:** `results/fidelity/prism-live-01/` contains
  the complete report, registration, split manifest, raw requests/responses,
  predictions, four fitted models, exported `usermodel.json`, inspection bundle
  and standalone `viewer.html`. One development user (`prism:user949`), nine
  held-out choices per method: M0 4/9, M1 4/9, M2 4/9, M3 3/9. All 36 predictions
  completed with zero failures. M2 retained no hypotheses, persona or exemplars
  for this user because its bounded validation search found no strict improvement;
  this empty outcome is preserved. M3 exported two tentative principles. This is not evidence of a winning method or of
  research transfer. One-user bootstrap intervals are degenerate, not meaningful
  uncertainty estimates.
- The live model was `openai-responses:gpt-6-luna`. Conservative estimated spend:
  $0.0175145 for fitting/evaluation plus $0.000082 for the actual team adviser
  verification, total **$0.0175965**. These are estimates, not billing reconciliation.
  The pilot used $0.09 + $0.01 per-process caps; Gio subsequently approved a $10
  ceiling for future work. No additional benchmark was launched to use that budget.
- The exported M3 model was loaded through the team's actual loader, and
  `TasteAdvisor.consult()` and `principles()` succeeded with the live backend.
  M3 is an illustrative integration artifact, not the selected winner.
- `results/fidelity/offline-smoke-02/` preserves a second complete synthetic smoke
  on the implemented CLI; its exported object was also loaded for a fresh prediction.
  `runs/fidelity/prism-offline-01/` and `runs/prism-review-01/` exercise the same path
  on real PRISM inputs with scripted outputs, with all 36 predictions completed.
- Historical Arena pilot, already completed by Gio: one user, five targets each
  for M0 and M1, zero failures; 4/5 versus 3/5 correct; reported conservative cost
  $0.005369. This establishes neither a winning method nor research transfer.

Run registration, full request/response traces, raw predictions, errors, saved
models and reports remain inspectable. Failed or bounded-out runs must be retained.
No live credits are consumed by the offline backend.

## Team handoff and limits

The exported `usermodel.json` uses the existing shared contract. The export
verification calls `research.advisor.load_user_model`, then
`TasteAdvisor.consult()` and `principles()`. No teammate-owned implementation is
changed. M3 is used in the runnable export example because it exposes readable
principles, not because it was selected as best.

M2 exports persona/examples for prediction and retained hypotheses as principles
for the proposer; M3 exports principles. Both use the existing adviser interface. M0–M3 confidence is
uncalibrated; the adviser does not enforce `calibrated`. Its threshold is not a
proved reliability guarantee. Numeric weights are unavailable for these methods,
and causal assumptions are not invented from preference labels.

M2 uses bounded hypotheses, greedy validation selection and selected examples;
M3 uses bounded principles, lexical clusters and in-sample reconstruction. Both
are adaptations, not full reproductions of their papers. A saved artifact must
reload with the same backend/model identity. Changing evaluation models requires
refitting on the same allowed data.

The next useful evidence is error inspection and a larger matched development
comparison across users if warranted. The current live pilot does not favor extraction. PRISM tests
preference prediction. Research improvement still needs Task B’s researcher data,
Task D’s controlled loop comparison and Task C’s validity measurement.

## Verification

The full repository suite passed 381 tests with one skipped before packaging.
The raw key was provided only to the live process environment, not saved in code,
run traces, models or Git. The original checkout and its uncommitted changes remain intact.

The final live HTML viewer was inspected in a browser: live/offline labeling,
method selection, history, principles, prediction and observed label all rendered.
A narrow reading view was checked on the offline bundle; no browser errors were observed.
