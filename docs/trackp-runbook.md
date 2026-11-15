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
* Before showing an item, a reviewer other than the answerer records a concrete benefit and
  cost for each option under the same constraint. They check that both options preserve the
  required behavior opportunity. Put JSONL rows with `pair_id`, `decision` (`pass`, `reject`,
  or `superseded`), `reviewer`, `reason`, `benefit_1`, `cost_1`, `benefit_2`, and `cost_2`
  in a review file, then run `review-pairs --file <review.jsonl>`. The last four fields are
  required for a pass. The review is stored in shared `data/researchers/item_reviews.jsonl`.
  An unreviewed item stays hidden. This step makes no model calls. The old Sonnet and Luna
  votes remain in `agreement.jsonl` for audit; vote balance does not decide eligibility.

## 2. Collect answers

Only the person answers. Never pick an option for them, and never guess a reply.

**In chat (agents):**

```bash
python3 -m autoresearch.taste.trackp status          # stop if consent is still pending
python3 -m autoresearch.taste.trackp pending --kind seed --limit 50
python3 -m autoresearch.taste.trackp record --id <id> --choice <n>
```

1. Before the first item, tell the person once: it takes about 15 minutes, they can stop and
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

* `e2` and `fit` skip answers to rejected or superseded seed items and refuse an answered
  pair that was never reviewed. The old answer stays in the raw log; it is never transferred
  to revised wording. Labels to logged decisions do not use this item review.
* `e2` writes `results/e2/P_<slug>.json` and refuses to overwrite it. Report the
  accuracies next to the `noise_ceiling` in the same file.
* `fit` writes `usermodel.json` for the R1-P arm and `history.jsonl` for R1-P-prompt.
  Fit with the same backend and model the loop's judge uses: `load_model` raises if the
  saved backend differs, and the only fix is to fit again.
* Before E4, pick a `--label-cutoff` date. Labels from runs on or after it are held out.
  Use the same cutoff for `e2` and `fit`.

## Files (`data/researchers/<slug>/`)

`seed_pairs.jsonl`, `seed_choices.jsonl`, `labels.jsonl`, `recheck.jsonl`, `usermodel.json`,
`history.jsonl`, `CONSENT.md`. All are append-only except the two that `fit` rewrites. The
shared `data/researchers/item_reviews.jsonl` holds review decisions across people.
`agreement.jsonl` holds historical model votes only.
Commit the answer files after each session; stage them by name.
