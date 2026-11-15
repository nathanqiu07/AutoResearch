The pinned 039 inventory has 337 logical inputs. The existing owner archive
manifest matches 234 of them by exact path, SHA256 and size, using 210 distinct
physical files. Twenty-four executed runner-source inputs reuse bytes already
retained as publication `runner_source` members. No path/hash conflicts or
hash-only alternative matches were found. The archive's three native `.eval`
members are not required.

The remaining inputs are 90 public runtime-source files (1,265,625 bytes) and
13 publication/review records (244,752 bytes). The latter may contain original
quote/trace content and must remain private. Initial matching used only the
pinned inventory and archive metadata, without reading retained payloads.

Root has now authorized these narrow additions:

1. Hash and size-check only the 210 named retained payload files, before and
   after use. Read no native `.eval`, unindexed sibling or active runtime.
2. Preserve exactly the 90 missing executed-source byte objects in a public
   code-only archive. Preserve exactly the 13 missing publication/review records
   in a new 0600 private archive under the existing ignored 0700 private root.
   Retain exact inventories/receipts; do not duplicate the full owner archive.
3. Add `reproduce_recovered.py` separately. Keep the original checker body and
   assertions unchanged; replace only its Git-object input adapter and invocation
   metadata with an explicit hash-pinned mapping from recorded `(commit,path)`
   identities to approved recovered byte files. Check paths, byte hashes and sizes
   at access and after completion. No fallback to Git or original temporary paths.
4. Run synthetic rejection controls for wrong hashes, missing inputs and unsafe
   paths. Send exact variant and input-map pins before a full recovered replay.
   Compare all substantive original report fields, retaining only explicitly
   explained invocation/reader-adapter metadata differences. The logical inventory
   should retain the same 337 recorded identities and byte hashes.

Frozen audit039 reader, reports, manifest and the independent original review
inputs remain unchanged. This is exact-byte recovery, not reconstructed Git
history, authenticated provider execution, an installed environment or a full
repository. The third-party normalizer source remains unverified.
