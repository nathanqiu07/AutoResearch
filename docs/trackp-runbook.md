# Track P runbook (WS B)

Track P is one team member's own research choices (PLAN §6.3, §12.2). This runbook is
for an agent collecting them. All commands are
`python3 -m autoresearch.taste.trackp <command>`, run from the repo root. After `init`,
`--researcher` defaults to the Track P person in `data/researchers/tracks.json`.

**Start every session with `status`.** Its `next` list says what to run, in order.

## 1. Set up (once)

```bash
python3 -m autoresearch.taste.trackp init --researcher <slug> --name "<full name>"
python3 -m autoresearch.taste.trackp seed-pairs --n 50
```

* The user decides who the person is (not Ethan).
* Before any answers are collected, the person ticks every box in
  `data/researchers/<slug>/CONSENT.md`, and `status` lists this step until they have.
* `seed-pairs` makes no model calls. `--llm-ideas K --llm anthropic` adds LLM-proposed
  interventions. That is a paid call, so ask the user first.

## 2. Collect answers

Only the person answers. Never pick an option for them, and never guess a reply.

**In chat (agents):**

```bash
python3 -m autoresearch.taste.trackp pending --kind seed --limit 5
python3 -m autoresearch.taste.trackp record --id <id> --choice <n> --reason "<their words>"
```

1. Show each item's `context`, any `evidence`, and its numbered `options` exactly as
   printed, without reordering, summarising or commenting on them, since your opinion
   biases the answer.
2. Ask which number they pick, and why in one sentence. The reason is optional, but it
   is extra signal for the user model, so record it word for word.
3. Run `record` once per answer. If they want to skip an item, don't record it.

**In a terminal (the person alone):** they run
`! python3 -m autoresearch.taste.trackp answer` (or `label`, or `recheck`) and answer
the prompts.

The three kinds of item:

| Kind | When | Notes |
|---|---|---|
| `seed` | after `seed-pairs` | aim for ~50 answers before any R1-P run |
| `label` | after loop runs exist | reads `runs/*/decisions.jsonl`, or pass `--decisions <files>`. Covers D1–D6. The loop's own choice and the arm are never shown |
| `recheck` | from 3 days after the first answers | ~20% of earlier items, options reversed. Gives the noise ceiling. Don't remind the person what they said before |

## 3. Fit and hand off (after WS A selects a method)

```bash
python3 -m autoresearch.taste.trackp e2 --methods m0 m1 <selected> --backend <b> --model <m> --dry-run
python3 -m autoresearch.taste.trackp e2 --methods m0 m1 <selected> --backend <b> --model <m>    # paid: ask first
python3 -m autoresearch.taste.trackp fit --method <selected> --config '<WS A config JSON>' --backend <b> --model <m>
python3 -m autoresearch.taste.usermodel_store push --researcher <slug>
```

* `e2` writes `results/e2/P_<slug>.json` and refuses to overwrite it. Report the
  accuracies next to the `noise_ceiling` in the same file.
* `fit` writes `usermodel.json` for the R1-P arm and `history.jsonl` for R1-P-prompt.
  Fit with the same backend and model the loop's judge uses: `load_model` raises if the
  saved backend differs, and the only fix is to fit again.
* Before E4, pick a `--label-cutoff` date. Labels from runs on or after it are held out.
  Use the same cutoff for `e2` and `fit`.

## Files (`data/researchers/<slug>/`)

`seed_pairs.jsonl`, `seed_choices.jsonl`, `labels.jsonl`, `recheck.jsonl`, `usermodel.json`,
`history.jsonl`, `CONSENT.md`. All are append-only except the two that `fit` rewrites.
Commit the answer files after each session; stage them by name.
