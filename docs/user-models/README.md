# Gio’s user-model first draft

The supported path is **PRISM → M0/M1 baselines → bounded SynthesizeMe (M2) and
ICAI (M3) → saved model → unseen-choice evaluation → team-adviser export**.
M4–M7 remain in the repository but are deferred. No method is declared a winner.
This work stays in Task A; it does not change teammates’ environment or orchestration code.

Start with the [recorded live PRISM viewer](../../results/fidelity/prism-live-01/viewer.html)
and [executed-run handoff](handoff.md). It includes actual inputs, extracted
principles, predictions and evaluation; no model call is needed to inspect it.

Run the commands below from the repository root. Use a new output directory for
each run: existing results are never silently overwritten.

## 1. Setup and offline smoke

Python 3.9+ is sufficient for inference, evaluation and the offline smoke. Only
PRISM preparation requires the optional Parquet reader:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install pyarrow
python -m autoresearch.taste smoke --output runs/taste-smoke-next
```

The smoke uses synthetic choices and deterministic scripted responses. It runs
M0–M3, saves and reloads a model, predicts new choices, evaluates them, and calls
the team’s actual `load_user_model` / `TasteAdvisor` interface. It writes:

- `runs/taste-smoke-next/run/report.json`: results, errors and usage.
- `runs/taste-smoke-next/bundle.json`: full inspection example and integration check.
- `runs/taste-smoke-next/viewer.html`: self-contained, open locally in a browser.
- `runs/taste-smoke-next/export/usermodel.json`: exported M3 model.

**These scores test plumbing, not preference accuracy.** There are no API charges.

## 2. Prepare the frozen PRISM data

```bash
python scripts/prepare_prism.py
```

This downloads the pinned canonical Parquet revision
`a03cab5122c397f1307ed092423a05732cc2aa93` from
[PRISM / PersonalRewardBench](https://huggingface.co/datasets/MichaelR207/prism_personalized_0125/tree/a03cab5122c397f1307ed092423a05732cc2aa93).
It writes normalized records to `runs/prefdata/prism.jsonl` and the shared manifest
to `data/prefdata/prism-splits.json`. Preparation can be repeated on identical data;
it refuses a different snapshot at an existing destination.

The snapshot has **16,693 unique pairs from 723 users**, after removing 12 agreeing
repeats. The manifest records each removal, source URLs and SHA-256 hashes. It has
345 development users and 378 final-test users. Released history, validation and
target conversations remain separate within each user. The adapter excludes stored
judge predictions, reasoning and scores, preserves context/response text, and gives
A/B a deterministic order. Conflicting labels or duplicates crossing boundaries
are errors. Canonical Parquet avoids the earlier row-service rate limit; no Arena
fallback is needed.

## 3. Exercise all four core methods on real PRISM inputs

First inspect the selected development workload without calls:

```bash
python -m autoresearch.taste fidelity --dataset prism --users dev \
  --methods m0 m1 m2 m3 --n-users 1 --seed 0 --dry-run
```

Then run the same path with scripted outputs:

```bash
python -m autoresearch.taste fidelity --dataset prism --users dev \
  --methods m0 m1 m2 m3 --n-users 1 --seed 0 \
  --backend offline --model fixture-v1 --max-calls 300 --max-seconds 300 \
  --config '{"max_history":5,"max_hypotheses":2,"max_principles":2,"max_exemplars":1,"k":5}' \
  --output runs/fidelity/prism-offline-next

python -m autoresearch.taste export \
  --run runs/fidelity/prism-offline-next --method m3 \
  --output runs/prism-review-next --verify-integration \
  --backend offline --model fixture-v1
```

Open `runs/prism-review-next/viewer.html`. Its **Recorded artifacts** tab shows the
actual run history, saved persona/principles, held-out pair, predicted/observed
choice, confidence, errors and comparison. The viewer labels scripted outputs as
**OFFLINE** even when their inputs are real PRISM records. The other tabs contain
teaching examples and an exploratory prompt editor; they do not change runtime
prompts. You can also import `bundle.json` into `docs/user-models/workbench.html`.

M3 is selected for this example because it exports readable principles, **not
because it won a benchmark**. Exporting without `--verify-integration` packages the
model without another inference call. Verification makes one additional prediction.

## 4. Small live development comparison

For live calls, set `OPENAI_API_KEY` in the process environment using a project
key under the credited Personal organization. Skip key entry if already configured.
See the handoff for executed live runs; the commands alone are not result evidence.
Do not place keys in files, Git or chat. In macOS zsh, this reads it without echo:

```zsh
read -s "OPENAI_API_KEY?OpenAI API key (hidden): "
export OPENAI_API_KEY
printf '\n'
```

With credentials configured, this is a bounded four-method development run:

```bash
python -m autoresearch.taste fidelity --dataset prism --users dev \
  --methods m0 m1 m2 m3 --n-users 1 --seed 0 \
  --backend openai --model gpt-6-luna \
  --max-usd 10 --max-calls 300 --max-seconds 300 \
  --config '{"max_history":5,"max_hypotheses":2,"max_principles":2,"max_exemplars":1,"k":5}' \
  --output runs/fidelity/prism-live-next

