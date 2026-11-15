Audit 026 independently verifies the released phase-2 embedding handoff: 456 checks pass, zero fail, exit 0. All 28 bundles match their pinned producer-response slices, and all 84 cap-specific content hashes reproduce. No discrepancy was found within these bindings and content-construction checks. This is not evidence of prediction quality, personalization benefit, provider authenticity, or authority to run jobs.

The immutable release is `cc4086f3f40f98118be0ed91e0443d62c14c0830`. Its index matches `50c60bd7770e1a28b2a1c1d1725ddb092e2a81a3271809eef799841332c27e9a`; construction check matches `69af332b9b859050551439d6991bb054ec491871845d4c39bf54d1eda6b2078d`; handoff 011 matches `9767b5571c127c60b4075916d7a2076f1ad3b37061d759006591d11490566975`. The retrieval helper is byte-identical to frozen runtime `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca` and matches the proposal/index implementation hash. The assembler bytes match both the release and the index's earlier code label, so the different commit labels do not create an assembler-byte mismatch.

The reader imports no project code. It independently reconstructs the canonical ordered decision query and the exact permitted source chunks, including the fixed character grid, individual-span boundaries, overlap partitioning, whitespace offsets and duplicate handling. It verifies source/release/item hashes, exact label-free decision fields, request ordering/deduplication, response-index roles, and the permission hash. Every entire bundle equals a reconstruction from its raw indexed vectors and usage references. Indices are integers; all 1,536-dimensional vectors are finite and nonzero. Raw source/query text and vectors stay in memory and are not exported.

| Producer batch | Indexed vectors | Queries | Permitted chunks | Reported input tokens | Recorded cost estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| neel_nanda | 20 | 14 | 6 | 1,644 | $0.00003288 |
| chris_olah | 23 | 14 | 9 | 2,278 | $0.00004556 |
| Total | 43 | 28 | 15 | 3,922 | $0.00007844 |

Independent cosine ranking and exact-prefix packing reproduce each reported content hash, passage count and rendered UTF-8 byte count at all three caps. Every one of the 240 selected passage occurrences is an exact source substring wholly inside one individual permitted span. All released documents provide explicit permission ranges; none uses the absent-span whole-document fallback.

| Personalization cap, UTF-8 bytes | Complete reconstructed contents | Rendered byte range | Individually permitted passage occurrences |
| --- | ---: | ---: | ---: |
| 512 | 28 | 511–512 | 30 |
| 2,048 | 28 | 1,940–2,048 | 70 |
| 8,192 | 28 | 4,936–6,692 | 140 |

The construction rows' source, decision, bundle, receipt, method implementation and renderer implementation bindings also match. The renderer hash explicitly combines `consumer.py` and `contracts.py`. Full `profile_id`, `config_id`, `prompt_sha256`, and `selected_spans_sha256` remain recorded-only. The pinned index, handoff 011, and construction check name no construction script, complete configuration, or extractor recipe from which those extra IDs can be independently rebuilt. No recipe was guessed. This limit does not affect the independent content hashes, exact passage membership, caps, or bundle/vector reconstruction above.

Usage is deduplicated by the two original producer receipts, each referenced by fourteen bundles. Counting each producer once gives 3,922 input tokens and $0.00007844, matching the pinned summary and index. The 84 constructed contents do not introduce a new per-profile charge. Recorded response usage, receipt usage, request/settings hashes, dispatch identity and declared-rate arithmetic agree. No active ledger was opened, so actual debit uniqueness, provider origin, billing, and the unresolved question of actual prediction execution remain outside this audit. The declared price is used only to verify recorded arithmetic.

The producer's construction report records zero model calls, and this audit reproduces all content without making a model call. Its clean/detached runtime fields remain producer metadata; immutable matching code bytes do not authenticate which code a past process loaded. Source approval and any source-quality judgment remain evaluator-owned. No private labels, environment/credential files, active ledger, network endpoint, or live backend was accessed; no other checkout was written.

`run-03/report.json` is the final evidence. It records 456 checks, sanitized bundle/batch metadata, 84 content reconstructions, source hashes, scope and limitations. `invocation-03.json`, stdout/stderr and `run-03/reader-used.py` preserve the exact invocation, explicit child environment, script and exit status. Seventeen synthetic tests pass for private replay boundaries, path/hash rejection, absent-versus-empty permissions, adjacent/overlapping spans, cosine order and UTF-8 cap behavior.

The first reader attempt incorrectly treated the renderer implementation hash as the hash of `consumer.py` alone. Inspection of the explicit source formula showed that it binds both consumer and contracts bytes. `run-01/reader-used.py`, `invocation-01.json` and its logs preserve that failed audit assumption; it was not an owner-artifact failure. `run-02` preserves the first successful reconstruction; `run-03` additionally checks integer response indices and reports explicit permission coverage.

`input-inventory.json` lists exactly 42 immutable Git objects and ten hash-pinned approved external JSON files. It is a preservation inventory, not a raw-data copy. Originals should be archived separately in the audit owner's private workspace using only those listed inputs. Do not copy producer directories, released source text, vectors, responses, or profiles into public results.

Reproduce from the approved originals:

```sh
python3 -I -B read_handoff.py \
  --repo /path/to/repository-containing-pinned-objects \
  --coordinator-root /path/to/approved-coordinator-root \
  --out /path/to/fresh-output
```

For a later verified private archive, the same reader supports relocation without consulting original host paths:

```sh
python3 -I -B read_handoff.py \
  --coordinator-root /recorded/coordinator/root \
  --archive-root /path/to/extracted-private-archive \
  --preservation /path/to/private-preservation.json \
  --out /path/to/fresh-output
```

The preservation receipt must map each inventory entry to a hash-pinned archive member, with `kind`, recorded path, commit/full commit for Git objects, `archive_member`, and `sha256`. Optional recorded-path aliases are explicit. The reader rejects unlisted/duplicate references, unsafe archive members, symlink escapes, and modified bytes. The archive branch has synthetic boundary coverage; a complete relocated replay awaits that private preservation step. Existing output directories are refused.
