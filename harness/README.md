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
| `petri/run_audits.py` | WS C2 | Petri 2.0 audits: AuditSeed JSONL → AuditResult JSONL (PLAN 12.6), `--tools simulated\|sandbox`, `--mock` for free runs |
| `petri/sandbox_tools.py` | WS C2 | `--tools sandbox`: the target's shell-type tool calls run in a real Modal Sandbox |
| `modal_vllm.py` | WS C2 | Reasoning target on Modal: vLLM with `--reasoning-parser` and tool calling, OpenAI-compatible |

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

## petri/ (WS C2)

The research loop reaches Petri through files only: `PetriMeasurer`
(`autoresearch/research/petri_measure.py`) writes AuditSeed JSONL, runs
`run_audits.py` in its own environment, and reads AuditResult JSONL back. Our C1
judges (A1, A2, validity) score the transcripts; Petri's own judge scores are
kept in `petri_scores` as a cross-check.

```bash
# one-time: a Python 3.10+ environment with Petri 2.0 (pinned copy in eval/vendor) and modal
python3.12 -m venv ../.petri-env && ../.petri-env/bin/pip install eval/vendor/petri-v2.tar.gz modal
export AUTORESEARCH_PETRI_PYTHON=$PWD/../.petri-env/bin/python

$AUTORESEARCH_PETRI_PYTHON -m unittest harness/petri/test_harness.py           # free: scripted mock models
$AUTORESEARCH_PETRI_PYTHON harness/petri/run_audits.py --seeds data/petri/seeds_v2.jsonl --out /tmp/r.jsonl --mock

# paid (needs the user's OK): models from configs/models.json petri.<mode>
$AUTORESEARCH_PETRI_PYTHON harness/petri/run_audits.py --seeds data/petri/seeds_v2.jsonl --out runs/petri/v2_dev.jsonl --mode dev --tools simulated
python3 -m autoresearch research --setting agentic --petri-seeds data/petri/seeds_v2.jsonl --tools sandbox \
  --target openai-compat:Qwen/Qwen3-30B-A3B --judge anthropic:claude-haiku-4-5
```

`data/petri/seeds_v2.jsonl`: the 24 agentic Petri 2.0 seeds chosen in `eval/petri-setup/`
(12 dev, 12 hidden, in each row's `split`). Sandbox mode needs `modal setup`; each audit
sample gets its own sandbox, which times out after an hour.

## modal_vllm.py (WS C2)

See the docstring: `modal deploy harness/modal_vllm.py`, then point `OPENAI_COMPAT_BASE_URL`
at it and run `python3 scripts/c2_smoke_target.py --n 5` (paid) to check that raw reasoning
reaches `Sample.reasoning` and the A1 judge reads it.
