# Sponsor features: live-run runbook

Every sponsor feature is built and tested offline. Its board task is done
only after the live steps below have run. Each step needs keys that only the
user supplies, and AGENTS.md rules 4 and 5 apply: get the user's approval for
anything paid, announce it with `agentctl post`, lock `autoresearch` with the
reason "live run", and commit the results with their `CODE_VERSION`.

Load your own keys into the shell first. Scripts never print them.

```bash
set -a; source .env; set +a      # EXA_API_KEY, PAST_API_KEY, ANTHROPIC_API_KEY (+ optional GITHUB_TOKEN)
modal setup                      # only for the Modal steps
```

The steps are ordered from cheapest to most expensive. Costs are estimates
until each step has run once.

## Tier 0: Exa and past.dev only (cents, no model calls)

**past.dev recall rate** (board task `pastdev-live-smoke`):

```bash
python3 scripts/pastdev_smoke.py --n 20 --wait 10 --out results/pastdev_smoke
```

**Real repos for the sandbox** (idea 1). This uses about one Exa search per
topic and two unauthenticated GitHub calls per candidate. GitHub allows 60
unauthenticated calls an hour; set `GITHUB_TOKEN` for more.

```bash
python3 -m autoresearch.research.real_repos find --topic "ML team evaluation scripts repository" \
    --n 5 --out results/real_repos/repos.jsonl --cache-dir runs/exa_cache
```

**Distance to the nearest real document** (idea 5). Without `--confirm`, the
command only prints the planned Exa calls.

```bash
python3 -m autoresearch.research.realism_nn run <environments.jsonl> --out results/realism_nn/nn.jsonl \
    --cache-dir runs/exa_cache            # dry run: prints the plan
python3 -m autoresearch.research.realism_nn run <environments.jsonl> --out results/realism_nn/nn.jsonl \
    --cache-dir runs/exa_cache --confirm
```

**Benchmark contamination** (idea 6). The 24 Petri seeds plan about 43
searches. Pass the target model's training cutoff as `--end-date`, or the
benchmark's own hosting pages will mark every item as exact.

```bash
python3 -m autoresearch.research.contamination run data/petri/seeds_v2.jsonl --format petri \
    --out results/contamination/petri.jsonl --end-date <TARGET_TRAINING_CUTOFF> --cache-dir runs/exa_cache --confirm
```

**Already verified live (2026-11-15, no key needed):**
* `real_repos.github_fetch` against the public GitHub API worked.
* The harness's `repo_setup_commands` cloned `octocat/Hello-World` from github.com at depth 5 into a local directory.
* The scrub left no remote, local branches, and an empty reflog.

What still needs checking is the same clone inside a Modal Sandbox (Tier 1).

## Tier 1: Modal with free mock models (Modal CPU minutes only)

**Clone a real repo inside a real Modal Sandbox** (idea 1, the infrastructure
half of the `real-repo-sandboxes` smoke test). `--mock` uses Inspect's mockllm
for every role, so the run makes no model calls. The sandbox and the clone
are real.

```bash
python3 -m autoresearch.research.real_repos attach --seeds <(head -1 data/petri/seeds_v2.jsonl) \
    --repos results/real_repos/repos.jsonl --out runs/real_repo_smoke/seeds.jsonl
../.petri-env/bin/python harness/petri/run_audits.py --seeds runs/real_repo_smoke/seeds.jsonl \
    --out runs/real_repo_smoke/results.jsonl --tools sandbox --mock
```

**Counterfactual snapshot replay on Modal** (idea 4). This takes cases from
the mock audit's `.eval` log, then replays them on a mock target, with real
Modal snapshots. Commands: `harness/README.md`, the "counterfactual cue
replays" section.

## Tier 2: paid model runs (each needs explicit approval)

| Step | Idea | Board task | Estimate |
|---|---|---|---|
| One Petri seed on a real repo, real models | 1 | `real-repo-sandboxes` | a few dollars plus Modal |
| Real-distractor pairs: `band` on a dev researcher, then `--researcher data/researchers/marius_hobbhahn --cutoff 2025-04-01` | 7 | (none) | under $5 (rewriter LLM) |
| Realism ladder: finalise `results/prereg/realism_ladder.json`, then `python3 -m autoresearch.research.ladder run --paid ...` | 2 | `realism-ladder` | about $90 plus Modal (unconfirmed) |
| Probing metric: score the ladder's sandbox transcripts, then about 120 hand labels via `probing label` / `probing agree` | 3 | `env-probing-metric` | free after the ladder |
| A v1 run with Exa and shared memory, then `python3 -m autoresearch.integrations.trail RUN_DIR` | 9 | (none) | a v1 run's normal cost |
| GPU bids: `--allocation market --gpu-budget-s N --target-llm openai-compat` on the Modal vLLM target, then `market audit` | 10 | (none) | GPU time at `OPENAI_COMPAT_USD_PER_HOUR` |
