# Lane01 morning packet contract v1

Uses existing run_matched.run_arm and role factory without edits. New preparer/runner live under scripts/gio_petri/morning_recovery/.
One-arm smoke and matched generic/raw/rich/compact use the same seed, models, settings, fixed clock, shutdown tools and common authoring instructions. Context is appended only to auditor.template. No outcome-based retries.

## Incoming context JSON
Required: schema_version="gio-auditor-context-v1", condition_id (lowercase identifier), method_id, researcher_id (string or null), source_bundle_digest (SHA256 or null only for generic), model_facing_text (nonempty UTF8), provenance (object), settings (object), implementation_commit (nonempty string), checks_performed (list), known_limits (list).
Optional: source_bundle_path, structured_artifact_path, structured_artifact_sha256. Paths local inputs for copying into frozen packet, never read by models. source_bundle_digest pins exact source bundle file bytes. No secret/private archive references.
Do not impersonate P8: method_id is honest producer label. P8 exporter can produce this wrapper from verified saved export. Other controls validated as opaque labeled text; no claim native P8 validation was performed.
No silent truncation. Producer owns source selection/cap. Consumer preserves exact text and structured artifact, tracks byte count/hash. Expected text hash supplied by sender or coordinator on frozen receipt. JSON braces escaped once for native Petri formatting.

## Packet and runner
prepare.py --contexts C1.json [C2.json ...] --out PACKET --start-time ISO --lease PROPOSED.json [--authoring-contract CONTRACT.txt]
run.py --packet PACKET --out RUN [--execute --lease ISSUED.json --credentials-file SECURE.env]
Dry run verifies checksums/seed/models/source dependencies, no calls. Issued lease same run_matched format: status issued, owner_chat=01a1de1f-bcb8-74a3-8076-0a3f9a27340a, lease_id, packet_checksums_sha256, expires_at, provider_allocations_usd. Both positive allocations required by existing budget API. Runtime commit must equal packet code_version. Once-only claim reused.

## Artifact layout
packet/seed.json + seed.txt unchanged; common.template.txt; settings.json; review instructions; per condition CONDITION.template.txt, CONDITION.context.json, CONDITION.context.txt, optional CONDITION.source-bundle.json and CONDITION.profile.json.
RUN/CONDITION matches old run_arm: auditor-template.txt, calls/, world/world-initial.json, world/attempted-target-inputs.jsonl, world-final.json, native-sample.json, audit.json, primary-review*, environment-review*, ledgers, summary.json. Top-level summary.json + provider-ledger.json + runtime source receipt. isolation.json records actual input checks.
Viewer mapping emits gio-recovery-viewer-v1 index. Lane07 evaluation.py and Lane08 viewer.py separately owned, not edited by lane01.

## Decisions/limits
First smoke uses saved Neel P8 export if new source extraction late. Source researcher is Neel, never Gio. Structural smoke does not establish profile benefit. Fixed clock, simulated shutdown and deliberate exposure remain explicit. Existing secondary/primary legacy reviews retained; lane07 new review has separately versioned result. No old result edited.

