# Taste-track sponsor features: real distractors (Exa) and disagreement-driven questions (past.dev)

Two additions to the user-model tracks (PLAN 6.3, 10). Both are standard library only, and every
test runs offline with fakes.

## 1. Real distractors for the time split (Exa)

`autoresearch/taste/real_distractors.py`

timesplit's held-out pairs set the researcher's real post-T decision against a named, a
contemporaneous (LLM-paraphrased) or a generated alternative. This module builds a second
held-out set in which the alternative is a **real project by someone else**, published after T,
as close in topic as the band allows. A judge cannot win by spotting the invented option,
because neither option is invented.

How a pair is made, for each of his `research__*` corpus documents dated on or after T:

1. **Search.** Exa search on the project's title and first sentence, dated from
   max(T, date − 6 months) to date + 6 months, with `exclude_domains` and `exclude_text` from his
   `identity.json`.
2. **Verify** (`verify_candidate`). Authors come from arXiv metadata (as in `scrape.py`), else
   from Exa's author field. A result with no author evidence is dropped. A result is also dropped
   if any author is him (`scrape._is_him`) or matches his `banned` names, if its URL is one of his
   corpus or harvest-manifest URLs, if it mentions him (`exclude_text` in its author field,
   highlights or summary), or if its verified date (arXiv v1, else Exa) falls before T.
3. **Match** (`match`). TF-IDF cosine on title + summary (`taste/textsim.py`). A candidate
   qualifies when `lo <= cos < hi` and its title is not a near copy of his (word Jaccard < 0.6).
   Each project gets its closest qualifying candidate, and a candidate is used for one project at
   most. A project with nothing in the band is skipped and counted (`no_candidate_in_band`).
4. **Render.** `timesplit.render_pair` (the same prompt and the same `check_pair` form checks)
   writes it, and `timesplit._pair_row` builds the row. So the row has every timesplit field, with
   `decision_point` D1, `tag` `real_project` and `distractor_source` `"real"`, plus
   `distractor_url`, `distractor_title`, `distractor_date`, `distractor_date_source`,
   `distractor_authors`, `similarity` and `band`. Neither title, nor any of his later titles, may
   appear in the context.

**The similarity band is set on dev data only.** `band` reads one researcher's documents from
before T and nothing held out. For each document it takes the cosine to his most similar other
document. `lo` is the median of those values: a distractor is hard if it is at least as close as
his typical nearest other project. `hi` is the 95th percentile, capped at 0.8: anything closer is
closer than almost any two of his distinct projects, so it is probably the same work. Compute the
band on a dev researcher, not the one under test. `DEFAULT_BAND = (0.15, 0.6)` is an untuned
fallback, and every row records the band it used and where the band came from.

The offline band, computed from the corpora on disk with cutoff 2025-04-01 and kept as a
scratch file, not committed: owain_evans [0.226, 0.371] (34 docs), evan_hubinger [0.268, 0.680]
(108 docs). The two bands differ a lot. The IDF is fitted on a different collection at dev time
than at match time, so treat a band as a starting point and check the `.matches.jsonl` audit.

**Leakage.** `check_leakage` runs before anything is written and fails the build if any pair is
not held out, is dated before T, carries a different cutoff, or has a distractor that is dated
before T, has no verified authors, is by him, or is one of his documents. Nothing is written into
the researcher's directory, so `history_timesplit.jsonl` and every profile built from it are
unchanged.

**Consuming the pairs.** The output is a pairs file in timesplit's format. `<out>.heldout_choices.jsonl`
holds the matching held-out `Choice` rows, built exactly as `timesplit.write_choice_files` builds
them, and `track_eval.load_choices` reads it. `track_eval.run_e2` reads fixed file names in the
researcher's directory. It needs no change for the comparison below. A `--heldout PATH` option on
`track_eval e2` would let it score these pairs directly (owner: track_eval/timesplit).

**Real vs LLM distractors** (`compare`, `compare_accuracy`). One user model is fitted on his
history pairs (`track_eval._fit`) and scored with `track_eval.paired_correct` (both orders) on the
LLM-distractor held-out pairs and on the real ones. The output gives each set's accuracy with a
document-resampled 90% CI, plus `matched`: the per-document accuracy difference (real − LLM) on the
documents present in both sets. Real pairs are per project and LLM pairs are per decision, so
`matched` is the fairer contrast.

```bash
# dev band (offline; reads only pre-T documents)
python3 -m autoresearch.taste.real_distractors band --researcher data/researchers/<dev_slug> --cutoff 2025-04-01 --out runs/track_s/band.json
# pairs: Exa search + the pair rewriter (paid: needs EXA_API_KEY and a model backend)
python3 -m autoresearch.taste.real_distractors --researcher data/researchers/<slug> --cutoff 2025-04-01 \
    --out runs/track_s/<slug>_real_pairs.jsonl --band runs/track_s/band.json --max-usd 5
# writes <out>, <out>.matches.jsonl (audit: every project, its candidate count, match or reason), <out>.heldout_choices.jsonl
# real vs LLM distractors (paid: user-model calls)
python3 -m autoresearch.taste.real_distractors compare --researcher data/researchers/<slug> \
    --pairs runs/track_s/<slug>_real_pairs.jsonl --method m1 --max-usd 10
```

