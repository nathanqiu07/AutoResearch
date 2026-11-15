# Independent review of pilot conditioning audit 019

Reviewer role: `/root/parallel_gap_audit`. Read-only review, 2026-11-15.

**No blocking correctness or sanitization finding for the current pinned artifacts and disjoint relocation roots.** This review inspected the public reader, three sanitized runs, and the preservation receipt. It did not rerun the dataset/model workflow, open the private replay files/archive, or inspect environment files or private labels.

Verified by metadata comparison:

- `run-01`, `run-02-relocated`, and `run-03-final` have identical `summary`, `profiles`, all 32 `recorded_requests`, and eight `matched_decisions` records.
- The final run's script hash matches the current `reproduce.py`; the original and first relocated runs each match their preserved `reproducer-used.py`. The final and first relocated input inventories are identical.
- All 89 original input hashes are present in audit 018's approved 252-file input inventory. Mapping the relocated paths back to the recorded coordinator root yields the exact same 89 path/hash pairs.
- Both sanitized reports exclude raw content, prompt, response, context, options, personalization, and environment-file fields. The code explicitly constructs its exports from identifiers, hashes, structural counts and flags, rather than serializing original artifacts.
- Both records retain 20 passages across distinct profiles, eight crossing a permitted-span boundary, 16 characters outside the span union, and zero nonwhitespace characters outside it. This is a structural observation; it does not establish permission for arbitrary restricted-span inputs.

The request comparison reconstructs the profile payload from the pinned consumer, compares the full prompt and settings including the system text, checks trace membership in the result's hashes, matches rendered/payload/cache hashes, and compares the same context/options hash across four controls. The no-profile check establishes empty personalization; the name-only check establishes the exact **configured** name content. The report appropriately limits these to recorded application requests, not authenticated provider traffic or efficacy.

The relocation function derives a relative path from the recorded root or current data root, resolves it under the current data root, and requires the resolved path to remain there. The reviewed run uses disjoint roots and has the same prepared-file hash and input bytes as the original run. The companion 018 audit supplies the completion-index/result/lease chain; 019 should continue to be presented with that metadata provenance rather than as an independent authenticity mechanism.

Two nonblocking documentation points:

1. The original reports said original artifact paths must remain available. This was corrected during review to allow a verified private archive with recorded-root remapping. A direct diff verifies the final limit string was the only reader change; `run-03-final` records the current script and unchanged substantive outputs. The temporary old-report/current-script mismatch is retained in `independent-review.json` as a concurrent review artifact, not a runtime failure.
2. `643f92df856165bd6378fbfc7c292b170d505ba3ace6e64d349368b8ee16a806` is the **archive** SHA256 recorded in the receipt. The receipt file `private-preservation.json` itself hashes to `030a16073c7fdaff999cb27d4e0783ca276b0c58fb365a579bdae2ac8f46745a`. The review did not independently reopen/re-hash the archive; that verification remains the coordinator's recorded operation.

Packaging boundary: `private-replay/` contains actual approved inputs and outputs and is excluded from this review and all public audit copies. Copy only an explicit public-file allowlist. This review and its JSON record are public metadata-only additions; no recursive staging-tree copy is justified.

Evidence: `independent-review-final.json` records the final reviewed public-file hashes and independently computed comparison booleans. `independent-review.json` preserves the interim concurrent-edit mismatch. This is a static review and saved-output comparison, not a second execution of the conditioning reader.
