# Personal-track runbook (WS B)

The personal track (code: `trackp`, track key `P`) is one team member's own research choices (PLAN §6.3, §12.2). This runbook is
for an agent collecting them. All commands are
`python3 -m autoresearch.taste.trackp <command>`, run from the repo root. After `init`,
`--researcher` defaults to the personal-track person in `data/researchers/tracks.json`.

**Start every session with `status`.** Its `next` list says what to run, in order.

## 0. One sitting (each person, at a terminal)

Each team member gets their own personal-track dataset. The person runs

```bash
python3 -m autoresearch.taste.trackp start            # asks for their full name
```

It creates `data/researchers/<slug>/` (slug from the name), writes the built-in seed items,
shows the consent statements and records the person's agreement, then asks the seed items.
They quit with `q` and run `start` again with the same name to resume. `start` makes no model
calls. Like `init`, it points the personal track (key P) at that person. The sections below are
the step-by-step equivalent, for agents and for the paid extras.

## 1. Set up (once)

```bash
python3 -m autoresearch.taste.trackp init --researcher <slug> --name "<full name>"
python3 -m autoresearch.taste.trackp seed-pairs
```

* The user decides who the person is (not Ethan).
* Before any answers are collected, the person ticks every box in
  `data/researchers/<slug>/CONSENT.md`, and `status` lists this step until they have.
* `seed-pairs` makes no model calls. It writes 21 items: a stance item for each of the 14
  trade-off axes, and one scenario item for each of the 7 axes where the loop lets taste act
  (D1, D3 when inconclusive, D4, D5), each in a different environment.
  `--llm-scenarios K --llm <backend>` adds LLM-written scenario items. That is a paid call,
  so ask the user first.
* Then run `balance --backend <b> --model <m>` (paid, ask first) and `review`. `balance` is the
  public track's blind judge: a model with no history answers in both orders, and an item where
  it gives one option 0.75 or more both times is flagged one-sided. A taste item should leave it
  roughly undecided.
  `review` lists the items awaiting a decision, and `review --id <pair_id> --decision
  approve|drop` settles one. Someone other than the person answering does both.

## 2. Collect answers

Only the person answers. Never pick an option for them, and never guess a reply.

**In chat (agents):**

```bash
python3 -m autoresearch.taste.trackp status          # stop if consent is still pending
python3 -m autoresearch.taste.trackp pending --kind seed --limit 50
python3 -m autoresearch.taste.trackp record --id <id> --choice <n>
```

1. Before the first item, tell the person once: it takes about 12 minutes, they can stop and
   resume at any point, there are no right answers, and each question asks what they would do.
2. `pending` serves scenario items grouped by their `group` field, then the stance items.
   Show a group's `context` once, then each item's `question` and its `options` one at a time,
   numbered 1 and 2 exactly as printed. Stance items come last. Fetch the whole list at once so
   groups are not split; a skipped item stays pending, so keep track of the ids you skipped.
3. Never name the axis, the poles or the decision point.
4. Say nothing about the content: no opinion, hint, paraphrase or "good choice". If they ask
   what an option means, re-show it word for word.
5. Run `record` right after each answer. Don't ask why; pass `--reason` only if they
   volunteer one, in their words. If they want to skip an item, or pick neither, don't record it.
6. Offer a break at the halfway point. At the end, run `status` and report what was answered
   and what is left.

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

* First run `agree --backend <b>` (paid, ask first; default model `claude-sonnet-5-5`). It is
  the public track's agreement filter: a blind judge with no history answers each *answered*
  item in both orders, and `e2` and `fit` drop an answer from every split (history, val and
  test) when the judge gives the option the person chose more than 0.8 both times. Such an
  item tests generic sense, not their taste. Items the judge confidently decides against the
  person stay. Probabilities are recorded in `agreement.jsonl`, so a new threshold needs no new
  calls; `e2` and `fit` refuse answers that were never judged, and `status` says when to run it.
  This is separate from `balance`, which checks items before anyone answers.
* `e2` writes `results/e2/P_<slug>.json` and refuses to overwrite it. Report the
  accuracies next to the `noise_ceiling` in the same file.
* `fit` writes `usermodel.json` for the R1-P arm and `history.jsonl` for R1-P-prompt.
  Fit with the same backend and model the loop's judge uses: `load_model` raises if the
  saved backend differs, and the only fix is to fit again.
* Before E4, pick a `--label-cutoff` date. Labels from runs on or after it are held out.
  Use the same cutoff for `e2` and `fit`.

## Files (`data/researchers/<slug>/`)

`seed_pairs.jsonl`, `seed_choices.jsonl`, `labels.jsonl`, `recheck.jsonl`, `agreement.jsonl`, `usermodel.json`,
`history.jsonl`, `CONSENT.md`. All are append-only except the two that `fit` rewrites.
Commit the answer files after each session; stage them by name.
