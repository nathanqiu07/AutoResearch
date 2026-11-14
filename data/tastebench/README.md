# Taste-Bench data

[Taste-Bench](https://github.com/wbopan/tastebench) (Pan et al. 2026, arXiv 2609.25804) asks
which of two candidate next steps is better at a real decision fork, labelled by how the rest
of the run went. We use its research subset: 112 forks from METR's RE-Bench and HCAST runs
(64 detour, 48 parallel). The engineering subset (390 SWE-bench forks) is optional.

The dataset `wenbopan/taste-bench` (revision v1.0, CC BY 4.0) is gated. Request access on its
[Hugging Face page](https://huggingface.co/datasets/wenbopan/taste-bench) with your own account.
This folder is gitignored apart from this file, so the rows never reach the repo.

The scorer, `python3 -m autoresearch.taste.tastebench`, reads one JSON object per line, with
the release's 14 columns, from `research.jsonl` (and optionally `engineering.jsonl`). The
download-and-convert step is not written yet: the release ships parquet, which needs pyarrow,
and it will be added once downloading is approved.