Status: tested offline only. No live Exa search or rewriter call has been run.

## 2. Disagreement-driven questions (past.dev)

`autoresearch/taste/active_queries.py`, plus a `label` command in `python3 -m autoresearch.taste`.

**Disagreements as facts.** When the researcher labels a logged decision and the user model had
picked a different option, a `DISAGREE` fact is written. It has living.py's fields (key, run, arm,
iter, point, confidence, context, action, taste) plus `by=researcher` and `label=<her option>`.
A `LABEL` fact with the same key is written alongside it, so `living.pending` stops listing the
decision. The key is `living._key(run, iter, point, context)`, the same key the loop's own
override fact (`DecisionLog`) uses. One decision therefore has one key across LABEL, the loop's
DISAGREE and the researcher's DISAGREE. No new fact kind was added. `disagreements` back-fills facts
for answers given through trackp's own `label`/`record`, and running it again writes nothing new.
Facts go to past.dev when `PAST_API_KEY` is set and to the local JSONL store otherwise.

**The queue.** It holds the unlabelled D1–D6 records from runs' `decisions.jsonl`, using trackp's
own pending logic, so one item is the same as one trackp label item. They are ranked by
uncertainty:

| source | when | score |
|---|---|---|
| `committee` | `--usermodel` given several saved models | entropy of the mean distribution + Jensen–Shannon disagreement, each ÷ log k |
| `model` | one saved model | normalised entropy of its distribution |
| `logged_calibrated` / `logged` | the record's own `user_model_choice`/`confidence` | normalised entropy, confidence on its pick and the rest spread evenly; Platt-calibrated on her earlier labels once ≥ 8 exist with both outcomes |
| `none` | no user model was consulted | 1.0 (maximal) |

A diversity term then spreads the queue: greedy maximal marginal relevance over TF-IDF of context +
options. Each step picks the item with the highest `(1 − d)·uncertainty − d·max similarity to items
already queued`, with d = `--diversity`, default 0.3. Queue rows carry trackp's item `id`, the
`decisions` file, the score and its source, and the `fact_key`.

```bash
python3 -m autoresearch.taste.active_queries queue --researcher <slug> --out runs/<slug>_queue.jsonl \
    [--decisions runs/*/decisions.jsonl] [--diversity 0.3] [--usermodel a.json b.json --backend ... --model ...]
python3 -m autoresearch.taste label --researcher <slug> --queue runs/<slug>_queue.jsonl [--limit 10]
#   asks in queue order (trackp's terminal loop, answers in labels.jsonl), then writes LABEL/DISAGREE facts
python3 -m autoresearch.taste.trackp record --researcher <slug> --id <queue row id> --choice <n> --decisions <row's decisions file>
#   an agent answering one queued item in chat; follow with `disagreements` to write its facts
python3 -m autoresearch.taste.active_queries disagreements --researcher <slug>
```

**The simulation** (the demo: a better user model from fewer labels). It runs offline on pairs that
are already labelled. Each seed makes one group-aware train/test split, and both strategies start
from the same 4 random labels. Then 4 labels at a time are added (8 for the text pairs), either at
random or by the uncertainty rule above. The uncertainty rule uses a 5-member bootstrap committee
of a stdlib Bradley–Terry learner plus the diversity term. Test accuracy is recorded after every
batch. The output has the mean curves, the per-seed area-under-curve (ALC) gain with a 90%
bootstrap CI over seeds, the labels each strategy needs to reach 95% of full-pool accuracy, and the
share of queried labels on which the current model disagreed.

```bash
python3 -m autoresearch.taste.active_queries simulate --choices data/researchers/demo_realist/choices.jsonl \
    --out results/taste_active_queries/demo_realist --seeds 0 1 2 3 4 5 6 7 8 9
python3 -m autoresearch.taste.active_queries simulate --choices data/researchers/marius_hobbhahn/history_timesplit.jsonl \
    --out results/taste_active_queries/marius_hobbhahn_history --seeds 0 1 2 3 4 5 6 7 8 9 --max-labels 120 --batch 8
```

Results (offline learner, 10 seeds, `results/taste_active_queries/*.{json,md}`):

| pool | pairs | ALC random | ALC uncertainty | gain (90% CI) |
|---|---:|---:|---:|---|
| demo_realist (synthetic, 7 features) | 160 | 0.866 | 0.858 | −0.008 (−0.014, −0.002) |
| demo_contrarian (synthetic, 7 features) | 160 | 0.819 | 0.830 | +0.011 (−0.009, +0.034) |
| marius_hobbhahn history pairs (text, bag of words) | 373 | 0.590 | 0.609 | +0.019 (+0.003, +0.035) |

Read these honestly. On the low-dimensional synthetic demo data, random labelling learns about as
fast as uncertainty labelling, and on demo_realist it is slightly faster: the uncertain pairs there
are mostly the noisy ones. On the higher-dimensional text pairs, uncertainty ordering gives a small
gain whose interval excludes 0. That learner is a bag-of-words model and partly learns the wording
of real vs distractor options, so this is a property of the queue, not a real user-model accuracy.
In every pool, uncertainty ordering asks about more decisions on which the current model disagrees
with the label (0.29 vs 0.17 on demo_realist). Those are the DISAGREE facts the living user
model learns from. The settings were not tuned on these results.
