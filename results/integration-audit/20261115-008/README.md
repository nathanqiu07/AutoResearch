# Baseline-controls handoff audit

Pinned role 05 release `675f6d23a079c500ea43aaba1016545768f160fa`, implementation
`8a310d50a211d5e77194e77fc06babc0b760816e`. Fixture SHA256:
`ccda86a7866f1aacb4f5e8817a2888a808023e38681c7b53ef722187c8735cee`.

All six complete saved control payloads match those constructed by the actual
loader, renderer and `predict_baseline` path. Semantic retrieval stays explicitly
unavailable with no call in this release. Scripted probabilities are plumbing
responses, not preference measurements.

Verified with synthetic variants:

- No-profile emits empty personalization. Name-only emits only the supplied name.
  Complete requests remain identical when approved source bodies, researcher IDs
  and extra personal metadata vary while the task, settings and explicit name
  are held fixed.
- Lexical/profile retrieval rejects changed context or reversed option order
  before calls through `predict_baseline`.
- Raw, lexical and profile retrieval retain the same approved source set, exact
  source character spans, only the declared passage fields, and the byte cap.
- Frozen summary content is reused exactly, with original fit usage and profile
  identity retained. The source is a synthetic summary substitute, not real P1.
- The imported retrieval-helper hash contributes to each registered policy hash.
  This verifies recorded policy identity, not universal runtime drift detection.

All 18 owner tests pass. An independent reviewer checked the audit script and
retained evidence, found no actionable issue within these claims, and independently
verified all 143 source hashes. No source changed or live call occurred.

## Integration limits

The generic `predict_profile` route accepts a changed retrieval decision. That is
a documented integration requirement: the shared runner must call the adapter or
enforce the same decision binding. This package does not establish that the
integrated runner does so.

Role 05's snapshot predates the common contract fixes. Its profiles must be
regenerated against the integrated pinned renderer. Actual P1 output, approved DEV
corpus, peer controls, live accuracy and scaling are untested. The later semantic
release is a different pinned artifact and does not change this record.

## Reproduce

Create the exact source archive listed in `source/AUDIT_SOURCE.json`, copy that
file to the snapshot root as `AUDIT_SOURCE.json`, and run with a new output path:

```sh
python3 -B reproduce.py --source-root SNAPSHOT --out NEW_OUTPUT
```

`run-01/observations.json` retains complete recorded requests and cases;
`report.json` contains source/fixture/tool hashes and limits. The published fixture
and owning source files are also retained under `source/`. Original invocations,
stdout/stderr, owner-test logs and the independent review are preserved.
