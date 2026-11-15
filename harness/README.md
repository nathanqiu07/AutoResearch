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

## petri/counterfactual.py (WS C2): counterfactual cue replays

This measures the causal effect of **one** cue. Take a finished sandbox-mode audit and stop it at a
decision point, target turn N (1-based, as `transcript.py` numbers turns). Replay the target from
there under each single-cue mutation, with everything else fixed. Each mutation is compared with the
unmutated control replay, paired by decision point.

1. **Case** (`cases`, needs inspect_ai + petri). From the Inspect log it takes the target's final
   branch, its tool definitions, and the shell commands that built the sandbox up to turn N, in the
   order they ran:
   * the repo clone from the sample's `repo`;
   * the auditor's `sandbox_exec` calls;
   * the target's routed tool calls, including any from rolled-back branches, because the sandbox does
     not roll back.
2. **Base.** In a fresh sandbox, first upload what the repo clone needs, then run those commands
   and snapshot its filesystem (`Sandbox.snapshot_filesystem()` returns an Image). Every branch starts
   from that snapshot, so they all share one clone. A failed upload or clone fails the case. A failed
   audit command is replayed as it happened.
   * A `local_path` repo goes through the audit harness's own path (`sandbox_tools.repo_uploads`):
     it is bundled on the replay host with `git bundle create --all`, uploaded with a sha256 check
     (`ModalSandbox._upload`; `FakeSnapshotSandbox.upload` in tests) and cloned by the case's
     `repo_setup_commands`.
   * The bundle is made at replay time, so the repo must be on the replay host with the commits the
     audit used. Each row's `setup` log records the upload's sha256 and size, and the case's
     `repo.ref` pins the checkout.
3. **Branch.** For each (mutation, replicate):
   * start `Sandbox.create(image=snapshot)`;
   * apply the mutation, a text edit of the target-visible prefix and/or a shell edit of the sandbox
     files;
   * sample the target's next K turns. The target runs alone through Inspect's model API, its
     shell-type calls run in that branch's sandbox (`sandbox_tools.route`), and other calls get a fixed
     "unavailable" error, the same in every branch.
   A branch stops early when the target replies without a tool call, since there is no auditor to
   answer it.
4. **Rows.** One JSONL row per (case, decision turn, mutation, replicate) with the mutated prefix,
   continuation, transcript, the continuation's raw reasoning, and `mutation_record`. The record holds
   the spec, the text changes per message, and each shell command with its exit status and output (the
   changed files with per-rule counts).

```bash
python harness/petri/counterfactual.py mutations                       # the registry
$AUTORESEARCH_PETRI_PYTHON harness/petri/counterfactual.py cases --log runs/petri/logs/X.eval --turns 2,4 --out cases.jsonl
python harness/petri/counterfactual.py replay --cases cases.jsonl --out rows.jsonl --mock   # free: mock target, fake sandbox
# paid + Modal (needs approval):
$AUTORESEARCH_PETRI_PYTHON harness/petri/counterfactual.py replay --cases cases.jsonl --out rows.jsonl \
    --target openai-api/modal/Qwen/Qwen3-30B-A3B --k 3 --replicates 3 --today 2026-11-15
# a target that ran with run_audits.py --target-thinking: replay it the same way
$AUTORESEARCH_PETRI_PYTHON harness/petri/counterfactual.py replay --cases cases.jsonl --out rows.jsonl \
    --target anthropic/claude-sonnet-4-5 --target-thinking [--reasoning-tokens 8000]
# score with C1's judges (A1 = Measurer.verbalized, A2 = Measurer.p_eval) and report per-cue effects
python3 -m autoresearch.research.counterfactual score rows.jsonl --out scored.jsonl   # paid; --offline is free
python3 -m autoresearch.research.counterfactual analyze scored.jsonl --out-dir runs/cf
```

**Mutations.** Each one is deterministic given the case and `--today`, and every row records its
inputs:

| mutation | what changes |
|---|---|
| `realistic_names` | placeholder names become fictional realistic ones (PLAN I18) |
| `lower_stakes` / `raise_stakes` | stakes wording |
| `messy_formatting` | neat markdown in the system prompt and user turns becomes messy plain text |
| `add_fake_git_history` / `remove_git_history` | the working directory's git history |
| `present_dates` | every ISO date shifts so the latest one is today; intervals are kept |

* Text edits and file edits use the same `apply_spec` code: its source is shipped into the sandbox.
* File mtimes are kept.
* Text edits never touch the target's own reasoning blocks (which may be signed), tool-call arguments
  or file names, so earlier commands still point at files that exist.
* Add a mutation by adding a `Mutation` to `MUTATIONS`.

**Target config.** `--target-thinking` (with `--reasoning-tokens`, default 8000) gives the replay target
the same Inspect `GenerateConfig` as `run_audits.py --target-thinking`, from one shared function,
`run_audits.target_thinking_config`. OpenAI models get `reasoning_effort="high"`; other models get a
reasoning-token budget plus 8000 tokens for the reply. Replay a case with the setting its audit used.
Each row records the config in `target_thinking` (null when it is off). As in `run_audits.py`, `--mock`
ignores it.

**`realistic_names` and PLAN I18.** I18 says environments use realistic but fictional entities: no
real private individuals and no impersonation of a real company. The replacement table
(`REALISTIC_NAMES` in `counterfactual.py`) was checked against that rule on 2026-11-15, and the
check found two problems:
* the company, Brightwell, shares its name with real companies;
* its domain, `brightwell-freight.com`, is a registrable public domain, so the generated email
  addresses could belong to, or reach, a real organisation.

Brightwell is also a name that LLM-written environments in `results/` use often. The table now uses:
* a coined company, `Kessrow Freight` (`FICTIONAL_COMPANY`);
* the domain `kessrow-freight.internal`. ICANN reserved `.internal` for private use and will never
  delegate it, so no address or URL in the table can reach a real host. It still looks like a
  company intranet rather than a placeholder such as `example.com`;
* invented first/last-name pairs (`FICTIONAL_PEOPLE`), taken from no scraped or Exa material.

`test_counterfactual.NamesTest` keeps the check running:
* every host in a replacement is under `.internal`;
* no replacement is itself a placeholder: applying the table twice changes nothing;
* no fictional person or company name appears in the repo's real-person data (`data/researchers/`).

Whether a coined name matches some real business somewhere can't be ruled out offline. Re-check
with a web search before any name change is published. `add_fake_git_history` deliberately uses
`Test User <test@example.com>`, a reserved placeholder domain, because it is the less-realistic arm.

**Injectable parts.** Sandboxes: `ModalSnapshotBackend` or `FakeSnapshotBackend`. Targets:
`InspectTarget` (any Inspect model or model id) or `FakeTarget`. Only those two import third-party
packages, lazily.

**Tests:** `harness/petri/test_counterfactual.py`.
* Standard-library tests run on any Python 3.9+.
* The Inspect tests skip without inspect_ai and petri. They run a mockllm target and a real Petri
  mock audit through `cases`.
* `tests/test_counterfactual.py` covers scoring and effects, and runs a free end-to-end replay, score
  and analyze.

**Not supported yet:**
* audits that ran in simulated mode (they replay with no sandbox, every tool call gets the fixed
  error, and file mutations are skipped and recorded as such).
