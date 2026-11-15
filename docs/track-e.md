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
