# Full-chain viewer input v1

The viewer reads only the artifact files explicitly listed in an index. It makes no model calls, does not follow pointers inside artifacts, and does not change source files. A rendered snapshot keeps every declared condition, including errors and missing stages. Generic, raw, rich and compact conditions are always displayed.

Run from the repository root:

```sh
python3 scripts/gio_petri/morning_recovery/viewer.py --index INDEX.json --artifact-root ARTIFACT_ROOT --out NEW_OUTPUT_DIRECTORY
```

The input index uses this structure:

```json
{
  "schema_version": "gio-recovery-viewer-v1",
  "artifact_kind": "recorded_run",
  "run_id": "new-run-id",
  "title": "Morning full-chain comparison",
  "scenario": "Exact scenario name and protocol version",
  "snapshot_status": "partial",
  "limitations": ["One attempt per condition; no reliable effect estimate."],
  "conditions": [{
    "id": "rich",
    "label": "Rich sourced profile",
    "status": "complete",
    "error": null,
    "stages": {
      "sources": [{"path": "sources/bundle.json", "label": "Allowed sources", "sha256": "64 lowercase hex characters"}],
      "profile": [{"path": "profile.json", "label": "Exact structured profile"}],
      "auditor_context": [{"path": "profile/auditor-template.txt"}],
      "environment": [{"path": "profile/world/world-initial.json"}],
      "target_trace": [{"path": "profile/audit.json"}],
      "state_changes": [{"path": "profile/world-final.json"}]
    },
    "reviews": {
      "validity": {"status": "unmeasured", "summary": "Awaiting review", "records": []},
      "taste": {"status": "unmeasured", "records": []},
      "behavior": {"status": "unmeasured", "records": []}
    },
    "costs": {"known_usd": null, "uncertain_usd": null, "reserved_usd": null, "records": []}
  }],
  "provenance": [{"path": "settings.json"}, {"path": "CODE_VERSION"}]
}
```

Use `artifact_kind: "offline_fixture"` for invented test data. This produces an unavoidable fixture banner. `snapshot_status` is `partial` or `terminal`; a partial snapshot never claims that all jobs finished. An index status is owner-supplied, not independently established execution evidence.

Every stage is a list of exact file references. Paths must stay inside the explicit artifact root; symlinks and parent traversal are rejected. `sha256` is optional while owners assemble an index: unpinned files are labeled **Unpinned**, and the bytes actually read are hashed. A hash mismatch is an error and its contents are not displayed. UTF-8 text and JSON are displayed as escaped text. References inside JSON are not opened automatically. Missing, oversized or unreadable files remain visible as errors. No silent truncation.

`costs` values are finite, nonnegative numbers or null. Keep known estimates, uncertain bounds and reservations separate; they are not provider bills. Do not sum duplicate ledgers into each condition. Extra condition IDs (such as retrieved) are allowed. Missing canonical conditions are displayed as not supplied. Review statuses and summaries come from their owners; the viewer does not turn scores into validated claims or invent a combined winner score.

Output is a local self-contained `index.html`, `snapshot.json` with loaded evidence, and a render receipt. Actual-run outputs may contain private data and belong in an ignored/private destination. Only the clearly labeled offline fixture is published with this lane.
