# Taste-Bench data

[Taste-Bench](https://github.com/wbopan/tastebench) (Pan et al. 2026, arXiv 2609.25804) shows
an agent's transcript up to a fork and two candidate next steps; the rest of the real run
labels the better one. This project uses it for experiment E7 (PLAN.md §9): does the loop's
decider pick the better step, and does adding a researcher's user model help? We use the
research subset, 112 forks from METR's RE-Bench and HCAST runs (64 of the kind the benchmark calls "detour", 48 "parallel"; its paper defines both).
The 390 software-engineering forks are not used.

## Download

The dataset `wenbopan/taste-bench` (revision v1.0, CC BY 4.0) is gated: request access on its
[Hugging Face page](https://huggingface.co/datasets/wenbopan/taste-bench) with your own
account. This folder (`data/tastebench/`) is gitignored apart from this file, so the rows
never reach the repo.

The scorer reads `data/tastebench/research.jsonl`, one JSON object per question with the
release's columns: `id`, `domain`, `method`, `cell`, `source`, `task_id`, `query`,
`prefix_text`, `prefix_text_short`, `prefix_steps`, `choices` (two strings), `answer` ("A" or
"B"), `answer_index` (0 or 1) and `canary`. No download script exists yet, because the
release ships parquet, which needs pyarrow; until one is added, convert the research rows
by hand (pyarrow's `read_table(...).to_pylist()`, one `json.dumps` per row). Ethan approves
the download first.

## Run

Every run costs model calls, so start with `--dry-run` and get Ethan's approval.

```bash
python3 -m autoresearch.taste.tastebench run --decider base --llm anthropic --model <id> --out runs/tastebench/base.jsonl
python3 -m autoresearch.taste.tastebench run --decider advisor --researcher <slug> --base runs/tastebench/base.jsonl --llm anthropic --model <id> --out runs/tastebench/r1.jsonl
python3 -m autoresearch.taste.tastebench score runs/tastebench/r1.jsonl --vs runs/tastebench/base.jsonl
```

Each question is asked with the options in both orders, and counts only if both answers are
right, so guessing scores 0.25. `score` prints that rate overall, per fork type and per
order, plus the difference from the base run with a 90% bootstrap interval.
