# User models: build, compare and hand off

This is Gio's WS A implementation. It does not modify the research loop, scorer,
agent orchestration, or the shared CLI. Run commands from the repository root.

## What is implemented

| ID | Method | Evidence used while fitting |
|---|---|---|
| m0 | Generic judge with no history | None |
| m1 | Seeded raw history; k=5/10/20/all | History |
| m2 | Hypotheses, validation selection, persona, greedy examples | History and validation |
| m3 | Principles, TF-IDF clusters, history reconstruction ranking | History |
| m4 | Label-blind text features and Bradley–Terry weights | History |
| m5 | M2 persona + M3 principles + lexical example retrieval | History and validation |
| m6 | M5 with iterative removal of harmful components | History and validation |
| m7 | M6 plus binary Platt calibration on separate conversations | History, tuning and separate calibration |

M2/M3 are **bounded adaptations**, not paper reproductions. Defaults use up to five
history pairs, five hypotheses/principles and three examples. M6 keeps tied components;
survival does not establish independent usefulness. M4 uses fixed L2=0.5 because the
existing fitter does not cross-validate without a text prior. M7 reports uncalibrated
confidence when there are fewer than eight calibration choices, only one label class,
or more than two target options. These settings are recorded in each artifact.

Scripts and independent synthetic fixtures test behavior, not real-model accuracy.
No test-set preference result has been established by the implementation checks.

## Shared contract

```python
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import Choice, load_model

model = create_method("m1", llm, seed=0, k="all", cache_dir="runs/taste-cache")
model.fit(history, validation)        # each is a list[Choice] for one person
prediction = model.predict(context, options)  # strings; no target answer supplied
print(prediction.choice, prediction.index, prediction.confidence)
model.save("runs/my-person/usermodel.json")
restored = load_model("runs/my-person/usermodel.json", llm)
artifacts = restored.artifacts()
legacy_profile = artifacts.to_profile("person-name")
```

`choice` uses a/b/c/... in option order; `index` is zero-based. Confidence is the
predicted choice's probability, not experiment success. `probabilities` gives all
options in order. Raw confidence is explicitly uncalibrated.

`artifacts()` exports principles, persona, feature weights, assumptions, exemplars
and method/source/split provenance. Only M4 learns feature weights; zeros elsewhere
mean **unavailable**, not indifference. Assumptions remain empty: the methods do not
turn preference labels into evidence of environmental causal claims. M2 retains
hypotheses and support IDs in metadata. Consumers should use `predict`, not silently
replace it with the legacy zero-weight adapter.

Saved artifacts must be reloaded on the same backend/model/endpoint. To evaluate on
a different model, fit afresh using that backend and the same allowed history. This
prevents invalid transfer of M4 feature weights and M7 calibration.

## Get the PRISM data

