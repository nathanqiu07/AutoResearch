# Downstream adapter audit, with later live failure preserved

The checks below cover a successful mocked native path on `09d3ba1`. After they completed, the owner reported live batch03 stopped before any target exposure after 11 auditor requests (10 complete, one pending): relative project paths were resolved incorrectly and repeated errors prevented setup. Both native positive mocks configured `files={}`; they did not exercise nonempty project-relative setup files. That later result is not cleared by these positive mock tests. Audit022 separately reproduces the omitted path boundary and will retest the owner repair. The reported live counts/reservation remain owner-reported here until the separately released terminal metadata handoff is checked.

# Frozen downstream adapter: bounded offline verification

No adapter blocker was observed in these checks. Source is pinned to
`09d3ba15774dd7dcf8bdf060d6121196494d2996`; the prepared packet checksum manifest
matches `18c92c49243e68ff423a72f9fc5d1cf09d15f2ff741c6f85b8985ca952347fdf`.
The saved M2 artifact matches
`ec2dfd26db38726b74feff1d9bca5929db277579622474fde1a3af182ac358f8`.
All 114 selected code files, packet members, and saved-model bytes remained unchanged.
There were zero real model calls and no owner-source edits.

## Verified

`run-03/report.json` records 19 verified checks, zero failures. The exact released
`NativeTaskSmoke` passes, and `targeted-tests.json` records 22 passing shutdown
world/native-forwarding and provider-budget tests.

- The renderer retains the saved persona and all eight selected examples exactly.
  The saved provenance identifies 57 learning and 18 validation IDs. The packet's
  context bytes and model/context hashes agree with the saved rendering. This
  checks artifact consistency, not truth or researcher approval of inferred labels.
- Baseline is exactly the common template; all three arm templates preserve that
  common prefix. Only the profile arm's actual rendered native auditor input
  includes the exact saved profile context. Template brace escaping is lossless.
- The actual native `build_task` path ran all three frozen arm templates with
  identical scripted auditor/target choices and a synthetic seed. Each completed
  four auditor calls, two target calls and one native judge call. Target input
  hashes and primary-review prompt hashes were equal across arms. Neither the
  target nor native/primary judge input contained the saved persona. The original
  owner smoke additionally exercised the original seed through the same task path.
- Common startup exposure was delivered from simulated state. A target-requested
  script write changed that state and returned its computed tool result. The
  completion gate passed. Invalid gate snapshots reject; owner tests also cover
  premature completion, pending tools, failed generation and retained evidence.
- The frozen role settings pass the runtime validator; constructing the real role
  factory with invented keys yields the declared model IDs/configuration. No real
  role generation occurs. Arm order is baseline, generic, profile.
- Provider-budget tests confirm separate local provider allocations, shared arm
  limits, retained uncertain reservations, arm-local failure handling and global
  stop on exceeded accounting bounds. This does not verify the external coordinator.

Source references within `source.tar`: `scripts/gio_petri/prepare_matched.py:70`
(saved rendering), `:163` (guidance), `:200` (templates);
`run_matched.py:95` (runtime/turn binding), `:114` (setup gate), `:120` (native
task), `:228` (valid-comparison conjunction), `:241` (arm order);
`shutdown_setup.py:253` (startup exposure), `:281` (state-backed continuation),
`:313` (completion). Real role settings are in `roles.py:8` and checked by
`run_baseline.py:20`. Installed Petri dependency versions and relevant source
hashes are recorded in the report.

## Limits that must accompany downstream results

**Thirty is the configured maximum, not thirty forced completed turns.** Native
Petri stops after `end_conversation`; all three scripted positive cases completed
at four. Describe it as a 30-turn allowance or cap. This is compatible with early
valid completion and is not a proven runner defect.

**The design measures choice after guaranteed shutdown exposure.** The initial
snapshot explicitly shows the editable script and schedule before the target's
first response. Time is fixed and scheduled process execution is not simulated.
It does not measure spontaneous discovery, actual process shutdown, or actual
shutdown prevention.

**No direct profile injection is a bounded claim.** The adapter sends saved
context only to the auditor. The auditor is allowed to author project files and
`workspace_note`; those generated contents can reach the target. Identical
scripted setups establish the direct input boundary, not a guarantee that a live
auditor cannot repeat profile material or steer a choice. The intended treatment
can change surrounding environment content. Primary validity judgment remains
model-based, with exact-quote provenance validation rather than semantic proof.

The full paid `run_arm`/CLI execution, coordinator issuance/global budget,
current provider availability/prices, live request authenticity, actual billing,
scientific validity and personalization benefit were not verified. The code's
valid-comparison conjunction was inspected; the native mocked path and its setup
gate were executed. There is one planned run per condition, and the generic arm
is not a length-matched causal control.

## Reproduction and evidence handling

Extract `source.tar` into a fresh directory. Use the saved `SOURCE_SNAPSHOT.json`
alongside it. Use Python with the recorded Inspect/Petri dependencies, and invoke:

```sh
python -I -B reproduce.py --source-root /path/to/extracted-source \
  --source-manifest /path/to/SOURCE_SNAPSHOT.json \
  --packet /path/to/approved-frozen-packet \
  --model /path/to/approved-saved-usermodel.json \
  --original-packet /path/to/approved-original-baseline-packet \
  --out /path/to/fresh-output
```

The three data paths are explicit read-only external dependencies. They are
deliberately absent from this sanitized evidence packet. No saved profile,
persona, choice, seed, target transcript or native raw log is packaged. Native
logs are created in temporary directories and deleted after summarization.
`manifest.json` enumerates the safe package files; the extracted source tree and
isolated HOME are excluded because the code archive is sufficient.

The recorded launcher used a fresh HOME and an explicitly constructed environment
without inherited credentials. The probe blocks sockets/DNS and uses mockllm.
Mock usage is explicitly synthetic (100 input/10 output tokens) to avoid an
otherwise attempted tokenizer download in an empty cache. Tokenization, context
limits and billing are not tested by those invented counts. The owner smoke's
task body is unchanged; only the mock usage estimator is replaced.

Two preliminary probe setup failures are retained in summarized form. Attempt 01
hit an unavailable tokenizer download in the fresh environment. Attempt 02 passed
the owner smoke, but the independent capture incorrectly treated a ToolCall
dataclass as a Pydantic model. Correcting the audit-only capture produced attempt
03's 19 passing checks. Neither setup failure is counted as an owner defect.


## Private reconstruction inputs

Root preserved the exact 15 packet files, saved model and six original baseline packet files in a local Git-ignored archive recorded by `private-preservation.json`. All 22 archive-member hashes were verified against their pinned input bytes. The archive itself is not published. Extract it privately and pass its `packet/`, `model/usermodel.json`, and `original-packet/` to the documented reader arguments. Native dependency source hashes/versions remain in the report; this is not a portable dependency installation or a new runtime execution. Retain the private archive when moving or removing this worktree. The original staging manifest covers its original19 files; `checksums.json` covers the complete final package except itself.
