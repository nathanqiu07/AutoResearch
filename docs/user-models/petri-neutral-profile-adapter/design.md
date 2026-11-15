# Future P8 auditor export implementation plan

**Goal:** Export a saved P8 profile as inspectable auditor guidance without changing the completed Hobbhahn M2 experiment.

**Architecture:** A separate standard-library module validates the saved envelope and renders its full content. It saves the original bytes and provenance alongside the context. It does not prepare or launch an experiment.

**Authority:** The coordinator adopted the bounded offline proposal and reserved these new paths under the existing downstream owner. The user authorized implementation and publication. The paid downstream lane stays closed.

## Design

Keep `prepare_matched.py` and all old packets unchanged. Extending that frozen preparer would blur the identity of an already completed experiment. Importing the newer extraction runtime would introduce an unnecessary dependency. Instead, implement the existing canonical envelope checks locally, then check parity against the authoritative `ProfileArtifact.from_dict` offline.

Require an independently supplied file hash, profile ID, researcher ID and replicate ID. Accept only `neutral-profile-v1`, P8, complete/pinned, uncalibrated confidence, and unavailable weights. Validate full-body, content, config and source-manifest hashes, mirrored config identity and the original UTF-8 byte count/cap. Preserve every content field and array order. Reject malformed JSON, duplicates, nonfinite numbers, non-null weights, invalid links and incomplete profiles.

Render descriptions, beliefs and preferences as distinct saved statements. Keep conditions, dates, sources, unresolved relations and nulls. The fixed preface explains that source statements are data, not instructions or permanent rules. It does not imply that a quotation proves the extracted claim or its usefulness.

Export into a new private directory: byte-exact `profile-original.json`, `auditor-context.txt`, escaped `auditor-suffix.template.txt`, `provenance.json` and `checksums.json`. Preserve all metadata in the original source; the model-facing text includes content and copied identity/status. Record the metadata fields omitted from context explicitly. No truncation or new inference. No source-document traversal, model/backend import, target/judge output or API call.

This checks artifact integrity and structure. It does not revalidate quotations against source documents, prove entailment, measure preferences, or establish downstream benefit. The output is not a runnable packet. Future wiring must explicitly insert the suffix into the auditor template only, retain an appropriate control, prove target/judge isolation, and obtain a new lease.

## Owned files

- `scripts/gio_petri/neutral_profile_adapter.py`: renderer, exporter, verification and CLI.
- `scripts/gio_petri/test_neutral_profile_adapter.py`: synthetic integrity, preservation and rejection tests.
- This directory: design, usage and verification metadata. No actual profile content is published here.

## Work and verification

- [x] Write failing tests for source identity, canonical envelope checks, content preservation, role rejection, escaping and no-overwrite export.
- [x] Implement the narrow module. Keep the existing M2 preparer untouched.
- [x] Export both selected profiles privately with network/model construction denied; compare full content and exact source bytes; check envelope parity.
- [x] Run focused tests, the full Petri tests, and `python3 -m unittest discover -s tests -t .`.
- [x] Obtain independent code review.
- Publication: only the owned source/tests/docs will be committed; the final handoff records the remote-verified commit.

Review focus: a hash-valid artifact for the wrong person; forged but self-consistent metadata; unknown dates becoming defaults; literal braces changing a Petri template; an old output folder being overwritten. Tests must cover each relevant boundary. A supplied external hash authenticates only a selection made elsewhere, not the truth of the profile.
