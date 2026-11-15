# Offline scaling manifest readiness

Role 09 supplies planning, integrity checks, and descriptive result joins. It does
not choose finalists, infer labels, verify model access, schedule jobs, read data,
load a UserModel, or call any model. The fixture uses invented researcher, method,
model and item IDs, reusing infrastructure's `fixture-v3.json` neutral content.
It is a plumbing check, not a scaling result.

## Interface

`build_manifest(spec, profiles)` validates approved neutral ProfileArtifact dicts
and emits an opaque manifest. Profile text, options, contexts and labels are not
included. Each method supplies exact expected profile `config_hashes` for every
available extractor level. Artifact IDs, content hashes, prompts, implementation
hashes, source hashes, extraction replicates and rendered byte counts are pinned.
Rehashed changed content cannot pass an existing frozen manifest digest. A
self-consistent new artifact still needs external approval as a new design.

`validate_manifest(manifest, expected_manifest_hash=...)` reconstructs every
expected arm/cell, then verifies the coordinator/evaluator's independently retained
digest. Retain that digest outside the editable manifest: reading a new digest
from the same untrusted file does not detect a coherent late rewrite. This is a
cooperative integrity check, not a signature, authorization or final-use lock.

`result_inventory(manifest, results, expected_manifest_hash=...)` accepts unique
cell results and returns every declared arm, including aliases, missing results,
planned absence, execution failures, empty output and unsupported output. Results
are evaluator-produced scores, not raw labels. Items must match frozen IDs,
option-order IDs, context hashes and ordered-option hashes. A complete cell cannot
omit an item or contain a failed item.

`summarize_results(...)` adds absolute available-case means and item-paired gains
against each consumer level's matched raw/retrieval control. It keeps every
unpaired item visible. Costs/calls count once per unique cell. Unknown cost stays
unknown. Fidelity and utility retain separate panel labels. No interval is
invented without the evaluator's independent-group policy; counts, failures,
missingness and item differences remain available for that owner to analyze.

These are new Role 09 functions only; the shared registry, consumer and runner
interfaces were not changed. This module is not an executable job manifest or a
runner adapter. Roles 00/01/04 must map frozen cells to their leased jobs, preserve
the cell IDs, and keep confirmation results in evaluator-only storage. The
existing audit owner remains responsible for actual rendered payloads and
conditioning behavior.

## Matrix and matching

The design is for one researcher and one common cap. The coordinator combines
researchers/caps in its single frozen final manifest; this helper never reserves
final data. The synthetic two-method example has 22 arms and 18 unique cells:

- A: two selected methods plus no-profile and raw/retrieval controls at S/M/L.
  Candidate arms vary both extractor and consumer and are labeled joint scaling.
- B: one explicitly selected neutral profile is held byte-for-byte fixed across
  fresh S/M/L consumers. Learned weights and calibration cannot transfer.
- C: primary method extractor S/L × consumer S/L. Identical A/B cells are aliases,
  so the cross does not duplicate execution or costs.
- D: S/M/L predict a documented archival judgment from fixed raw evidence. The
  manifest pins the independent judgment inventory and answer-withholding receipt,
  without opening either. Candidate profiles and inferred-label tiers are rejected.

All available levels share the same ordered items, option schedules, source set,
context hashes, profile/context caps, renderer and consumer prompt. Any effective
settings difference must have an exact declared deviation and reason. Backend
`enforced_settings` must agree with the declared effective settings. Exact backend
identity stays distinct from model revision evidence and adapter implementation.
Provider-unversioned public IDs must be reported as such; IDs are not known
parameter counts or independently measured capability rankings.

Deduplication hashes full cell semantics (including artifact, extractor, consumer,
settings, configuration, sources, items, code and prompts), excluding only study
membership. S/S and L/L cross arms reuse joint cells only when those semantics
match. Unavailable models keep their arms with reasons. An individual unavailable
profile slot is explicitly declared with an evidence hash and propagates only to
dependent A/B/C arms; other methods and controls at that model stay present.

The `512/2048/8192` profile caps use `utf8-bytes-upper-bound-v1`, not actual tokenizer
counts. The current no-drop rule rejects oversized profiles rather than silently
truncating fields. A future different truncation rule needs a declared schema
change. Swapped/shared-profile arms and interval estimation are not implemented in
this first manifest version; they must be explicitly added and frozen if required,
not relabeled as own-profile arms.

## Live dependencies and limits

The coordinator's declared API panel is `gpt-6-luna`, `gpt-6-sol`, `gpt-6-astra`,
with common Responses medium reasoning only where verified. Exact adapter pins,
effective settings, capability evidence and allocations must come from 00/01/04.
A CLI comparison is a separate panel with its own adapter/settings pins. The
synthetic fixture does not verify any of these live models.

Finalists are not frozen. Required next inputs are FINALISTS_FROZEN, approved
profile artifacts/config pins, model verification evidence, exact evaluation item
and raw-evidence/withholding hashes, and the audit owner's comparison-packet check.
Utility needs the existing downstream owner's frozen task manifest. Core and
scaling arms must enter the same evaluator-owned confirmation reservation.

The campaign API guard is $10 aggregate with $4 reserved for scaling. Those are
coordinator policy limits, not a spend allocation to this module. No live jobs,
API/CLI/embedding calls, researcher corpus access, or final use were assigned or
performed here. Unknown cost is never presented as free live inference.

## Checks

Run `python3 -m unittest tests.test_overnight_scaling_manifest` for focused checks,
and `python3 -m unittest discover -s tests -t .` for the required full suite.
The focused tests cover wrong artifact/config hashes, coherent late rewrites,
item/order/context/settings changes, matching extraction replicates, panel
transport, backend-bound model guards, exact deduplication, planned model/profile
absence, empty/failed/unsupported output and paired gains without duplicate costs.
