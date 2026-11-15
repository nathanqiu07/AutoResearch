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

### Auditor-prompt rewrites

Petri's auditor runs on a long fixed system prompt (`data/petri/stock_auditor_prompt.txt`,
with five `{placeholders}`); the seed is pasted into it. Both can be rewritten:

* loop: `research --setting agentic --petri-rewrite seed|auditor|both` (`auditor` writes realism
  guidance once per design and inserts it before the prompt's seed section, so every seed gets
  the same auditor behaviour); `--auditor-prompt FILE` swaps in a fixed custom prompt.
* E3b: `scripts/c2_e3b.py --condition stock=S.jsonl --condition aud=S.jsonl --auditor-prompt aud=FILE`
  compares auditor prompts with the seeds held fixed.
* harness: an AuditSeed row may carry `auditor_prompt`; rows are grouped into one Inspect task per
  (tool mode, auditor prompt). Every custom prompt is checked for the five placeholders and for
  unescaped braces before anything runs.

### Real repos in the sandbox (idea real-repo-sandboxes)

A sandbox the auditor fills by hand tends to look invented (neat trees, placeholder names, no
history). Instead, an AuditSeed row can carry a real repo, which is cloned into that sample's
sandbox before the auditor's first turn:

```json
"repo": {"url": "https://github.com/owner/name", "ref": "<commit or branch>", "depth": 200,
         "licence": "MIT", "source_url": "<the URL Exa returned>", "published": "2025-04-02",
         "path": "/home/user/name", "scrub": true, "remote_url": "git@git.corp.example.com:team/name.git"}
```

Either `url` or `local_path` is required; every other field is optional.

* `local_path` is an absolute path to a git repo on the machine that runs the harness. Use it
  instead of `url`.
* `depth` is 200 commits by default, or `"full"` for the whole history.
* `path` defaults to `/home/user/<name>`.
* `scrub` defaults to true.

A row with `repo` must use `tools: "sandbox"`: `load_seeds` and `validate_audit_seed` reject it
otherwise.

```bash
# paid: Exa search plus GitHub's public API (60 requests an hour; GITHUB_TOKEN is used if set)
python3 -m autoresearch.research.real_repos find --topic "kubernetes deploy scripts" --out runs/repos/k8s.jsonl
# free, no network: a repo on this machine (licence read from a committed LICENSE/COPYING file)
python3 -m autoresearch.research.real_repos local --path /abs/path/to/repo --out runs/repos/local.jsonl
# free, no network: give each seed a repo, chosen by a hash of its seed_id, and set tools=sandbox
python3 -m autoresearch.research.real_repos attach --seeds data/petri/seeds_v2.jsonl \
  --repos runs/repos/k8s.jsonl --out runs/repos/seeds_k8s.jsonl [--seed-ids a,b] [--salt x]
```

**Finding repos**
* `find` keeps repos that are not archived, have a permissive licence (`--licences known`
  accepts any licence GitHub can identify), are under `--max-size-kb`, and have at least
  `--min-commits` commits.
* It pins `ref` to the default branch's newest commit, so every arm and re-run clones the
  same tree.
* Rejected repos are printed with the reasons.
* Each Exa result a repo came from is appended to `<out>.sources.jsonl` with
  `used_for: "repo_sandbox"`.
* `local` pins `ref` to HEAD. It records `licence` as the SPDX id of a committed
  LICENSE/COPYING file, `"NOASSERTION"` if the file isn't recognised, and null if there is no
  such file.

**Cloning**
* A `url` repo is cloned inside the sandbox with `git clone --no-single-branch --depth N`.
* A `local_path` repo is packaged on the host with `git bundle create --all`. Only committed
  history goes in, and the bundle is capped at 200 MB. The bundle is uploaded to
  `/tmp/autoresearch-repo/`, with a sha256 check, using Modal's Sandbox filesystem API
  (`sb.filesystem.copy_from_local`, modal 1.x) or base64 chunks through `exec` on older modal.
  It is then cloned through a mirror in the same way, and the staging directory is removed.
* `ref` is checked out, and fetched first if it is older than the shallow history.
* Every value is shell-quoted. URLs with credentials, queries or option-like refs and remotes
  are refused. git never prompts or uses stored credentials.
* If the clone fails, the sample fails: it does not fall back to an empty sandbox.

**Scrub (default on)**
* The clone is made to look like a working copy, not a fresh clone. HEAD is put on a branch
  (a pinned commit would otherwise be a detached HEAD). Without `remote_url`, every remote
  branch becomes a local branch and `origin` is removed. With `remote_url`, `origin` is
  pointed there instead.
* The reflog (`clone: from ...`) and `FETCH_HEAD` are cleared.
* Not hidden: a depth-limited clone keeps its shallow boundary (`.git/shallow`; `git log` marks
  the oldest commit `grafted`). Fetching the full history is the only fix, so it is done only
  when you ask for `depth: "full"`.
* Depth counts back from every branch tip, so `git log` on HEAD can reach further back than
  `depth` through older branches.
* With `scrub: false`, the clone keeps its `origin`, and for a local repo that `origin` points
  at the deleted staging mirror.

**Prompt and tests**
* The auditor's resources prompt says where the repo is, whether it has a remote, and tells the
  auditor to build the scenario around its real files.
* Seeds in one Inspect task can have different repos, because the repo travels in each
  sample's metadata.
* Tests: `tests/test_real_repos.py`; in `harness/petri/test_harness.py`, `RepoSetupTest`,
  `LocalRepoGitTest` (the real setup commands run with local git in temp dirs) and the repo
  audits (FakeSandbox). None of them use Modal or the network.

