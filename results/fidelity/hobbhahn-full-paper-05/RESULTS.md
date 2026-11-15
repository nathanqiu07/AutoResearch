# Full-history researcher comparison

Development agreement with AI-inferred Marius Hobbhahn labels; not verified human preferences.
236 learning / 70 validation / unchanged 67 dev choices. Original heldout was not loaded.

| Method | Correct / 67 | Accuracy | Failures |
|---|---:|---:|---:|
| No history | 54/67 | 80.6% | 0 |
| Raw history | 46/67 | 68.7% | 0 |
| SynthesizeMe adaptation | 50/67 | 74.6% | 0 |
| ICAI adaptation | 51/67 | 76.1% | 0 |

Run cost estimate: $2.213274; retained reservations: $0.186072. Including prior commitments: $4.207126 / $10.

These methods were adapted and validated on one researcher. This is development evidence, with no claim of a statistically established winner or downstream research improvement. The user-bootstrap CI in report.json is degenerate because n_users=1; do not treat it as certainty.

## Extracted SynthesizeMe persona

Prefers evidence-calibrated, cautious reasoning: distinguish informed judgment from tested findings, qualify conclusions when evidence is limited, and avoid making safety arguments depend on claims that are difficult to verify. Values independent validation and practical, measurable methods, while recognizing uncertainty and trade-offs. Tends to favor approaches grounded in observed trends over speculative breakthroughs, and incremental policies over sweeping bans. These judgments are often context-specific; several choices reflect what the evidence supports rather than a strong personal preference.

## Extracted ICAI principles

- Select the response that avoids drawing uncaveated safety implications from limited evidence.

m2: 31 selected examples; 0 principles. Confidence is model-reported and uncalibrated.
Generic published persona instruction, not cross-user MIPRO training. One cached label-hidden bootstrap pass over ALL history per stage; random subsets of successful traces rather than regenerating traces for every trial. Up to 64 bootstrapped examples; 10 random trials plus released-code controls per stage. Independent pair predictions, no batched-choice scoring. No invented principle weights.

m3: 0 selected examples; 1 principles. Confidence is model-reported and uncalibrated.
Two contrastive generation prompts; text-embedding-3-small 256-dimensional k-means instead of paper embedding backend. Three unanimous voting repeats, 40 rules/request. Released-code correct/total >= 10% filter; rank correct minus incorrect. Compare top 5 vs 10 on validation (extension); omit optional final diversity reclustering.

## Inspect and reproduce

See the two HTML viewers, model JSON files, split manifest, and predictions.jsonl in this directory. Full raw API traces are retained in the local run archive; prompts and settings are recorded in the artifacts.

Execution code: `68f7a88d6192e514af7a5eb7b631d555aa497a1d`. Source dataset revision: `877dcff723c77c4525cde3fd10fc16f7a540a9d6`.
Method details and commands: `docs/user-models/full-history-paper-run.md`.

Offline replay from this checkout (no credentials or spending):

```bash
mkdir -p runs/hobbhahn-replay
cp results/fidelity/hobbhahn-full-paper-05/records.jsonl runs/hobbhahn-replay/
cp results/fidelity/hobbhahn-full-paper-05/split-manifest.json runs/hobbhahn-replay/manifest.json
python scripts/taste_full_history.py offline --output runs/hobbhahn-replay
```

One new prediction from a saved model, using an environment-configured API key
and a separate $0.01 maximum (not run during packaging):

```python
from autoresearch.taste.paper_backend import PaperOpenAILLM
from autoresearch.taste.usermodel import load_model
model = load_model(
    'results/fidelity/hobbhahn-full-paper-05/exports/m2/usermodel.json',
    PaperOpenAILLM(max_usd=0.01, max_request_attempts=3),
)
print(model.predict('What should we investigate next?', [
    'Check whether the result survives a matched control.',
    'Scale the promising experiment to more examples.',
]))
```

This final comparison reused cached live responses. Per-method cost describes
new work in this attempt; the $4.207126 total includes earlier costs and held
reservations. All prior run ledger files are retained in `earlier-attempts/` and
`budget.json`. Additional live work must count those commitments against the
remaining allowance. See `interface-checks.json` for cached-live handoff checks.
