# eval/: folded into the main pipeline

This folder held a standalone Petri 2.0 eval-awareness pipeline (four conditions, its own
EvalAwareBench judge and post-hoc question). To keep **one** scorer for agentic
eval-awareness numbers (so E3b can't come out two ways), it was folded into the repo's
C2 pipeline on 2026-11-15. The old code is in git history (commit df7635e).

| Was in `eval/pipeline/` | Now |
|---|---|
| `run_petri.py`, `extract.py`, `common.py` (audits, transcript and reasoning extraction, Petri judge parse failures as null) | `harness/petri/run_audits.py`, `harness/petri/transcript.py` (AuditSeed → AuditResult JSONL) |
| `eab_judge.py`, `posthoc.py` (A1 on reasoning, post-hoc P(eval)) | C1's judges via `PetriMeasurer` (`autoresearch/research/petri_measure.py`): A1 audit judge, A2 probe questions, validity, every judge's A1/A2 |
| `score.py` (per-condition means, paired bootstrap CIs vs stock) | `scripts/c2_e3b.py` |
| `control.py`, taste conditions (rewritten seeds) | rewrites come from the research loop (`research --setting agentic`, arms R0/R1) or any file of AuditSeeds with `variant: "ours"`, compared by `scripts/c2_e3b.py` |
| `modal_vllm.py` | `harness/modal_vllm.py` (dev target with `--reasoning-parser`) |
| `config.yaml` | `configs/models.json` (the team's model lineup) |
| `conditions/stock/` seeds | `data/petri/seeds_v2.jsonl` (same 24 seeds, 12 dev / 12 hidden) |

Kept here: `petri-setup/` (how the 24 seeds were chosen, the stock auditor prompt) and
`vendor/` (pinned Petri 2.0 source, installed by the harness environment, and the
EvalAwareBench prompts).
