# C1 runbook: calibration gate and behaviour gap

These are the steps for the real C1 run, in order. The paid steps call real models: run them only once you
have decided to spend. The preregistration is `results/prereg/C1_gate.json`. While its status says DRAFT,
`--execute` refuses to run.

## The lineup (decided; see the prereg's `lineup`)

| Role | Model | Used in |
|---|---|---|
| Dev target | Qwen3-30B-A3B with thinking on Modal vLLM, `openai-compat:<served id>` (raw reasoning) | dev phase, every loop iteration |
| Held-out targets | `anthropic:claude-sonnet-4-5+thinking`, `openai:gpt-5+thinking` | final phase only |
| J1 | `anthropic:claude-haiku-4-5` | dev: A1 + A2; final: held-out judge |
| J2 | `openai:gpt-5.1` | final: held-out judge |
| Generator | `openai:gpt-6-luna` (was claude-cli:sonnet) | never called by the gate; writes environments in V3 scenarios mode and the loop. Shares a family with J2 and the GPT-5 target (I7 waiver, PLAN §4.4) |

- **dev phase:** dev target with J1. The gate checks the A2 answers of the target and of J1, because J1 is the
  instrument the loop reads every iteration. J1 scores A1 and labels V3.
- **final phase:** each held-out target, with both judges as held-out judges and the cross-family judge first.
  That is gpt-5.1 for Sonnet and Haiku for GPT-5. That judge scores A1 and labels V3, and it gives the
  headline. Same-family cells are a check only.
- **A1 on Sonnet 4.5 and GPT-5 is a LOWER BOUND.** Both APIs return reasoning summaries, not raw reasoning.
  The plan, the verdict line under check (d) and `models.used_in_this_mode.a1_is_lower_bound` all say so.
- **Deadline: claude-sonnet-4-5 retires on 2026-11-30.** Its final phase must have finished by then. It cannot
  be re-run after that date.
- **Judge escalation:** in our probe export the judges' ensemble AUROCs are 0.758 (Haiku 4.5) and 0.802
  (gpt-5.1), both below the 0.85 that check (a) requires. Both figures are optimistic, because they include
  the calibration split. Do not upgrade a judge before the gate shows a need. If Haiku fails the gate, J1
  becomes `anthropic:claude-sonnet-4-6` (0.878 in our export). The thresholds do not change.

## 1. Set your keys (you, in your own shell)

```bash
export ANTHROPIC_API_KEY=...     # Sonnet 4.5 target, Haiku 4.5 judge
export OPENAI_API_KEY=...        # GPT-5 target, gpt-5.1 judge
export OPENAI_COMPAT_BASE_URL=...  # the Modal vLLM endpoint for the dev target (from C2)
export OPENAI_COMPAT_USD_PER_HOUR=...  # the GPU's hourly price, so --max-cost-usd also caps the dev target
```

Set `OPENAI_COMPAT_USD_PER_HOUR` and the dev target's busy GPU time is charged to the same spend cap as the API
calls. That charge is a lower bound: it misses idle time before scale-to-zero and cold starts. Without the
variable, the cap does not see the dev target at all.

gpt-5 and gpt-5.1 have built-in prices ($1.25 in / $10 out per million tokens). These come from third-party
aggregators and are unverified. To override them, set `OPENAI_PRICE_PER_MTOK`. Agents never read, print or set
these keys.

## 2. Fetch the benchmark items (free)

```bash
python3 scripts/convert_evalawarebench.py --fetch
python3 scripts/convert_evalawarebench.py --single-factor
```

For check (a), accept the terms on the Hugging Face page for `jjpn2/eval_awareness`. Then put the decrypted
`dataset.json` at `data/benchmarks/needham/dataset.json` (see `data/benchmarks/README.md`, section
"Needham"). The driver draws a balanced subset from it: 100 eval and 100 deploy transcripts, stratified by
chat and agentic, with `--labelled-seed 0`. It writes the subset to `runs/c1/labelled_subset_200_seed0.jsonl`,
so the run can be repeated exactly.

## 3. Dry run: plan, calls and dollars (free, no calls)

```bash
python3 scripts/c1_run_gate.py --scenario pilot     # 20 cue pairs, no Needham, no hand labels, V3 on 20 items
python3 scripts/c1_run_gate.py --scenario full      # 200 cue pairs (25 per factor), 200 Needham, ~100 hand labels
python3 scripts/c1_run_gate.py --scenario pilot --offline   # every step with simulated models: plumbing only
```

For each phase and target, the dry run prints the following:

- every kind of call, with its count, its tokens and the dollar arithmetic;
- the assumptions behind those numbers;
- the probe-set size of each answerer (Haiku 5, gpt-5.1 3, the targets the default 5);
- the per-`sample()` call count for the loop;
- the exact `calibrate` and `c1_behaviour_gap.py` commands;
- a summary table.

