# CLAUDE.md

Read and follow `AGENTS.md`. It is the shared contract for every agent on this repo
(code map, commands, coordination via `scripts/agentctl.py`, and rules).

Quick start for each session:
```bash
python3 scripts/agentctl.py register <name> --role "<focus>"   # first time only
python3 scripts/agentctl.py status && python3 scripts/agentctl.py inbox
```