The preference data is PRISM from PersonalRewardBench
([dataset](https://huggingface.co/datasets/MichaelR207/prism_personalized_0125),
[official loader](https://github.com/SALT-NLP/SynthesizeMe/blob/main/synthesizeme/datasets/dataset.py)).
The repo holds only the split manifest (IDs and hashes, no text). Each person
downloads the data once:

```bash
git pull
python3 -m autoresearch.taste prepare
```

No API key, Hugging Face account or extra package is needed; it uses the public
Hugging Face rows service through the standard library. Expect about 10 minutes and
about 200 MB of cached pages. On success it prints:

```
{"n_examples": 16693, "n_removed_repeats": 12, "n_users": 723, "manifest_id": "b6e2453150fb5983052e393497e62c094aa44998796ecfd27817d05962c280c9"}
```

What it writes, all under ignored `runs/prefdata/`:

- `runs/prefdata/raw/prism/`: cached pages (about 200 MB).
- `runs/prefdata/prism.jsonl`: the 16,693 normalized choices (about 40 MB) that
  `fidelity` and `schema_search` read by default.

If the download stops (HTTP 429 rate limit or a 5xx error after the built-in
retries), run the same command again: cached pages are kept, so it resumes. If it
reports `split manifest already exists with different content`, your download does
not match the committed `data/prefdata/prism-splits.json`; do not delete the
manifest to get past it, report it instead. Never commit `runs/`.

### What the data is

723 users (345 development, 378 final test). Upstream has 16,705 rows; 12 are exact
repeats (same person, prompt, responses, answer and partition). `prepare` keeps one
copy and lists each removal in `data/prefdata/prism-splits-removed.json`. Repeats that
disagree on the answer or cross a partition fail the strict manifest check. The
canonical Parquet files at upstream revision
`a03cab5122c397f1307ed092423a05732cc2aa93` give the same records.

The outer train/validation user partitions are development users; outer test users
stay held out. Within each person, preserve released history/validation/test
conversation groups. Blank responses are valid data. Prior judges' reasoning,
predictions and scores never enter normalized records. Target options are
deterministically shuffled A/B; the seed and normalized source digest are pinned.
The command is idempotent for identical data and refuses to overwrite a different
manifest or record snapshot. The rows service may return truncated cells; the loader
fails rather than score partial conversations.

Chatbot Arena, the other PersonalRewardBench dataset, was removed on 2026-11-14 at
Ethan's request; it is no longer supported.

## Preview and compare

```bash
python3 -m autoresearch.taste fidelity --dataset prism \
  --methods m0 m1 m2 m3 m4 m5 m6 m7 --n-users 3 --dry-run
```

Dry-run makes no model calls and does not consume the final-test marker. Its
prediction count excludes fitting/search calls, which can dominate compute.

Live development example (uses plan allowance through the authenticated Codex CLI):

```bash
python3 -m autoresearch.taste fidelity --dataset prism --methods m0 m1 \
  --n-users 1 --backend codex-cli --max-calls 20 --max-seconds 180 \
  --output runs/fidelity/codex-dev-01
```

Use `--backend openai-compat --model MODEL` for a configured OpenAI-compatible API
endpoint, or `anthropic`/`claude-cli` for existing team backends. Do not paste keys
into commands or commit them. API model names must be explicit. Backend selection
does not change split policy. The shared budget counts attempted calls, including
failed calls. Providers can have internal retries, so this is a cap on backend
invocations, not a guarantee about provider-billed attempts or dollars.

For the redeemed OpenAI credits, a direct Responses API pilot is available:

```bash
python3 -m autoresearch.taste fidelity --dataset prism --methods m0 m1 \
  --n-users 1 --backend openai --model gpt-6-luna --max-usd 1 \
  --max-calls 20 --max-seconds 180 --output runs/fidelity/openai-dev-01
```

Set `OPENAI_API_KEY` in the process environment using a project key under the
organization that received the credits. Optional `OPENAI_ORG_ID` and
`OPENAI_PROJECT_ID` select explicit headers. Never put the key in this repository
or in chat. [Official key guidance](https://developers.openai.com/api/docs/guides/api-keys).

This direct backend currently supports only the priced `gpt-6-luna` pilot. It uses
reasoning effort `none`, no tools, standard service, and `store=false`. It reserves
a conservative dollar amount before each request, retains uncertain reservations
after failures, makes no HTTP retries, and rejects long-context requests. The cap
and cost estimates use the [published rates](https://developers.openai.com/api/docs/pricing)
checked November 14, 2026; they are not a provider billing statement. Adding a
different evaluation model requires verifying its settings and rates first.

Gio approved up to $1 for this ten-prediction development check on November 14.
It still requires local credentials. Larger runs and the final evaluation need a
separate concrete decision.

Codex runs from an empty temporary directory, ignores user configuration, disables
tools and rejects any tool event. It is a **CLI harness** comparison, not raw API
inference. Temperature/output-token settings are not enforced like API parameters;
record this when interpreting results. A synthetic smoke test succeeded in about
4.2s with about 11,300 input tokens. No benchmark accuracy follows from that test.

Each run creates a registration, prediction JSONL, per-user model artifacts and
`report.json`. Outputs cannot be overwritten. Failures count as wrong in accuracy;
Brier score covers valid predictions only and must be read alongside failure count.
Accuracy averages users equally. Differences from m1 use a paired user bootstrap.
Method artifact `cost` records fitting usage; report usage includes predictions.
Unknown dollar costs remain marked unavailable, not asserted free.

## Final evaluation: stop and review the concrete run

Final use requires `--users test --final` and a pinned model. All methods being
compared must be passed in **one invocation**. A single exclusive marker,
`results/fidelity/TEST_USED`, is written before any fitting. A crash or another
output path does not grant a second attempt. Never delete the marker to tune again.

Final registration covers PRISM, the only dataset. The final launch remains Gio's
decision after model access, budget, dev results and method settings are frozen.

## Bounded schema search

Write a JSON list of up to eight explicit `{id, method, config}` objects (methods
m5–m7), then run:

```bash
python3 -m scripts.schema_search --configs configs.json --dataset prism \
  --n-users 3 --max-calls 100 --output runs/schema-search/01
```

This command always uses development users, shares one call budget across all
configurations and logs every trial. It selects a configuration only when **all**
declared trials finish without errors. An exhausted budget or failed trial leaves
the search incomplete, with no winner. It has no final-test switch. A dev winner
still needs the held-out comparison.

## Verification and limits

Run `python3 -m unittest discover -s tests -t .` before pushing. The suite covers
label isolation, split integrity, cache separation, persistence, method selection,
calibration isolation, call caps and final-use protection. Existing unrelated
resource warnings may appear.

Preference fidelity, research judgment and useful research outcomes remain separate
claims. The environment and orchestration teams own the downstream test. No files
in their implementation areas are changed by this track.
