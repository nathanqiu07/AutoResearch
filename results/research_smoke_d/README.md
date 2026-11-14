# WS D live smoke: one cheap seed per arm (2026-11-14)

Code version: `d49802193ec9` (see `CODE_VERSION`), run from a git worktree pinned at that commit.
Backend: `--llm claude-cli` (generator/judge `sonnet`, target `haiku`). Settings per arm: scenario
`metric_inflation`, 2 iterations, 3 samples per evaluation, 1 evaluation per iteration, 4 proposals,
no web, no shared memory, no faithfulness or realism samples, seed 0, fresh memory per arm.

**Purpose:** check that every runnable arm works end to end against real models and what it costs.
These are **not findings**: n = 3 per evaluation, one seed, and the claude-cli backend leaks harness
context to the target (PLAN I13). R1-P / R1-S were not run (no `data/researchers/tracks.json` yet).

| arm | calls | $ (API-equivalent) | wall | sample errors | validated / tested | decision records (user model consulted) | claims supported |
|---|---|---|---|---|---|---|---|
| R0 | 72 | 0.91 | 7.1 min | 0 | 0 / 2 | 11 (0) | 1 / 3 |
| R1-demo_realist | 72 | 0.61 | 5.8 min | 0 | 0 / 2 | 12 (2, D1) | 2 / 4 |
| R1-demo_realist-prompt | 72 | 0.56 | 5.2 min | 0 | 0 / 2 | 11 (0) | 2 / 3 |
| R1-bad | 72 | 0.53 | 5.3 min | 0 | 0 / 2 | 12 (2, D1) | 1 / 4 |

All 46 decision records validate against the schema. No generated environment was flagged for
setting drift. Baseline scores were 0.46-0.48 in every arm; no change was accepted (all P(better)
< 0.9), as expected at this sample size.

**Claim checker on real drafts.** 7 of 14 drafted claims were rejected. Most were genuine
overclaims ("improves" citing findings whose status was "rejected"; "no clear effect" citing a
clearly worse finding). The rest were misquoted numbers for claims citing several findings: the
drafting prompt did not say which delta to state, so the model gave a sum, a max or 0. The prompt
now asks for the mean of the cited deltas (commit after `d49802193ec9`); these runs predate that fix.

**Cost vs estimate.** ~$0.53-0.91 per run of this size, i.e. about $0.008-0.013 per call. Scaling to
the E4 draft settings (items_per_iter 4, samples 2, 8 iterations) gives roughly 600-900 calls, about
$5-12 per run, within PLAN 11's $8-15 estimate.

`e4b_packets/` holds blinded rating packets built from these records
(`scripts/make_rating_packets.py make`), as a check of the E4b pipeline on real records.
Run logs and decision files under `runs/smoke_d/` are scratch (gitignored); the reports and
`*_decisions.jsonl` here are the committed copies.
