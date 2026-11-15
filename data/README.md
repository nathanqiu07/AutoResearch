# Data catalog

Everything committed under `data/`: what each file is, whether it is **raw** (collected from
people or outside sources, and lost if deleted) or **derived** (rebuilt by a command), who
writes it and what governs its use. Files stay where the code expects them; this catalog is
the index. `tests/test_data_catalog.py` fails when a folder, or a file in a researcher's
folder, is missing from the tables below, so add a row when you add one.

Not here: `runs/` (gitignored run outputs, e.g. `runs/<run_id>/decisions.jsonl`) and
`results/` (committed experiment outputs and `results/prereg/` pre-registrations).

## Folders

| Folder | Holds | Raw or derived | Written by | WS | Use and provenance |
|---|---|---|---|---|---|
| `researchers/` | One folder per person (layout below), plus `tracks.json` mapping the personal (P) and public (S) tracks to a slug, and `agreement.jsonl`, the personal-track item gate: a blind Sonnet 5.5 judge's 10 votes per trade-off item (5 per option order), keyed by question and pole texts, shared by every person (derived, paid; `trackp gate`). An item with more than 80% of votes for either option is never shown | mixed | `trackp`, `timesplit`, `track_eval`, `scripts/make_demo_data.py` | B | Consent per person in `<slug>/CONSENT.md`; no answers before it is ticked |
| `trackp/` | `tradeoffs.jsonl`, the personal-track trade-off bank | raw (hand-written) | by hand | B | Sources must not include anything by a tester (no Hobbhahn/Apollo material) |
| `prefdata/` | `prism-splits.json`, `prism-splits-removed.json` (split manifest; the data goes to `runs/prefdata/`) | derived | `python3 -m autoresearch.taste prepare` | A | PRISM dataset |
| `benchmarks/` | EvalAwareBench split and convert report, EvalDetect probes and provenance | derived (downloads in gitignored `raw/`) | `scripts/convert_evalawarebench.py` | C1 | Downloads are untrusted; see its README |
| `labels/` | Hand labels for the A1 judge (`<name>.jsonl`) and their `transcripts.jsonl` | labels raw (human), transcripts derived | `autoresearch calibrate --dump-transcripts`, `autoresearch label-transcripts` | C1 | See its README |
| `real_corpus/` | `wildchat_sample.jsonl`, 200 first user turns | raw (external) | `python3 -m autoresearch corpus --n 200` | C1 | allenai/WildChat-1M, ODC-BY; see its README |
| `petri/` | `seeds_v2.jsonl`, `stock_auditor_prompt.txt` | raw (upstream Petri, edited by hand) | by hand | C2 | Upstream Petri |

## A researcher's folder: `researchers/<slug>/`

The same layout for every person. Track: P = personal (`trackp`), S = public (`timesplit`,
`track_eval`), demo = synthetic. Raw files cannot be rebuilt: never overwrite or delete them.

| File | What | Raw or derived | Written by | Track |
|---|---|---|---|---|
| `CONSENT.md` | The person's consent and its scope | raw | `trackp init` template (P), by hand (S), Profile Studio (P) | P, S |
| `seed_choices.jsonl` | The person's answers to the trade-off questionnaire | raw (human) | `trackp answer` / `record`, Profile Studio (through `trackp.record`) | P |
| `labels.jsonl` | The person's choices at the loop's decisions D1–D6 | raw (human) | `trackp label` | P |
| `recheck.jsonl` | Re-asked items, for the noise ceiling | raw (human) | `trackp recheck` | P |
| `seed_pairs.jsonl` | Questionnaire items built from `trackp/tradeoffs.jsonl` | derived (append-only: answers point at its ids) | `trackp seed-pairs` | P |
| `history.jsonl` | Choices the user model was fitted on | derived | `trackp` fit | P |
| `identity.json` | Who the person is, for the harvest | raw | `timesplit harvest` | S |
| `harvest_manifest.jsonl` | Each harvested document with its source and date | raw (external) | `timesplit harvest` | S |
| `corpus/` | The person's writing, one `.txt` per document (demo: synthetic) | raw (external); studio questionnaire answers raw (human) | `timesplit harvest` (S), `make_demo_data.py` (demo), Profile Studio uploads, imports and questionnaire (`autoresearch/studio/`) | P, S, demo |
| `extraction/` | `exa.jsonl`, `decisions.jsonl`, `checked.jsonl`, `rejected.jsonl`, `distractors.jsonl`: decisions taken from the corpus | derived (paid) | `timesplit extract` / `check` / `distract` | S |
| `pairs_timesplit.jsonl` | Decision pairs, before and after the cutoff date | derived | `timesplit pairs --cutoff` | S |
| `history_timesplit.jsonl` | Pairs before the cutoff | derived | `timesplit pairs` | S |
| `heldout_timesplit.jsonl` | Pairs after the cutoff, the test set | derived | `timesplit pairs` | S |
| `review_timesplit.jsonl` | Human check of held-out distractors | raw (human) | `timesplit review` | S |
| `gate_timesplit.jsonl` | Blind-judge gate results; runs once per pair set | derived (paid) | `track_eval` gate | S |
| `usermodel.json` | The fitted user model the loop loads | derived | `trackp` fit, `track_eval` | P, S |
| `choices.jsonl` | Synthetic choices | derived | `scripts/make_demo_data.py` | demo |
| `hidden_weights.json` | The synthetic person's true weights | derived | `scripts/make_demo_data.py` | demo |
| `profile.json` | Extracted taste profile | derived (may hold hand edits, marked `sources.manual_edit`) | `make_demo_data.py`, `taste/researcher.py`, Profile Studio build | P, S, demo |
| `studio.json` | Profile Studio metadata: name, bio and its source, questionnaire answers, summary card, raw extracted principles, build log. Present only in folders the studio made; others it shows read-only | questionnaire answers raw (human), the rest derived | Profile Studio (`autoresearch/studio/`) | P, S |
