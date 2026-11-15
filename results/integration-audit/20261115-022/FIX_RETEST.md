The bounded setup-path blocker is fixed in pinned source `f0ac0eabd525cd6d0b52c345a6357b5454f8b2d3`. The old failure, original reproducer, terminal-record evidence and `findings.md` remain unchanged. This is an offline path/packet retest, not live-run approval or evidence of an experimental effect.

The same twelve path cases now meet their fixed-source expectations. Bare `README.md` / `src/a.py` and `./` variants are accepted at `/home/user/projects/omnicore/...`. Absolute and `~/projects/omnicore/...` positive controls still work and complete native startup with synthetic target responses. Invalid paths, protected files, nontext content and file/directory collisions remain rejected. Workspace files and required state remain unchanged on failure; the new implementation intentionally appends error counters and an error log. The new diagnostic names the offending path and gives accepted project-relative and full-path examples.

The error-stop control uses the actual native Petri `audit_loop`, a 30-turn maximum, and fixed synthetic auditor outputs. The third occurrence of the same setup-error fingerprint raises terminal `SetupAborted`. Exactly three auditor generations occur, with repeat counts `[1, 2, 3]`; a fourth-generation sentinel is never reached. The world is failed but unconfigured/unstarted, with zero target responses/calls. This is a guard for three matching error messages/types, not a guarantee to stop after any three distinct setup errors.

There is one documented path-semantics change beyond the failed bare-path case. Old home-relative `projects/omnicore/README.md` now resolves to `/home/user/projects/omnicore/projects/omnicore/README.md`. The new rule treats every relative configure key as project-relative. Use `README.md` or an absolute/`~/projects/omnicore/...` form for the original location. Target tools retain their separate home-relative rules. The old home-relative control records acceptance and its changed destination; it is not presented as unchanged path equivalence.

Only the reviewed packet 04 was compared. Its checksum-manifest SHA256 is `7f1e55f281025f04ee02b34ce4a448d38b3c8ff4b8c7020fa1b262d536f9763a`. The superseded draft was not read. All 38 packet checks pass, with all settings changes enumerated by path, presence, type and hash:

- Seed JSON/text, profile context/provenance, generic guidance, judging instructions and evaluation probes are byte-identical to packet 03.
- Models, routing, generation settings, retry settings, judging configuration, 30-turn allowance, start time, arm schedule and budget allocations are unchanged.
- All three arm-specific guidance suffixes are identical after removing each packet's common prefix. The new common prefix is exactly the original baseline content plus the fixed-source protocol and explicit scenario-clock block. No raw prompt/profile text is exported.
- Changed settings are `code_version`, `setup_protocol`, and eleven lease/accounting fields. Missing fields remain explicit; no unknown field is silently ignored. Lease metadata changes do not imply issuance. The reviewed packet's lease is not issued.
- Old and fixed worlds initialized at the reviewed start time have identical simulated state, startup text and clock policy. The shutdown interval remains 600 seconds, and no real process shutdown is performed. The repair grounds the auditor's common prompt in that existing clock.

The source archive contains the same 114 selected code paths as audit 020. Four files differ: the setup module, packet preparation module and their two tests. All source hashes were verified. The original 17 safe evidence files match `SAFE_FILES_SHA256.json`; that old-stage manifest is preserved. `SOURCE_F0AC0EA.json` and `archive-f0ac0ea.command.json` pin the new source bytes and archive command. The code archive includes the owner's committed synthetic regression fixture, not private evaluator or source-corpus data.

The fixed reproducer is separate so the original executable evidence remains intact. It excludes only the new error-counter field when testing workspace mutation on rejection. It also records authored destination paths and exercises the new native-loop stop:

```sh
python -I -B reproduce-fixed.py \
  --source-root /path/to/fixed-source \
  --source-manifest /path/to/SOURCE_F0AC0EA.json \
  --expect-project-relative accept \
  --out /path/to/fresh-fixed-output
```

`fixed-source-run-01/report.json` and `fixed-source.invocation.json` record twelve case expectations met, the terminal guard, source hashes, dependency versions and exit 0. No real model calls occurred; the native target forwarding boundary was mocked with invented text, and sockets/DNS were denied.

The packet comparison and clock control are also portable:

```sh
python -I -B compare_reviewed_packet.py \
  --left /path/to/packet03 --right /path/to/packet04-reviewed \
  --old-source /path/to/old-source --new-source /path/to/fixed-source \
  --out /path/to/fresh-comparison
python -I -B clock_control.py \
  --old-source /path/to/old-source --new-source /path/to/fixed-source \
  --packet /path/to/packet04-reviewed --out /path/to/new-clock-report.json
```

Inspect `packet-comparison-01/report.json`, `packet-comparison.invocation.json`, `clock-control.json`, and `clock-control-portable.json`. Packet raw contents and terminal records remain external dependencies. No owner edits, live entrypoint, lease actions, environment/credential-file access, private labels or actual content publication occurred. No statement here attributes the earlier repeated choices to an external model defect.
