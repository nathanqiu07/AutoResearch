# harness/

Code that needs third-party libraries (Inspect, PyYAML, pyarrow, Modal, vLLM) and therefore
stays outside `autoresearch/`, which is standard library only. Harness code talks to
`autoresearch/` through files (JSON/JSONL), never imports.

Rules:
* Every script fails with a clear message naming the missing package. Run with
  `uv run --no-project --with <pkg> python ...`. Don't install into the system Python.
* Downloaded inputs are untrusted: one directory per source under `data/benchmarks/raw/`,
  run with `python -I`.
* No paid model calls without the user's approval (AGENTS.md rule 5).

| Path | Owner | What |
|---|---|---|
| `evaldetect/export_probes.py` | WS C1 | EvalDetectBench (freeze-lasr/aware_bench) probe questions → `data/benchmarks/evaldetect_probes.json` for `--probe-questions`. Uses public files only, no model calls. Needs `pyyaml`; parquet scores also need `pyarrow` |
| `petri/` | WS C2 | Petri audits (not built yet, PLAN 12.3 item 7) |
| `modal_vllm.py` | WS C2 | Reasoning target on Modal (not built yet, PLAN 12.3 item 5) |

## evaldetect/export_probes.py

```bash
# inputs (public, small): aware_bench probe YAMLs + el7982/aware-bench scores parquet (1.45 MB)
G=https://raw.githubusercontent.com/freeze-lasr/aware_bench/master
mkdir -p data/benchmarks/raw/evaldetect_github data/benchmarks/raw/evaldetect_hf/scores_parquet
curl -sSL -o data/benchmarks/raw/evaldetect_github/probe_questions_eval_mcq.yaml.txt $G/probe_questions/eval_mcq.yaml
curl -sSL -o data/benchmarks/raw/evaldetect_github/probe_questions_eval_mcq_calibration.yaml.txt $G/probe_questions/eval_mcq_calibration.yaml
curl -sSL -o data/benchmarks/raw/evaldetect_hf/scores_parquet/0000.parquet \
  "https://huggingface.co/datasets/el7982/aware-bench/resolve/refs%2Fconvert%2Fparquet/scores/train/0000.parquet"

uv run --no-project --with pyyaml --with pyarrow python -I harness/evaldetect/export_probes.py \
  --scores data/benchmarks/raw/evaldetect_hf/scores_parquet/0000.parquet
```

Without `--scores`, the script exports only the `default` set. To get per-model sets for a judge
upstream didn't run, run their selection with model calls (paid, needs approval):
`uv run run.py --config <config with probe_selection.strategy: exhaustive>` in a checkout of
aware_bench. That writes `probe_selection/selected_pqs.json` and Inspect `.eval` logs. Convert the
measure logs to a CSV with the `measure_logs/scores.csv` columns (as el7982 did) and pass it as
`--scores`. That conversion step isn't written or tested here.
What we adapted from upstream, and why: `data/benchmarks/README.md` and the provenance file.
