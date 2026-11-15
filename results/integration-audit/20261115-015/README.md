# Independent semantic normalization fix retest

The original subnormal-vector ranking defect is **verified fixed** in source `462538b5af30826c5ca895fcbf6a1fc446f0b259`, implementation `b7c49c08ff9aea943f044df73bf8a8f5715f1b44`. Seven retest claims are verified; none failed. All 23 existing retrieval/baseline tests pass. The root reviewer independently reran the retest in `root-confirmation/`: the same seven claims passed, with 216 scale combinations, six signed cases and unchanged source hashes.

This establishes a numerical robustness fix on synthetic inputs. It does not establish that provider-origin vectors triggered the previous defect, that any actual study was affected, or that shared live runner integration is ready.

## Scope and exact pins

The selective read-only archive contains `autoresearch`, `tests`, and only the permitted role05 handoff files 001/002/004 plus `fixture.py` and `README.md`. Handoff003 readiness reports and data were neither archived nor read. `SOURCE_SNAPSHOT.json` records the exact git archive arguments, archive hash and all 146 file hashes. It is the packaged copy of staging's `snapshot/AUDIT_SOURCE.json`; original `findings.md` remains unchanged from staging.

- `004-semantic-fixture.json`: `8f2a601fd05fefdb8d383c0cf11e0afc98dadc54987650deaf1f2542e6cb1203`
- `retrieval.py`: `ea579653c0904612db4d3531e05c95660df659a1f6b89a9dd8fd0b77b45dca06`

Both requested hashes match. The new snapshot, preserved009 probe, and old evidence remained unchanged.

## Old versus fixed behavior

The preserved009 probe was replayed **without modification** against its original source snapshot `0ca54b470947fcf453c577b14f6b12c7e2a267b0` (implementation `8f91bde9c96c109fb43a9cb4ce0e3ca205f126af`). It reproduced exactly the prior failure: the minimum positive subnormal `[5e-324, 5e-324]` normalized to `[1, 1]`, creating a false tie and ranking `fit-a` before the better-aligned `fit-b`.

The new retest reuses those original vector lists, documents and decision. Only bundle request metadata is regenerated for the current retrieval implementation, as required by the input pins. Both the original subnormal case and its normal-scale counterpart now rank `fit-b` before `fit-a`, and their built profiles are complete.

`retrieval.py:160-167` now divides coordinates by their maximum absolute magnitude before computing the norm. This avoids underflow distortion in tiny raw norms and overflow in very large raw norms.

## Additional independent checks

- **216 scaling combinations:** query and each passage independently use minimum subnormal, other subnormal, small normal, ordinary, large, or near-maximum finite magnitudes. Every combination retains the correct ordering.
- **Six signed-vector cases:** opposite and orthogonal directions at the same six magnitude scales retain the expected order.
- **Norms and cosine bounds:** maximum measured unit-norm error is 0 for these cases using `math.hypot`; cosine values range from `-0.9999999999999998` to `1.0`. The declared assertion tolerance is `1e-12`, not exact real-number arithmetic.
- **Large finite vectors:** `[1.7e308, 1.7e308]`, which previously failed because the raw norm overflowed, now normalizes and builds correctly. This is an intentional expansion of safe finite inputs, not a regression of the previous rejection test.
- **Invalid vectors:** zero, infinite, boolean, wrong-dimension and unrepresentably huge integer coordinates remain rejected.
- **Source and cap preservation:** the fixed tiny/normal/large profiles retain exact source spans, remain within their declared caps, and make zero extraction calls.

These direction families are not an exhaustive floating-point proof. Existing tests also pass: `python3 -m unittest tests.test_overnight_retrieval tests.test_overnight_baselines -v` reports 23 passing tests. No full repository suite was rerun.

## Source and policy implications

The retrieval helper hash changes from `977b9e47f09c10d2578d6abf873a85c6ac26ab65eda07563f7ceed7e78829cf0` to the pinned new hash above. All seven baseline method policy hashes change because each includes the retrieval helper hash. Old bundles fail current-code source/query/model/hash validation rather than being silently reranked. Exact old/new policy hashes are retained in `run-fixed/source-and-policy-pins.json`.

For planned live work, this is robustness hardening unless producer evidence shows the affected extreme magnitudes. No evidence in this synthetic retest supports a claim that previous live results need rerunning. Adopting the fixed implementation still requires new policy pins and regenerated bundles/profiles for that implementation; old artifacts should retain their original identities. This retest does not verify shared runner dispatch, live-job authority, actual embedding origin, usage, cost or quality.

## Reproduction and evidence

`retest.py` takes `--source-root`, `--old-evidence`, `--old-probe` and a fresh `--out` directory. It contains no machine-specific path constants and refuses to overwrite results. The old probe is neither edited nor repurposed. Its exact bytes are copied to `preserved-009/probe.py`; its SHA matches both old evidence and current reports.

For a portable retest from the packaged evidence, extract `source.tar` into a fresh source directory and copy `SOURCE_SNAPSHOT.json` into that directory as `AUDIT_SOURCE.json`. Then run `retest.py` with that directory as `--source-root`, this packet's `original-replay` as `--old-evidence`, this packet's `preserved-009/probe.py` as `--old-probe`, and a new output path. Original absolute paths in recorded invocations are provenance, not required locations. Replaying the old defect from source additionally uses the separately pinned source archive from the prior009 packet; it is not silently substituted with the fixed source.

- `original-replay-invocation.json`, `original-replay/`: unmodified009 probe execution and reproduced old defect.
- `retest-invocation.json`, `run-fixed/report.json`: exact new command, stdout/stderr, source hashes, old/new pins, adaptations and explicit verified/failed/unverified claims.
- `root-confirmation/`: root reviewer's independent repeat of the same retest.
- `run-fixed/original-case-old-new.json`: exact original and fixed vector results.
- `run-fixed/scale-grid.json`: all 216 independent-scale and six signed cases, norms and scores.
- `run-fixed/large-finite-norm.json`, `invalid-vector-controls.json`, `profile-preservation.json`: numerical and profile controls.
- `run-fixed/source-and-policy-pins.json`: old/new policy comparison and old-bundle rejection.
- `targeted-tests.json`: complete 23-test output.
- `source.tar`, `SOURCE_SNAPSHOT.json`, `manifest.json`: selective code archive, its source/file pins, and hashes of packaged evidence. The manifest excludes itself and the duplicate extracted `snapshot/` tree; it includes `root-confirmation/`.

No real model call, key, API, actual corpus, label or final record was used. No owner code or model setting was changed.
