# CLAUDE.md

Read and follow `AGENTS.md`. It is the shared contract for every agent on this repo
(code map, commands, coordination via `scripts/agentctl.py`, and rules).

Quick start for each session:
```bash
python3 scripts/agentctl.py register <name> --role "<focus>"   # first time only
python3 scripts/agentctl.py status && python3 scripts/agentctl.py inbox
```

## Team rules

- **Commit and push frequently.** After each working unit of change: pull with rebase, run
  `python3 -m unittest discover -s tests -t .`, then commit and push. Small, frequent pushes
  keep the five workstreams from drifting apart. Stage files by name; never push failing tests.
- **Only work within your specified track.** Each session works only on its assigned
  workstream (A–E in PLAN.md §12) and that workstream's board tasks. Anything outside it goes
  on the board with `agentctl task add`, or to its owner with `agentctl post`. Don't edit it yourself.
