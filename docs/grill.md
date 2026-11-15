# Grill: patch a user model for the current task

`autoresearch/taste/grill.py` (WS B). It interviews the person about the decisions the research
loop faces on the task at hand, like the "grill me" skill, and patches their user model with the
answers. Their model then decides the way they would on this task, instead of only the way their
general history suggests.

## The loop

1. **Questions for this task.** There are four sources, most grounded first:
   * `decisions`: records the loop logged on this task (`--decisions runs/<run>/decisions.jsonl`), asked as logged.
   * `bank`: the trade-off items in `data/trackp/tradeoffs.jsonl` closest to the task text (TF-IDF), framed as decisions on this task.
   * `llm`: questions and follow-ups written by `--backend` (paid unless offline). Malformed rows are dropped, never repaired.
   * `agent`: questions an agent writes in chat with `add` (the `grill-usermodel` skill).
2. **Model's guess first.** With `--um-backend` (the backend the model was fitted on), every question
   carries the user model's prediction and confidence. That guess is shown as the recommended answer.
3. **Least sure first, branches depth-first.** `pending` lists the newest follow-ups first. After
   them come the questions the model is least sure of. Questions with no guess come last, in queue order.
4. **Follow-ups.** A disagreement with the model, or a stated reason, opens follow-up questions on
   that branch. In the terminal they come from `--backend`; in chat the agent writes them.
5. **Patch.** `apply` writes the answers into `usermodel.json`. `revert` undoes it.

## Files

`data/researchers/<slug>/grill/<task>/`:

| File | Contents |
|---|---|
| `meta.json` | task slug and text |
| `questions.jsonl` | every queued question: point, context, options, source, parent/depth, model guess and confidence |
| `answers.jsonl` | `choice` rows (chosen index, reason, model guess, `agreed`), `skip` rows, `principle` rows |

`data/researchers/<slug>/usermodel.base.json` is the unpatched model. `apply` saves it the first
time, and replaces it whenever `usermodel.json` is a fresh, unpatched fit.

## What a patch does to each method

| Method | Principles | Exemplars | Effect |
|---|---|---|---|
| m5, m6, m7 | appended | appended to `metadata.retrieval_pool` | retrieved by TF-IDF when a decision resembles the answer |
| m1, m2, m3 | appended | appended to `artifacts.exemplars` | shown on every prediction |
| m0, m4 | — | — | `apply` refuses: they read neither, so refit instead |

* A principle is the person's own words, scoped to the task: `While working on <task>: ...`. It
  comes from each stated principle and from each answer that came with a reason.
* An answer with k options becomes k−1 pairwise choices (`source: "grill"`): the chosen option against each other one.
* m7's Platt calibration was fitted before the patch. The patched file records this in `metadata.grill.notes`.
* `metadata.grill` records the base sha, the time, and per task the answer count and the sha of `answers.jsonl`.

## Rules that keep results honest

* Grill answers stay out of trackp's splits (history/val/test). They are corrections for one task,
  not held-out evidence.
* A patched model is not the model E2 evaluated. R1 with a patched model and its prompt-arm
  control (`advisor.history_text`, which does not read grill answers) differ by more than the
  method. Report which model a run used (`metadata.grill` is in the file the loop loads).
* `apply` refuses a patched `usermodel.json` whose base file is missing or changed.

## Commands

```bash
# terminal, no paid calls: logged decisions + trade-off bank, no model guess
python3 -m autoresearch.taste.grill run --researcher <slug> --task eval_awareness --decisions runs/<run>/decisions.jsonl
# with the model's guess and LLM follow-ups (paid: needs the user's OK)
python3 -m autoresearch.taste.grill run --researcher <slug> --task eval_awareness --backend anthropic --model claude-haiku-5-5 --um-backend <fit backend> --um-model <fit model>
# chat (agent drives it; see .claude/skills/grill-usermodel/SKILL.md)
python3 -m autoresearch.taste.grill start  --researcher <slug> --task-text "..."
python3 -m autoresearch.taste.grill next   --researcher <slug> --task <slug>
python3 -m autoresearch.taste.grill record --researcher <slug> --task <slug> --id <qid> --choice 2 --reason "..."
python3 -m autoresearch.taste.grill add    --researcher <slug> --task <slug> --point D3 --parent <qid> --context "..." --option "..." --option "..."
python3 -m autoresearch.taste.grill apply  --researcher <slug>     # or: revert
```