python -m autoresearch.taste export \
  --run runs/fidelity/prism-live-next --method m3 \
  --output runs/prism-live-review-next
```

The direct OpenAI backend reserves conservative estimated cost before each call,
uses no HTTP retries, and retains uncertain reservations after failures. The
$10 limit is **per invocation**, not a provider billing guarantee or a global
account cap. Repeated runs and optional integration calls count against the total
approved budget. If a time/call/cost bound is reached, retained errors are part of
the result; do not treat an incomplete comparison as method selection.

M1, M2 and M3 receive the same seeded subset of up to five history pairs in this
configuration. M2 additionally uses the user’s validation conversations for search;
M3 does not. That difference is part of the methods, not a matched-information
ablation. The development model may differ from a later evaluation model; refit
with the latter rather than loading an artifact under a different backend.

## 5. Load the exported object and predict

For the offline export from step 3:

```bash
python -m autoresearch.taste predict \
  --artifact runs/prism-review-next/usermodel.json \
  --backend offline --model fixture-v1 \
  --context 'How should I organize a short work session?' \
  --options 'Choose one concrete task and work on it for 25 minutes.' \
            'Build a detailed taxonomy of every possible productivity method.'
```

This last example has no human preference label; it demonstrates prediction, not
an accuracy result. Use `--backend openai --model gpt-6-luna --max-usd 0.02` with a
live artifact saved by that same backend/model. Backend identity is checked on load.

The Python contract is unchanged:

```python
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import load_model

model = create_method("m3", llm, seed=0, max_history=5, max_principles=2)
model.fit(history, validation)              # one person's Choice records
model.save("runs/person/usermodel.json")
restored = load_model("runs/person/usermodel.json", llm)
prediction = restored.predict(context, [response_a, response_b])
artifacts = restored.artifacts()
```

`Prediction` includes choice, probabilities, rationale, confidence and `calibrated`.
M0–M3 confidence is **uncalibrated**, not a measured probability of being right or
of experimental success. Only M4 learns feature weights; zero weights elsewhere
mean unavailable. Assumptions remain empty because response preferences do not
establish causal facts. M2 exports a persona/examples and retained hypotheses as principles; M3 exports
principles. The team adviser ranks through `predict()` and reads
`artifacts().principles`. M2 ranking uses persona/examples, while its retained
hypotheses can guide the proposer. The adviser does not enforce the calibration flag; confidence routing needs
explicit downstream policy. The verification call tests compatibility, not whether
research quality improves.

## Methods and limits

| Method | Implemented stages | Important limit |
|---|---|---|
| M0 | Predict without user history | Generic preference baseline |
| M1 | Seeded labeled history in predictor context | Raw-history baseline |
| M2 | Per-pair hypotheses → greedy validation selection → persona → validation-selected examples | Bounded SynthesizeMe adaptation; no DSPy random search. Validation selection is not independent verification. |
| M3 | Per-pair principles → TF-IDF complete-link clusters/medoids → history reconstruction ranking | ICAI-inspired bounded adaptation; lexical clustering and in-sample ranking, not a paper reproduction. |

Source implementations: [SynthesizeMe](https://github.com/SALT-NLP/SynthesizeMe)
and [ICAI](https://github.com/rdnfn/icai). Search caps, selection traces and source
IDs are stored with each model. Empty selected artifacts and method failures are
valid outcomes that should remain visible. M4–M7 are preserved but deferred; M7’s
per-user calibration is not supported by the current PRISM validation structure.

Each run writes `registration.json`, `split-manifest.json`, `predictions.jsonl`,
`requests.jsonl`, `models/` and `report.json`. These capture code version/dirty state,
source revision, prompt text and settings, raw replies/errors, outputs and usage.
Do not publish traces from private researcher data without reviewing their contents.
Reports use user-average accuracy, count failures as wrong, and report paired
bootstrap differences versus M1. Brier scores cover only valid predictions.
One-user confidence intervals are not meaningful uncertainty estimates.

## Final users stay protected

Development commands never consume the final-test marker. A final comparison needs
explicit `--users test --final`, a pinned live model and frozen settings. The marker
is `fidelity_TEST_USED` in Git’s common directory, shared across this repo’s
worktrees; the legacy `results/fidelity/TEST_USED` marker is also checked. A crash
still consumes the attempt. Do not delete or bypass markers. This cannot prevent
someone from making a separate clone and deliberately rerunning the data.

No final evaluation was run for this draft. After the development comparison and
budget are agreed, prepare the final command as one invocation containing every
method to compare; keep it separate from these runnable smoke instructions.

## Checks and current evidence

```bash
python -m unittest discover -s tests -t .
```

See [handoff.md](handoff.md) for executed runs and remaining limits. Historical Arena
pilot: one user, five targets each for M0/M1, zero failures; M0 got 4/5 and M1 3/5,
with reported conservative spend $0.005369. This was a plumbing check, not evidence
that M0 beats M1, and not a PRISM result.
