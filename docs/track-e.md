# Track E: completion and replay

The market, bidders, caching, batch backend, research grid, preregistration
runner, plotting, and living-memory helpers were delivered by david-e. The
remaining demo entry point is `python3 scripts/demo.py`. It reads only committed
Git objects, resolves its revision once, and replays four moments in PLAN §10
order: tools, target reasoning, grid, and living user model. Each moment reports
missing evidence explicitly. `--strict` fails when any moment lacks evidence;
`--json` emits an auditable manifest. No live calls occur during replay.

Use `--paths results/research_smoke_d` for the existing four-arm live smoke.
These runs have one seed and three samples per evaluation, no validated
findings, and the documented claude-cli harness confound. They do not establish
an E5 efficiency result. Every replayed run shows its code version, seed,
sample count, baseline and best metrics, validation count, and recorded cost.

Validation commands:

```bash
python3 -m unittest discover -s tests -t .
python3 scripts/demo.py --paths results/research_smoke_d
python3 scripts/pastdev_smoke.py --local --n 20 --wait 0 --out runs/track_e/local_recall
python3 scripts/run_experiment.py E5 --check
```

The last command is expected to refuse the draft E5 plan. Do not bypass that
gate for scientific results. `results/prereg/E5.json` lists the unresolved C1
calibration, benchmark, C2 model configuration, taste-arm decision, and paid-run
approval requirements. Commit the final preregistration before launch. The
runner executes a pinned code snapshot and records a manifest and code version.

## Local verification completed

The three allocation arms each completed seeds 0, 1, and 2, with four iterations
and four samples per evaluation, from pinned code `fa81cc45904a`. All nine cells
succeeded. The fixture is `scripts/fixtures/track_e_offline_smoke.json`; generated
reports, cell manifests, decisions, wallets, an allocation table, and three
charts are in `results/track_e_offline/`. No model calls were made. The reported
simulator validations do not establish real findings or cost savings; cost per
real validated finding remains unmeasured. Each standalone chart labels its
offline data explicitly.

Local shared-memory smoke recovered 20/20 tagged facts. This is a script check,
not a past.dev measurement. A six-fact live smoke refused to start because
`PAST_API_KEY` was unset. The one-cell offline Modal smoke also refused to start:
the installed Modal client reported “Token missing.” Neither failure incurred
model usage. The user directed this continuation to finish local verification
and leave live checks pending; neither live task is marked complete.

Reproduce the offline grid and charts from a clean, committed snapshot:

```bash
python3 -m autoresearch.grid --prereg scripts/fixtures/track_e_offline_smoke.json \
  --llm offline --workers 3 --out runs/track_e_recheck
python3 scripts/plots.py all runs/track_e_recheck --out runs/track_e_recheck
python3 scripts/demo.py --paths results/track_e_offline results/research_smoke_d
```

Charts require `scripts/requirements-plots.txt`. The package itself retains its
standard-library-only requirement. The demo can replay available local grid
evidence, while explicitly leaving the real-tools, raw-reasoning, and living
memory demonstrations missing until their real artifacts are committed.

Still required for the full Track E acceptance criteria:

* One actual Modal research-grid cell, with an execution record. A local dry
  run does not verify Modal deployment. The `modal-swarm-run` board task also
  requests the original shared versus isolated swarm comparison.
* A real past.dev smoke and measured recall rate, using a user-provided key.
  Local JSONL recall verifies the script only.
* A final, committed E5 preregistration and approved model budget, followed by
  the equal-budget arms, held-out evaluation, tables, and charts in `results/`.
* Committed real versus simulated Petri tool runs and target reasoning from C2
  before those two sponsor demo moments can show measured comparisons.

No credentials belong in this document or in result artifacts. All live
experiments retain seeds, sample counts, code versions, and negative results.
