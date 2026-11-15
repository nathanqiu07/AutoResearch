# Reference supervisor v2

The successor admits only the 52 never-started jobs remaining after v1 drained.
Its immutable inputs are the original issued 57-lease index, v1 supervisor claim,
and v1 terminal receipt. It preserves all 57 allocations ($39.90) and the older
$5 allocation: $44.90 remains reserved. It never settles or edits a ledger.

V1 could admit a new user before observing that another child had finished with
the second unknown outcome. V2 polls and records all terminal children before
checking admission gates, and repeats that observation before each admission.
Two unknown outcomes stop admissions. Missing terminal evidence or a nonzero
child exit also stops admissions. Running children are allowed to finish.

The script verifies the exact issued index and reference runtime 63a2c21, all
runtime file hashes, Python version, each lease and plan, prior terminal records,
and completion/report hashes. It excludes all previously started jobs. Any claim
or output without reconciled prior terminal evidence blocks preflight. Global
claims and packet launch markers are checked again immediately before launch.
An exclusive admission record precedes each child process; a failed launch is
consumed and requires inspection, never an automatic retry.

The new output root must not exist. Creation of that directory and its exclusive
`SUPERVISOR_CLAIM.json` precede children. At most two children run at once. No
packet starts at or after 16:44 UTC; the unchanged child leases forbid new requests
at or after 17:00 UTC and retain their 900-second and $0.70 limits. The coordinator
must keep other reference launchers stopped to preserve the global two-process
limit. Creating `STOP_ADMISSIONS` in the v2 output root stops new admissions and
drains running children. Do not delete claims to resume this invocation.

The coordinator supplies `OPENAI_API_KEY` and optional org/project values in the
child environment using its existing pinned data-only parser. This script does
not read or print credentials. It launches the unchanged frozen reference wrapper.

Read-only check (does not need credentials and creates no claims):

```sh
python3 reference_supervisor_v2.py --dispatch DISPATCH.json --dispatch-sha256 SHA --check
```

The coordinator may execute the same command without `--check` after inspecting
the exact script and dispatch hashes. This handoff did not execute that command.

Concrete prepared dispatch: `/var/folders/34/ry_tht6x6q30sxjdtvzmzxr80000gn/T/gio-reference-v2-proposal-qjw5gryh/dispatch.json`,
SHA256 `a61412ead30f153ec07d2d13bb70ec2af79c06da5304b72ba448a339fd127f2d`.
Script SHA256 `74127010f1725ca19a08f03090cdd79879093159f75f43372f588d3cc679ffb1`.
Output root: `/private/tmp/gio-profile-20261115-coordinator/reference-expansion57-v2`.
Read-only preflight verified 52 eligible jobs, five excluded known terminal jobs,
and zero carried unknown outcomes.

Offline regressions cover second-unknown observation before admission, a known
completion freeing a slot exactly once, concurrency/deadline/stop-file limits,
missing terminal evidence, a claim appearing after preflight, and reconciliation
of prior terminal/claim identities. Six tests pass. All standalone handoff tests:
31 passed. Repository suite: 711 run, 709 passed and two skipped.
