# Phase-2 uncertainty guard source/mock audit 028

Independent reviewer role: `/root/parallel_gap_audit`, 2026-11-15.

**61 synthetic checks verified, zero failures, exit 0** against immutable runtime `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`. The tested runner/API/SQLite path retains full reservations after unknown outcomes, preserves known partial usage, marks the failed job unavailable/uncertain, halts its later item, rejects another backend using the same synthetic ledger without another HTTP request, and rejects reuse of the same job claim. This is source/mock guard assurance, **not diagnosis of the actual phase-2 failure**, proof of its actual reservation, or permission to restart it.

Comparison baseline: audit014's successfully tested `7bb1589127ba386d74dd00c029659f195ffe28b8`, implementation `fd0c81f79a578ac65db945b23884dd5788cf0c05`.

Relevant changes required a replay rather than wholesale evidence reuse:

- `runner.py`, `consumer.py`, `registry.py`, `llm.py`, `usermodel.py`, and package initialization files are byte-identical.
- `backends.py` changed SHA256 from `991bfe9f0bae1b125abac384fef582ef32a10a5aaac8190c89e4cf78bdc2af54` to `6ece37e0a623e8d0a7e3b916925532d1c239a0a82269d98cc2d40fb8563a232d`. It declares 1.25x input-rate estimates, a new pricing/cost-basis identity, and `prompt_cache_options={mode: implicit, ttl: 30m}` in both identity and request. The ledger summary now reports its persisted pricing version. Core `_money`, `_time`, reservation/settlement, and ledger connection/state functions retain identical syntax trees.
- `contracts.py` adds a quote resolver and constant; every previously existing function/class declaration is unchanged. Its file hash changes, so synthetic profiles/configs are freshly built with the correct new renderer pin.
- The conservative 28-module static import closure also finds a newly present `evaluation.py`, referenced only by the runner's confirmation branch, and added quote-resolver tests. These dev-stage guard cases do not enter confirmation or the quote resolver. Static import closure is not a full dynamic call graph.

The seven audit014 scenarios are retained: successful two-decision control; missing usage; input-only usage; output-only usage; valid input with boolean output-token count; incomplete response with complete usage; and transport exception. They use the real `run_job`, API adapter and local SQLite ledger, a wholly synthetic profile/key, socket denial and an in-memory transport. No actual environment dictionary, provider endpoint, active ledger, private label or phase-2 failure artifact was read.

`run-01-original-expectations` preserves the **unmodified** audit014 probe: 50 checks pass and four cost assertions fail, with zero execution-boundary failures. Those failures are expected fixture-policy mismatches: the old probe assumes a sol input rate of 2 while the frozen new source declares 2.5. They are not four production guard defects.

`run-02-phase2` changes only that explicit expected input-rate number and adds seven cache/pricing identity checks, one per scenario. All **61 checks pass**. The exact probe diff is retained. This verifies the emitted settings and configured arithmetic; it does not verify provider acceptance of the cache options, current prices, actual cache behavior or invoice amounts. Fresh-backend calls blocked before reservation remain conservatively marked uncertain by the generic runner; the report separately records zero additional reserved/transport attempts.

All 148 exported source-only Python files match the frozen Git objects and remain unchanged through both replays. The old snapshot's 162 listed files were checked against its saved manifest before comparison. Function/dependency hashes, source diffs, source-only pin manifests, exact probe commands, stdout/stderr and exit statuses are retained. Existing suite tests were not broadly rerun. The current mock interpreter's SQLite version is recorded without claiming it matches the original/live runtime.

An ad hoc inspection initially tried to read the absent old `evaluation.py`; `setup-note.json` preserves that inspection error. The main comparison already represented the old module as absent, and the added-module diff is retained. This was not a guard-case or live-run failure.

Reproduction, with available immutable Git objects and the audit014 source snapshot, uses `compare_sources.py` to create the source-only snapshot, then:

```sh
python3 -I reproduce-audit014-original.py --source-root source --out run-original-new
python3 -I reproduce-phase2.py --source-root source --out run-phase2-new
```

The first command is expected to exit 1 with the four documented old-rate assertions; the second is expected to exit 0 with 61 checks. Output directories must be fresh. The comparator's exact Git source command is in `source-comparison-invocation.json`; both probe runs retain exact child argv/environment and outputs.

Actual terminal metadata has not been released to this audit. Unknown-outcome state, retained amounts, lane stopping, provider error cause and physical request count for the real execution therefore remain unverified here. Any review of that event needs its separately approved frozen records. No real job was restarted or modified.
