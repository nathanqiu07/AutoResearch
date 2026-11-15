---
name: grill-usermodel
description: Interview the user, grill-me style, about the decisions the research loop faces on the current task, and patch their user model (data/researchers/<slug>/usermodel.json) with the answers. Use when the user asks to grill them, correct or update their user model / taste model for a task, or "teach the model what I'd do here".
---

# Grill the user to patch their user model for the current task

You interview the user relentlessly but briefly about the decisions the research loop will face on
**the task at hand**, one question at a time, until their user model would decide the way they would.
Each answer becomes part of a task-scoped patch on their `usermodel.json`, the file the loop loads.
The code is `autoresearch/taste/grill.py`; `docs/grill.md` explains what a patch does to each method.

All commands are `python3 -m autoresearch.taste.grill <cmd> --researcher <slug> ...`. JSON goes to
stdout. Never call a paid backend (`--backend anthropic`, `claude-cli`, ...) without the user's OK.
You write the follow-up questions yourself, so the grill needs no paid backend. The only paid part is
the user model's guess: `--um-backend`, which must be the backend the model was fitted on.

## 1. Pin down the task and the person
- Whose model: `--researcher <slug>` (default: the personal-track person in `data/researchers/tracks.json`).
- Which task: a registered name (`--task eval_awareness`), or the user's own words (`--task-text "..."`).
  If a run on this task exists, pass its log: `--decisions runs/<run>/decisions.jsonl`. Those
  decisions are the most grounded questions there are.
- Start: `start --task ... [--decisions ...] [--bank 4] [--um-backend <fit backend> --um-model <m>]`.
  The output gives the task slug (use it as `--task` from now on) and the pending questions.

## 2. Ask, one question at a time
For each question from `next --task <slug>`:
- Show the decision point, the context, the numbered options and any evidence. If there is a
  `recommended` option, give it as **your recommended answer** with the model's confidence: "Your
  model would pick 2 (61%)." This is the grill-me move, so the user corrects a concrete guess.
- Ask for their pick and **why**, in one line. The reason becomes a principle in their own words,
  so never paraphrase it when you record it.
- Record it: `record --task <slug> --id <qid> --choice <n> --reason "<their words>"`.
  Use `skip --id <qid>` if they pass. If they state a general rule ("I never trust one seed"),
  record it with `principle --text "<their words>"`.

## 3. Walk down the branch
After an answer that **disagrees with the model**, or whose reason opens a new question, ask a
follow-up before you move on. Ask what the answer leaves open on this task: the next decision it
implies, where the reason stops applying, or how far it goes. Write it yourself and queue it:
`add --task <slug> --point D1..D6 --parent <qid> --context "..." --option "..." --option "..." [--why "..."]`.
`next` then returns it first (depth-first). Give each follow-up 2-4 concrete options a thoughtful
researcher could really choose between, and do not re-ask what they have already answered.
Stop a branch when the answers start to match the model, or after about three levels.

## 4. Finish
- Stop when the user says so, or when the pending questions are ones the model already gets right.
- Show `status --task <slug>`: answered, skipped, principles, and how often the model agreed.
- Ask before you patch. Then run `apply` (rebuilds `usermodel.json` from `usermodel.base.json`
  plus every task's answers) and show its JSON. `revert` undoes it. If `apply` refuses (m0/m4, or
  no fitted model yet), tell the user why and leave their answers on disk. A refit can use them later.
- Commit the session files and the patched model only if the user asks. If they want workers to
  get the patched model, it is `python3 -m autoresearch.taste.usermodel_store push --researcher <slug>`.

## Rules
- The answers are the user's own research choices and reasons. Record exactly what they said.
- Grill answers stay out of trackp's history/val/test splits. Don't copy them there to raise a score.
- A patched model is not the model E2 evaluated. Say so if the user is about to run an experiment.