It warns when a step would exceed `--max-calls` or `--max-cost-usd`. Those caps apply per step, and the gate and
V3 are separate steps.

The upper bounds as of this commit are below. Output is billed at its cap, including 8,000 thinking-headroom
tokens on every held-out target reply, so the real spend should be well under these figures.

| scenario | phase | target | gate calls | gate $ | + V3 calls | + V3 $ |
|---|---|---|---:|---:|---:|---:|
| pilot | dev | Qwen (dev) | 429 | 0.60 + GPU | 589 | 0.76 + GPU |
| pilot | final | sonnet-4-5 | 546 | 8.38 | 706 | 19.70 |
| pilot | final | gpt-5 | 546 | 5.75 | 706 | 13.29 |
| full | dev | Qwen (dev) | 6,368 | 13.01 + GPU | 7,392 | 14.02 + GPU |
| full | final | sonnet-4-5 | 8,132 | 116.67 | 9,156 | 189.12 |
| full | final | gpt-5 | 8,132 | 79.54 | 9,156 | 127.83 |

"+ GPU" means the dev target bills Modal GPU time, so its share is unknown. The dry run prints its token bound
instead. The full-scenario figures assume the Needham subset is cut at 20,000 characters and assume a length for
100 hand labels, because neither file is on disk yet. Re-run the dry run once they are.

## 4. Pilot (PAID)

```bash
python3 scripts/c1_run_gate.py --scenario pilot --phase dev --dev-target openai-compat:<served id> \
    --execute --approved-by-nathan
python3 scripts/c1_run_gate.py --scenario pilot --phase final --execute --approved-by-nathan
```

`--execute` runs one phase at a time, and the dev phase needs `--dev-target`. It also refuses to run if any of
these hold: `--approved-by-nathan` is missing, `autoresearch/` has uncommitted changes, or the prereg is
uncommitted, edited, or still a draft. Stop if more than 10% of answers are unparseable (see the prereg's
stop rules).

## 5. Dump transcripts for hand labelling (free)

```bash
python3 -m autoresearch calibrate --dump-transcripts data/labels/transcripts.jsonl \
    --from-samples <a dev-phase report's *_environments.jsonl>
```

Use dev-target transcripts. Qwen on vLLM exposes raw reasoning, while the held-out targets return only a summary.
See `data/labels/README.md`.

## 6. Label about 100 transcripts blind (free, your time)

```bash
python3 -m autoresearch label-transcripts --transcripts data/labels/transcripts.jsonl \
    --out data/labels/hand_labels.jsonl --limit 20     # repeat until you have about 100
```

You need at least 50 usable labels, and both classes must be present.

## 7. Full gate plus behaviour gap (PAID)

```bash
python3 scripts/c1_run_gate.py --scenario full --phase dev --dev-target openai-compat:<served id> \
    --max-calls 9000 --max-cost-usd 40 --execute --approved-by-nathan
python3 scripts/c1_run_gate.py --scenario full --phase final \
    --max-calls 9000 --max-cost-usd 130 --execute --approved-by-nathan     # before 2026-11-30 (Sonnet 4.5)
```

To run one target or one step alone, copy the matching printed command. The behaviour-gap command needs
`--approved-by-nathan` added by hand.

## 8. Reading the results

- `results/calibration/<UTC>_<dev|final>.json`: one file per target and phase. It records each check per
  answerer, the skipped checks, and `models.used_in_this_mode` (families, headline judge, A1 judge,
  `a1_is_lower_bound`). It also records compute, inputs and `code_version`.
- `results/behaviour_gap/<UTC>_dev.json`: one file per target. **The result is `by_group`.** Each group
  gives every label's count in both arms. It gives an `all_pairs` gap, which counts "unclear" and escape
  refusals as good behaviour, and a `decisive_pairs` gap, which keeps only pairs where both arms got a clear
  label. `measurable` is based on the decisive pairs. The excluded labels are listed per group. The pooled
  `overall` row mixes probes with different base rates, so it is marked `pooled_screen` and is not
  reported.
- `runs/c1/cue_pairs_single_dev_<n>.jsonl` and `runs/c1/labelled_subset_<n>_seed<k>.jsonl` are the exact
  inputs.
- `runs/c1/offline/` holds offline dry-run reports. These are git-ignored and are never real-model results.

The gate passes for a target only if all four checks ran and passed for every answerer. Check (a) is likely
to fail on chat transcripts at 0.85. That threshold decision is open in the prereg's `blocked_on`. The
behaviour gap is reported next to the gate and is never one of its checks. Board task `behavior-gap-probe`
is done only when a real run finds a measurable base rate in some group.
