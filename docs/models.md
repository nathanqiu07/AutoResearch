# Models by task

Source of truth: `configs/models.json` (check it with `python3 -m autoresearch.research.models_config`).
Taste-pipeline rows are CLI defaults and can be overridden with `--model`.

## Research loop and measurement

| Task | Model | Spec | Runs on | When |
|---|---|---|---|---|
| Generator / research agent (proposers, critic, distiller) | Claude Sonnet | `claude-cli:sonnet` | Claude CLI | every iteration |
| Target, dev (raw reasoning) | Qwen3-30B-A3B, thinking | `openai-compat:Qwen/Qwen3-30B-A3B` | Modal vLLM, 1× H100 | every iteration |
| Target, held-out | Claude Sonnet 4.5 + thinking | `anthropic:claude-sonnet-4-5+thinking` | Anthropic API | final only, before 2026-11-30 |
| Target, held-out | GPT-5 + thinking | `openai:gpt-5+thinking` | OpenAI API | final only |
| Judge J1, dev (A1, A2, validity) | Claude Haiku 4.5 | `anthropic:claude-haiku-4-5` | Anthropic API | every iteration |
| Judge J1 fallback (if Haiku fails the calibration gate) | Claude Sonnet 4.6 | `anthropic:claude-sonnet-4-6` | Anthropic API | only if needed |
| Judge J2, held-out | GPT-5.1 | `openai:gpt-5.1` | OpenAI API | final only |

## Petri audits (`harness/petri`)

| Role | Dev | Final |
|---|---|---|
| Target | Qwen3-30B-A3B (Modal) | Claude Sonnet 4.5, GPT-5 |
| Auditor | Claude Sonnet 4.6 | Claude Sonnet 4.6 |
| Judge | Claude Haiku 4.5 | GPT-5.1 |

## Taste pipeline (user models)

| Task | Model | Command |
|---|---|---|
| Track P seed-pair ideas | Claude Sonnet 5.5 | `trackp seed-pairs --llm-ideas` |
| Track P E2 (methods vs held-out choices) | Claude Haiku 5.5 | `trackp e2` |
| Track S harvest + decision extraction | Exa (no LLM) | `timesplit harvest`, `extract` |
| Track S decision check, distractors | Claude Sonnet 5.5 (+ Exa) | `timesplit check`, `distract` |
| Track S guessability gate (blind judge) | Claude Opus 5.5 | `track_eval gate` |
| Track S method select / E2 / final fit | Claude Sonnet 5.5 | `track_eval select`, `e2`, `final` |
| TasteBench | Claude Sonnet 5.5 | `tastebench --model` |

## Notes

- Only the dev target gives **raw** reasoning. A1 on the held-out API targets uses vendor summaries, so it is a lower bound.
- The headline judge for each target is from **another family**: GPT-5.1 for Claude, Haiku for GPT, either for Qwen.
- Held-out targets and J2 run in final mode only (PLAN I7), so nothing tunes against them.
- The dev target is billed per H100 GPU-second (about $3.95/h) and scales to zero after 15 idle minutes.
