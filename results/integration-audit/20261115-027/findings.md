# Saved P1 / memory reuse: effective conditioning is an alias

The two released saved P1 profiles and their memory-summary reconstructions
produce identical consumer conditioning on all 28 released ordered decisions at
all three caps. **84/84 system, prompt and payload comparisons are equal**, and
their hashes match the owner's independently recorded comparisons. Each profile
uses its own required method/renderer/prompt identities; identities were not
substituted to force equality.

The final run verifies **543 metadata/hash checks with zero failures**. There
are six complete memory profiles, 56 complete hybrids at caps 2048/8192, and
28 explicitly unavailable hybrids at cap 512. There were zero model calls.

Release/handoff commit: `3a39e23220c04c6ccb58f0af3af15b44833fb207`.
Exact integrated runtime: `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`.
The handoff and both owner report hashes match their released pins. All 153
archived code files and six approved input files remained byte-identical.

## What was independently checked

The approved handoff index selects the first predeclared explicit-only P1
cap512/replicate0 profile for each researcher. Their file hashes, profile IDs,
runtime, status, configuration, full-document hashes and source manifests match
the approved development-v2 releases. The 14 ordered items per researcher match
the proposal hashes and contain only the label-free allowed item fields.

The actual frozen `build_profile` and `prepare_payload` code was used. No provider
backend, job execution, ledger or saved prediction was accessed. Memory builds
retain exactly the parent's content, source/document bindings and original
fit-usage metadata. Their construction uses no extractor calls. The new
artifacts were held in memory; only hashes, counts, statuses and identities were
written. Their distinct no-calls extractor identity can give them different
artifact IDs from the owner's constructed artifacts. Their required renderer
identities and all 84 payload hashes independently match the owner evidence.

This establishes effective-conditioning aliases for these saved parents and
items. A memory label or a larger declared cap does not create another treatment
when the exact consumer input is unchanged. It also does not create independent
measurement evidence. No selection based on prediction scores was performed.

## Execution reuse remains conditional

**Actual prediction execution equality is unverified.** The handoff releases no
prediction packets, responses or results. It does not establish that existing
P1 predictions used the same backend/model, effective settings, ordered item
schedule or replicate identity as a proposed memory prediction job.

The renderer does not include execution model or generation settings in its
payload. Counterfactual metadata controls retain identical rendered bytes when
those fields change. Consequently payload equality alone cannot justify reuse.

The actual runner's pure cache-key function includes semantic manifest identity,
prompt and settings. Representative synthetic execution-manifest controls show
that P1/memory method/profile/cap identities have different cache keys despite
equal prompts. Changing model, settings, item identity or order schedule changes
the key too. This was a pure key calculation, not an execution/cache replay. The
runner does not automatically collapse these aliases.

Before any saved-result reuse, the coordinator must establish identical actual
system/prompt, model/backend identity, effective generation settings and exact
item/context/ordered options, with compatible replicate and provenance records.
Any reuse needs an explicit mapping to the original prediction and its cost;
it must not be counted as another provider call, independent replicate or
independent intervention. Equality of conditioning also does not guarantee that
a fresh stochastic model call would return the same response.

Source references within the frozen archive: `baselines.py:64` returns saved
summary content and preserves original fit usage; `consumer.py:28` validates
each profile's identities before rendering; `runner.py:43` constructs cache keys,
`:102` binds profile/item/schedule identity, and `:184` checks actual call
settings. The integrated `control/run_batch.py:248` binds full source records,
researcher and code; `:399` validates prediction items, profile and renderer.

## Hybrids remain distinct

At total caps 2048 and 8192, all 56 hybrids retain the exact parent profile and
add nonempty retrieved passages. Every passage equals its exact approved source
slice and lies within one individual permitted span. Total JSON byte caps and
the separate passage allowance both hold. Their rendered payloads differ from
the parent P1 payloads. Their content hashes, statuses and rendered-byte counts
match the owner's records.

At total cap512, the fixed512 profile allocation leaves no retrieval allowance.
All 28 hybrids are explicitly unavailable with `frozen_profile_exceeds_allocation`.
The parent is neither shrunk nor regenerated, and P1 is not silently substituted
as a successful hybrid. Preserve these unavailable rows in coverage accounting.

Zero new construction calls does not erase the original parent extraction usage
or establish zero profile-production cost. No scoring, researcher fidelity,
benefit, provider authenticity, actual execution reuse or live-cost saving is
claimed by this audit.

## Evidence and reproduction

`run-04/report.json` is final; its input inventory records all six approved
originals by exact path, byte hash and size. Raw profiles, fit-source text and
decision text were read only in memory and are deliberately absent from the
public evidence packet. `owner-reports/` contains only released metadata reports.

Extract `source.tar` into a fresh directory. The reader accepts a metadata input
inventory mapping six logical inputs to paths and expected hashes. A private
copy can replace the paths without changing any required byte hash; embedded
original paths in the handoff are not followed. Use a new output directory:

```sh
python3 -I -B reproduce.py --source-root /path/to/frozen-source \
  --source-manifest SOURCE_SNAPSHOT.json --inputs /path/to/input-inventory.json \
  --owner-reports owner-reports --out /path/to/new-evidence
```

`approved-inputs.json` records the approved original paths. Preserve these exact
six files separately in private storage if reproducibility must outlive their
current locations. `manifest.json` lists public evidence and excludes the
duplicate extracted code tree. No active runtime or original artifact was edited.

The initial run passed 453 checks. Two attempts to add owner hybrid-row matching
used the wrong interpretation of the owner's `item_sha256` field (whole item,
then item/order pair). They failed in the audit harness and are preserved. The
field is a canonical digest of the item ID; the final run uses that definition,
adds 90 owner-identity/content checks, and passes all 543 checks. These were
audit-reader lookup mistakes, not owner/runtime failures.
