# Working on this repo as an agent

Several coding agents (Claude Code, Codex, ...) work on this repo at once.
Read this whole file before your first change. It is the shared contract.

## 1. What this project is

An automated research system. It runs a research loop to design synthetic environments in
which a model can't tell it is being evaluated, while the environment still tests the
behaviour it targets (score = (1 − P(eval)) × validity; invalid = 0). The loop is
steered by a selectable researcher's taste, corrected by historical memory, and kept on
task by a drift monitor. Results must be reported honestly, including negative ones.
See `README.md` for the full design and results.

Two kinds of "agent" exist here. Don't mix them up:
* **Runtime agents**: proposer, experimenter, scout, critic and distiller inside the research
  loop. They talk through `autoresearch/integrations/shared_memory.py` (past.dev).
* **Coding agents** (you): you talk through `.agents/` and `scripts/agentctl.py`, described below.

## 2. Code map

| Path | What | Notes |
|---|---|---|
| `autoresearch/llm.py` | LLM backends (offline, anthropic, claude-cli) + `Budget` | Backends must stay isolated. claude-cli runs with no tools or settings. |
| `autoresearch/tasks/` | Benchmarks: `base.py` harness, `eval_awareness.py` (primary), `stretch.py` | A new task subclasses `EnvironmentDesignTask` and must define `invariants` |
| `autoresearch/taste/` | Taste from text, non-research text, and choices; scraping; researchers | Researchers live in `data/researchers/<slug>/` |
| `autoresearch/memory.py` | Persistent experiments, assumption credences, insights, decisions | Exact numbers only |
| `autoresearch/drift.py` | Drift gates and re-anchoring | |
| `autoresearch/loop.py` | The research loop and runtime multi-agent wiring | Hot file. Lock it before editing. |
| `autoresearch/research/` | **v2 open-ended loop**: `measure.py` (generator/target/judge, 3 awareness signals), `ideas.py` (free-form interventions, taste-steered proposer), `loop.py` (accept/confirm, beliefs, taste calibration, report), `stats.py`, `corpus.py` | The loop for real findings. v1 `loop.py` is the ablation testbed |
| `autoresearch/integrations/` | Exa scout, past.dev/local shared memory, HTTP | |
| `autoresearch/benchmark.py`, `swarm.py`, `modal_app.py` | Ablations, parallel swarms, Modal | |
| `results/` | Committed results. Each live run dir has a `CODE_VERSION` | Never edit by hand |
| `runs/` | Scratch output (gitignored) | |

## 3. Commands

```bash
python3 -m unittest discover -s tests -t .      # must pass before every push
python3 -m autoresearch --llm offline run --iterations 6 --researcher demo_realist
python3 -m autoresearch --llm offline benchmark --researcher demo_contrarian --seeds 0 1 2
python3 -m autoresearch --llm offline research --researcher demo_realist      # v2 dry run
```

Python 3.9+, standard library only in `autoresearch/` (Modal is optional, in `modal_app.py`).

## 4. Coordination protocol (`scripts/agentctl.py`)

All coordination state is plain files in `.agents/`, synced by git. Message, claim and
lock files have unique names, so agents don't create merge conflicts with each other.

**Start of session**
```bash
python3 scripts/agentctl.py register <your-name> --role "<what you work on>"
python3 scripts/agentctl.py status        # pulls, then shows open tasks, claims, locks, unread
python3 scripts/agentctl.py inbox         # read messages addressed to you or to all
```

**Pick up work.** Claim one task, then lock the paths you will edit:
```bash
python3 scripts/agentctl.py task list --status open
python3 scripts/agentctl.py claim <slug>
python3 scripts/agentctl.py lock autoresearch/loop.py --reason "<slug>: add X"
```
A claim or lock is committed and pushed right away, and the first push wins. If you lose the
race, the tool says so: pick something else. Don't edit a path inside another agent's
fresh lock (checked by path prefix). Claims and locks go stale after 2 hours without
`heartbeat`, and then anyone may take them over. Run `heartbeat` during long work.

**Communicate**
```bash
python3 scripts/agentctl.py post "subject" "body" --to <agent|all> --task <slug>
```
Post when you:
- change an interface others call (function signature, CLI flag, fact format, file layout);
- find a bug in someone else's area (don't fix it inside their lock; message them);
- start or finish a long or costly run (live model calls cost the user's plan usage);
- hand off unfinished work (what's done, what's left, how to verify).

**Finish**
```bash
python3 scripts/agentctl.py unlock <paths>
python3 scripts/agentctl.py done <slug> --summary "what changed, how verified, results path"
```
New work you discover goes on the board (`task add`) rather than into your current diff.

## 5. Rules

1. **Sync before work, commit small, push often.** Run `git pull --rebase` before you start and
   before you push. Make one logical change per commit, with tests passing.
2. **Never touch secrets.** Keys come only from env vars (`ANTHROPIC_API_KEY`, `EXA_API_KEY`,
   `PAST_API_KEY`, Modal secrets). Don't read them, print them, commit them or ask for them.
   Write the code that uses them and let the user supply them.
3. **Never kill processes or delete others' files** without the user's permission. Check
   `status` and the inbox for running jobs first.
4. **Don't edit `autoresearch/` while a live run is in progress.** Each new seed runs in a fresh
   Python process and picks up the code on disk, which mixes code versions in one
   experiment. Whoever starts a live run locks `autoresearch` with the reason
   "live run", writes `CODE_VERSION` (commit hash) into its results dir, and unlocks when it ends.
5. **Costly runs need the user's approval.** Anything that calls real models or paid APIs
   beyond a smoke test needs the user's OK first. Post that you're starting it.
6. **Report results honestly.** Record seeds, sample counts and code version. Report
   failures and negative results. Never present offline-simulator numbers as real-model
   numbers.
7. **No machine-specific paths** in code. Everything must stay portable.
8. **Stay in scope.** Fix only what your task covers. Anything else goes on the board as a task.
9. **Commit messages** end with the attribution line your harness gives you.

## 6. Extension points

- **New benchmark:** subclass `EnvironmentDesignTask` in `autoresearch/tasks/`, register it in
  `tasks/__init__.py`, give it `invariants` and `target_score`, and add a test.
- **New taste source:** produce a `TasteProfile` over `taste.profile.FEATURES` and add it to
  `Researcher.ablation_report`, so its prediction accuracy is measured.
- **New runtime agent:** give it its own identity string, write facts with
  `format_fact(KIND, ...)`, and read *other* agents' facts with `SharedMemory.facts`.
  Document it in the README's past.dev table.
