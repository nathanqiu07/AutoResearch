# Full-chain morning successor

This lane carries the same source bundle through a saved profile, the Petri auditor, an authored environment, the target and recorded reviews. It does not claim that the profile helps.

The seed remains `v2_seed_48`. The existing Qwen auditor, Nemotron target and GPT-5.1 judge retain their settings. The auditor can use up to 30 turns. The target sees the authoritative shutdown script and schedule before choosing. The clock is fixed and no real shutdown occurs.

The only condition-specific input is extra auditor context. Generic, raw, rich and compact receipts use the same interface. The common authoring instruction asks for neutral code and documentation without prefilled findings. A scoped adapter checks each proposed setup before it reaches the target. Structural failures use the existing correction policy: stop on the third identical error, within the same 30-turn ceiling. Semantic flags never trigger rejection. Every check and rejected attempt is retained alongside the original call ledgers. Old packets, preparers, runtime functions and results remain unchanged.

## Run

Use the existing Petri environment and provider credentials. No new dependencies are needed. Create context receipts as described in [CONTRACT.md](CONTRACT.md). The coordinator supplies the bounded lease; its packet hash is issued after preparation.

```sh
python scripts/gio_petri/morning_recovery/prepare.py \
  --contexts generic.context.json raw.context.json rich.context.json \
  --out runs/morning-packet --start-time 2026-11-15T17:30:00+00:00 \
  --lease proposed-lease.json

# Offline verification only
python scripts/gio_petri/morning_recovery/run.py \
  --packet runs/morning-packet --out runs/morning-comparison

# Same command with execution and a new packet-bound lease
python scripts/gio_petri/morning_recovery/run.py \
  --packet runs/morning-packet --out runs/morning-comparison \
  --execute --lease issued-lease.json
```

For a one-arm smoke, supply only one context receipt. Each arm still runs the full existing audit and review path, including legacy secondary probes. It is not a single API call. All input sources and runtime files must be committed and pinned before execution. Failed attempts remain visible; no automatic reroll occurs. New paid calls stop by 11:45 Pacific on November 15.

The run writes exact input receipts, environment files, target transcripts, review inputs and outputs, provider captures, costs, and `viewer-index.json`. Lane07 owns the additive evaluation; lane08 owns the viewer. Their results must stay distinct from the old primary and secondary scores.

## Checks and limits

Offline tests check exact source preservation, seed and model settings, template escaping, direct auditor-only routing and provider accounting. Actual role captures check whether the complete supplied text appears in auditor requests or leaks to target/judge requests. That lexical check does not prove there is no partial or semantic copying. Missing captures are missing evidence.

The saved Neel P8 smoke is a fallback. Its original source record and all six quote spans were checked against the shared allowed-source bundle. This is a model of Neel based on limited writing, not a model of Gio. No final-test choices are used.
