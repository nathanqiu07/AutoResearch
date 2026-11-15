# Full-chain local evidence viewer

The viewer shows sources, the exact supplied profile, model-facing auditor context, generated environment files, target trace and state changes. Generic, raw, rich and compact conditions stay side by side, including unrun and failed conditions. It keeps environment validity, taste adherence, target behavior and costs separate.

## Offline fixture

The published [fixture preview](fixture-preview/index.html) contains invented records only. Its banner and every fixture file say so. It is a display check, not a real experiment or scientific result.

```sh
python3 -m unittest tests.test_gio_recovery_viewer
python3 scripts/gio_petri/morning_recovery/viewer.py \
  --index docs/morning-recovery/lane08/fixture/index.json \
  --artifact-root docs/morning-recovery/lane08/fixture \
  --out runs/morning-recovery/viewer-fixture-new
```

Open the new output directory's `index.html`. It works without a server, network or external assets. Reusing an output directory fails rather than replacing evidence.

## New Petri receipts

Lane01's `gio-recovery-viewer-v1` index maps its frozen packet and native `run_arm` output to [INPUT.md](INPUT.md). Use an explicit root containing the referenced files. The viewer reads only those listed files; it does not follow private archive pointers or links found inside them.

| Viewer stage | Native record examples |
|---|---|
| Sources | `packet/CONDITION.source-bundle.json` |
| Profile | `packet/CONDITION.profile.json`, `packet/CONDITION.context.json` |
| Auditor context | `packet/CONDITION.context.txt`, `CONDITION/auditor-template.txt` |
| Environment | `CONDITION/world/world-initial.json` |
| Target trace | `CONDITION/audit.json`, `CONDITION/world/attempted-target-inputs.jsonl` |
| State changes | `CONDITION/world-final.json`, plus an explicit diff if supplied |
| Reviews | Separate lane07 validity/taste/behavior records; original reviews remain attached |
| Costs | Condition audit/review ledgers, with overlap-aware totals supplied by the owner |
| Provenance | `settings.json`, `CODE_VERSION`, `isolation.json`, source/runtime receipts |

An initial/final file is not automatically turned into a finding. The owner must supply review statuses and any descriptive summary. A successfully loaded file does not prove that its contents reached a model; the isolation/delivery receipt covers that claim.

Render actual runs into an ignored or private local directory. Actual output may embed complete source documents and transcripts. This lane publishes the viewer and synthetic fixture only; it does not authorize publication of private experiment contents.

## Verification

The focused tests cover retained missing conditions, exact source content, HTML escaping, changed hashes, missing files, traversal/symlink rejection, no automatic pointer following, fixture labeling, separate review/cost fields, unknown costs, credential-pattern redaction and exclusive output creation. These checks establish viewer behavior, not model quality.

The initial clean repository suite ran 809 tests successfully, with two skipped. The first 12 viewer tests pass. Browser visual inspection and the post-change repository suite are recorded in `STATUS.json` as they complete. No model calls are made by the viewer or its tests.
