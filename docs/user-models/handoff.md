# WS A handoff — November 14, 2026

## Current state

All eight methods, the shared interface, PRISM splits, the fidelity runner and
bounded schema search are implemented. Foundation commit: `fd00fe6`. Method commit:
`9c72e05`. Dataset/runner commit: `ee7a308`. See [the guide](README.md) for commands
and [the design](design.md) for assumptions.

The combined repository passed 166 tests after syncing teammates' work. A later
review found an incomplete-search selection bug: an early trial could win after
later trials exhausted the budget. A regression test reproduces that case; search
now reports `incomplete` with no selected configuration whenever any trial fails.

Update 2026-11-14 (Ethan): Chatbot Arena was removed; PRISM is the only
preference dataset. Its 12 duplicate content pairs were all exact repeats (same
labels, same partitions), so `prepare` keeps one copy of each and records the
removals in `data/prefdata/prism-splits-removed.json`. PRISM has 16,693 choices from
723 users (345 development, 378 final test). How to get it: [the guide](README.md),
"Get the PRISM data".

## Choices and their reasons

- Keep development and final users separate, and preserve conversation groups.
  This prevents a repeated conversation from making accuracy look better.
- Start with M0 and M1. More complex methods must show a gain over simply giving
  the model the user's past choices.
- M2 and M3 implement bounded core stages, with adaptations recorded. They are
  not full paper reproductions. See the method table in the guide.
- Reserve separate validation conversations for M7's confidence calibration.
  Too little evidence yields explicitly uncalibrated confidence.
- Export preference artifacts without inventing causal assumptions. Only M4
  learns numeric feature weights. Other methods should be called via `predict`.
- Keep the model/provider replaceable. Refitting is required when changing the
  backend: learned feature weights and calibrated confidence need not transfer.

## Evidence and open work

Synthetic tests verify mechanics, label isolation, selection, persistence, budget
handling and split protection. A tiny Codex CLI synthetic call succeeded; earlier
failed attempts were retained locally. No real preference accuracy or winning
method has been established. Final test users have not been evaluated.

Gio redeemed OpenAI credits in his Personal organization and approved up to $1
for ten development predictions using `gpt-6-luna`. No API key was present in the
checked process environment. The direct Responses adapter is pushed in `816d064`;
the combined suite passed 175 tests after syncing teammates' changes. It makes no
retries, reserves conservative cost before requests and preserves failed holds in
the report. A pilot checkout is pinned to that commit under ignored
`runs/taste-pilot-worktree`. The local `runs/taste-openai-pilot.command` prompts for
the key without echo and writes `runs/fidelity/openai-dev-01/report.json`. No live
API call has run. Do not infer the remaining credit balance from redemption alone.

The first proposed live check is ten development predictions, M0 versus M1, for
one PRISM user (the pinned pilot checkout predates the switch and still targets
Arena; re-point it before running). Question: can both methods make valid, auditable predictions on
real data within the cap? Expected result: valid saved outputs and usage. Errors,
missing usage or inconsistent reload predictions count against readiness. Even
a perfect result on this pilot does not establish preference quality.

Then compare methods on more development users, choose a configuration and model,
and freeze them before the single final invocation. The final command
registers PRISM, the only dataset. Do not delete the final marker to rerun.

## Integration handoff

The harness owner can use `create_method(...).fit(history, validation)`,
`predict(context, options)`, `save(...)`, and `load_model(...)`. Predictions include
choice, probability, rationale and calibration status. The team owns the test of
whether this improves research outcomes; PRISM preference accuracy alone cannot
answer that question. No teammate implementation files were modified for WS A.
