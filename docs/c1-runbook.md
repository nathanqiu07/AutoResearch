# C1 runbook: calibration gate and behaviour gap

These are the steps for the real C1 run, in order. Steps 1 to 4 and 8 cost nothing. Steps 5, 7 and 9 call paid
models, so run them only once you have decided to spend. The preregistration is
`results/prereg/C1_gate.json`. While its status says DRAFT, `--execute` refuses to run.

Call counts are upper bounds. Each distinct environment is counted once, because answers are cached; the
single-factor pairs of one task share their without-cue environment. Run any command without `--execute` and
it prints the exact bound for your inputs. Add `--usd-per-call X` to get a cost bound as well.

## 1. Set your keys (you, in your own shell)

```bash
export ANTHROPIC_API_KEY=...     # Sonnet 4.6 target
export OPENAI_API_KEY=...        # OpenAI target (and the judge, if it is OpenAI)
```

If the OpenAI model has no built-in price, also set `OPENAI_PRICE_PER_MTOK='<input>,<output>'` (USD per million
tokens). Without it the backend refuses to start, because the spend cap could not count its calls. Agents never
read, print or set these keys.

## 2. Fetch the benchmark items (free)

```bash
python3 scripts/convert_evalawarebench.py --fetch
python3 scripts/convert_evalawarebench.py --single-factor     # the default cue set; about 0.4 MB
```

These write `data/benchmarks/evalawarebench_{original,minimal_cue,cue_pairs}.jsonl` and
`evalawarebench_single_factor_pairs.jsonl` (240 pairs: one cue on vs all off, 30 dev tasks × 8 factors). Those files are gitignored
(CC BY-NC). The frozen split, `evalawarebench_split.json`, is committed.

Optional, for check (a): accept the terms on the Hugging Face page for `jjpn2/eval_awareness`, fetch the
dataset as described in `data/benchmarks/README.md` (section "Needham"), and put the decrypted `dataset.json` at
`data/benchmarks/needham/dataset.json`. You can also pass `--labelled PATH`.

## 3. Pick the models and finalise the prereg (free)

Choose the OpenAI target id and the judge spec, then fill in `<OPENAI_MODEL>` and `<JUDGE_SPEC>` in
`results/prereg/C1_gate.json`. Settle the open `[decide]` items. Set `status` to `final` and commit the file.

## 4. Dry run (free, no calls)

```bash
python3 scripts/c1_run_gate.py --judge <JUDGE_SPEC> --openai-target <OPENAI_MODEL>+thinking --usd-per-call 0.02
python3 scripts/c1_run_gate.py --offline     # runs every step with simulated models: plumbing only
```

The first command prints each step's command, its call bound, and the inputs that are missing. Any check that
lacks inputs is skipped, and a skipped check fails the gate. The `--offline` results are marked offline, say
nothing about real models, and go to `runs/c1/offline/` (git-ignored), never to `results/`.

The cue set is `--cue-set single` by default: one cue factor on vs all off. The gate number is the pooled
result over all of those pairs. The verdict also prints a per-factor screen (F1–F8: n, mean diff, CI,
fraction moving the right way) with each factor's median prompt length ratio. F2 and F4 change the prompt
length a lot (about +1/3 and ×0.5), so treat a large effect there with suspicion: the scorer may be reacting to
length, not to the cue. `--cue-set all8` (all cues vs none) is the older, blunter test.

## 5. Subset gate: 5 pairs per factor (40) plus 20 behaviour-gap items per target (PAID)

```bash
python3 scripts/c1_run_gate.py --judge <JUDGE_SPEC> --openai-target <OPENAI_MODEL>+thinking \
    --limit 5 --gap-limit 20 --execute --approved-by-nathan
```

With the single cue set, `--limit` applies per factor, so every factor is represented. This makes up to about
1,180 calls with both targets and no labelled set or hand labels. `--execute` also
refuses to run if `autoresearch/` has uncommitted changes or the prereg is uncommitted, edited, or still a draft.
Stop here if more than 10% of answers are unparseable (see the prereg's stop rules).

## 6. Dump transcripts for hand labelling (free)

```bash
python3 -m autoresearch calibrate --dump-transcripts data/labels/transcripts.jsonl \
    --from-samples <a report's *_environments.jsonl>
```

Prefer transcripts from a target that exposes raw reasoning. Sonnet `+thinking` returns only a summary. See
`data/labels/README.md`.

## 7. Label about 100 transcripts blind (free, your time)

```bash
python3 -m autoresearch label-transcripts --transcripts data/labels/transcripts.jsonl \
    --out data/labels/hand_labels.jsonl --limit 20     # repeat until you have about 100
```

You need at least 50 usable labels, and some of them must be aware. The driver picks up
`data/labels/hand_labels.jsonl` automatically. If you saved it elsewhere, pass `--hand-labels PATH`.

## 8. Re-check the bound (free)

Run the step 4 dry run again. It now counts the labelled set and the hand labels. With the full Needham set, the
labelled check dominates the cost: about one call per transcript per probe question per target.

## 9. Full gate plus behaviour gap on all dev items (PAID)

```bash
python3 scripts/c1_run_gate.py --judge <JUDGE_SPEC> --openai-target <OPENAI_MODEL>+thinking \
    --limit 0 --gap-limit 0 --execute --approved-by-nathan
```

This runs all 240 single-factor pairs per target, plus the labelled set and kappa if you have them, plus
behaviour-gap calls (4 × 128 × 2 = 1,024 per target). Before the labelled set, that is up to about 7,200 calls
for both targets. Optional and secondary: add `--cue-set all8 --gap-limit 1` for the all-cues test as well. Each step is capped by `--max-calls` (default 4000) and
`--max-cost-usd` (default $40). The spend cap counts list prices for the anthropic and openai backends. It does not count openai-compat.

To run one target or one step alone, copy the matching printed command. The behaviour-gap command needs
`--approved-by-nathan` added by hand.

## 10. Where the results go

- `results/calibration/<UTC>_dev.json`: one file per target. It records each check's verdict, the skipped
  checks, models, compute, inputs and `code_version`.
- `results/behaviour_gap/<UTC>_dev.json`: one file per target. It records the as-is and with-notice
  misbehaviour rates, the gap with its CI, and `measurable` both overall and per safety/capability group.
- `runs/c1/cue_pairs_<single|all8>_dev_<n>.jsonl`: the exact cue pairs used, which you need to repeat a run.
- `runs/c1/offline/`: offline dry-run reports. These are git-ignored and are never real-model results.

The gate passes only if all four checks ran and passed for every target. The behaviour gap is reported next
to the gate and is never one of its checks. Board task `behavior-gap-probe` is done only when a real run finds a
measurable base rate.
