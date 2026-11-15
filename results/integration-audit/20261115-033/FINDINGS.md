Audit 033 closes audit027's narrower actual-execution comparison gap for the released memory references. **477 checks pass, zero fail**: all 84 explicit references match 28 recorded completed, ordered P1 predictions in two canonical jobs. The 28 rows comprise 14 decision groups with two option orders each. The references add no independent observations or prediction rows. This audit made zero model calls.

This is recorded-artifact consistency evidence. It does not authenticate provider origin, capture the actual network request, or establish prediction quality. The executed method is P1. `memory_summary` is an explicit mapping to those saved results, not a separate executed memory job, automatic runner cache hit, or promise that a new stochastic call would return the same answer.

The pinned release is `a6c75b0e5b23cbd3ca8c364263f6ba6bfe2a67c2`. Handoff `016-prediction-bindings-ready.json` matches SHA256 `a33ab258ee81e96f5225f98eef3a6bb1e39065f861e5eebe02965e9ff848abef`. Both published output reports match their declared hashes. Runtime semantics come only from six immutable source files at `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`; no project code or owner checker is imported or executed.

| Canonical P1 prediction job | Recorded attempts / complete rows | Recorded conservative API cost, counted once |
| --- | ---: | ---: |
| `8ea5c13ff5ee91ab5a86e4dcf7c029558e26cd9aa678af277835a1c96e4009dc` | 14 / 14 | $0.00141175 |
| `ed907e0a39daf2fd03c72a45ea62597ee91e2220a80d899b503a7ca31ee02d10` | 14 / 14 | $0.00112950 |
| Total | 28 / 28 | **$0.00254125** |

Cost is summed with Decimal once per unique canonical job, not per item, cap, or alias. The result usage and published job usage hashes agree. Both recorded jobs have zero cache hits, uncertain attempts and missing arms. This is the saved conservative cost estimate, not a provider invoice or an independently inspected live ledger.

For each canonical job, the reader independently verifies the prepared packet's byte hash and membership in the pinned prepared batch; semantic job/config/manifest hashes; exact ordered item IDs and option schedule; full released source records and individual content hashes; canonical profile/config/content hashes; parent build packet and terminal result; fixed parent selection; and source/profile/replicate/code identity. Parent profiles remain the original complete, explicit-only P1 profiles at 512 bytes, replicate 0. Their rendered contents fit every requested alias cap, 512/2,048/8,192.

For each of the 28 predictions, it reconstructs the canonical consumer payload, prompt and system from frozen source constants and the pinned profile/item. These equal the actual started trace byte-for-byte. The trace backend/settings and cache key match the prepared manifest. The exact completed sibling trace is selected by the frozen runner's sequence rule, with its byte hash pinned by `result.trace_hashes`; no directory scan is used. Its response hash is verified, and its parsed response equals the saved prediction row. Parsing is a consistency check only: no labels, scores, accuracy, choices, probabilities or rationale text are exported.

All 84 alias proof records point to the correct existing packet, canonical profile, result and started trace, with exact field hashes and three cap references per canonical row. The public owner report is checked against those independently reconstructed bindings, rather than used as evidence that the comparison succeeded. Its memory construction IDs are cross-linked to the earlier pinned public012 metadata. The relevant payload equivalence was independently established in audit027; no new memory builder or alias prediction job runs here, and distinct memory profile IDs are not relabeled as actual executed P1 IDs.

Recorded backend identity is `OpenAIResponsesBackend`, model `gpt-6-luna`, reasoning `medium`, output limit 8,192, and configured timeout 60 seconds. The adapter source identity matches the frozen code's canonical string digest. Caller settings contain temperature `0.0`, but the pinned adapter explicitly records **temperature not sent**. The source constructs a Responses request without a temperature field. No provider temperature value is inferred. The timeout value is configured policy, not a measured network duration. Store false, default service tier, no tools, and implicit 30-minute cache policy agree with the recorded identity and frozen adapter.

The 234 control/hybrid preparations and 112 no-profile/name-only cap aliases are **outside this actual-memory execution audit**. Their public owner report is retained as a hash-pinned snapshot, but its prepared-state claims were not promoted to execution evidence or independently rechecked here. Nothing here asserts that those jobs did or did not execute later.

The final reader run is `run-02/report.json`, with 477 checks and exit 0. `run-01` preserves the first successful 470-check run; final additions explicitly verify parent build config, document content/source-manifest identity, P1 module bytes and adapter fields. Both runs have empty stderr; there were no failed execution attempts. Original audit027 files remain unchanged.

The exact inventory contains 76 named, hash-pinned private JSON inputs and ten public Git objects: four published metadata reports plus six runtime source files. `run-02/input-inventory.json` records every path/hash/size for root-owned private preservation. The reader follows only scoped references needed for the two canonical jobs and their parents. It does not follow environment-file, active ledger, unrelated job, or private label pointers. It rechecks every private input's bytes at completion. Raw inputs remain at their approved locations; this public package contains only metadata, hashes, source code and commands.

Reproduce from approved originals, with explicit path remapping:

```sh
python3 -I -B read_execution.py \
  --evidence-root /path/to/execution-alias-33 \
  --data-root /path/to/relocated-original-data-root \
  --recorded-data-root /recorded/original-data-root \
  --out /path/to/fresh-output
```

Original recorded root is `/private/tmp`. The reader can also use a later verified private archive:

```sh
python3 -I -B read_execution.py \
  --evidence-root /path/to/execution-alias-33 \
  --archive-root /path/to/extracted-private-archive \
  --preservation /path/to/private-preservation.json \
  --out /path/to/fresh-output
```

The preservation receipt must list each private input with `kind: external`, recorded `path`, `sha256`, and a safe relative `archive_member`. Only listed hash-matched members are accepted; traversal or escaping symlinks are rejected. The archive branch is available for root's preservation/replay; this task executed the original-input mode. Output directories must be fresh. Exact argv, minimal child environment, exit status, stdout/stderr and reader snapshots are retained. `SAFE_PACKAGE_MANIFEST.json` lists the safe public files; the private inventory is metadata only.
