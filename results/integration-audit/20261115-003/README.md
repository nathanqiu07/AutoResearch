# Synthetic directory-loader and identity-guard audit

Nine canonical saved fixtures were checked in each of two pinned sources:
main-derived `0ebcf7b19bacca64c1bd22a2c4383f39edf889d8` and pilot draft
`9616fe8a3c550664d8aae0b72c938d936c0a7347`. Both commands exited 0.

- 18/18 source/fixture combinations preserved saved artifacts and stable fields.
- 18/18 preserved exact request sequences through the team's canonical directory
  loader and adviser compared with direct prediction.
- 54/54 deliberately mismatched backend identities were rejected with zero
  transport calls during the guards.
- Every source/input hash remained unchanged through its audit.

These are synthetic plumbing checks. Recorded fixture advice and artificially
calibrated state are not evidence of preference quality, calibrated reliability,
live backend compatibility, or Petri use. No live calls occurred.

## Fixtures and limits

M0–M7 were created through their actual constructors, populated with explicit
synthetic TasteArtifacts, then saved by the production serializer. No method fit
was run. Every method receives the same canary principle, persona, exemplar and
weights so that channel use is visible. Thus the M0 fixture is intentionally not
a valid no-profile baseline. The M4 fixture additionally marks its weights as
learned to exercise that local branch. M7 calibration state was produced offline
from eight artificial probabilities/labels; its metadata explicitly labels the
state synthetic. The saved JSON files are the authoritative exact input bytes.

Normal M0 fitting clears personal artifacts, but the generic adviser can export
principles from a stale or mislabeled nonempty M0 artifact. The actual pilot M0
in package 001 is empty. No contamination of that run is alleged.

Package 002 preserves the preceding handcrafted-fixture failure. This package
uses the real serializer's default config and does not replace that record.

## Reproduce

From this package directory, replace SOURCE with a checkout at one of the exact
commits above, verify its `autoresearch/` hashes against the observation, and use
a new output path:

```sh
python3 -B tool_snapshot/profile_audit.py --source-root SOURCE \
  --artifact fixtures/m0.json --artifact fixtures/m1.json \
  --artifact fixtures/m2.json --artifact fixtures/m3.json \
  --artifact fixtures/m4.json --artifact fixtures/m5.json \
  --artifact fixtures/m6.json --artifact fixtures/m7.json \
  --artifact fixtures/m7_calibrated.json --out fresh-observation.json
```

`commands.json` records the original invocations, return codes, timestamps and
stdout/stderr. Observations retain exact constructed prompts, artifact hashes,
source hashes and the tool hash. `verification/` retains development RED/GREEN
and full-suite logs plus the independent review record. Those tests concern the
audit tool; they do not validate scientific results from the synthetic replies.
