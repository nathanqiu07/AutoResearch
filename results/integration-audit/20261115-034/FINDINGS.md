Audit 034 verifies the two named completed sparse control/hybrid batches: **4,572 checks pass, zero fail**. All 234 canonical jobs contain 364 completed prediction rows and 364 recorded attempts. No mismatch was found in the checked packet, source, profile, parent, item/order, backend/settings, trace, result or cost bindings. This audit made zero model calls and computed no scores.

| Batch | Canonical jobs | Completed rows / recorded calls | Recorded conservative cost, counted once |
| --- | ---: | ---: | ---: |
| Matched controls | 178 | 308 | $0.046276 |
| Fixed-P1 hybrids | 56 | 56 | $0.011194 |
| Total | **234** | **364** | **$0.057470** |

The 364 rows evaluate the same **28 ordered items**, each across 13 method/cap conditions. Those items form 14 decision groups with two option orders each. Neither rows across methods/caps nor alias references are independent new judgments.

All **112 sparse no-profile/name-only cap references** match 56 existing rows in four canonical jobs already included above. Their canonical cost is **$0.00463625**, a subset of $0.057470, not an additional charge. Variant profile IDs at 512/8,192 independently reproduce by changing the canonical profile/config cap and recalculating their hashes; the rendered content and consumer input stay identical. Both alias provenance and actual started/completed traces identify the same canonical requests/results. The original alias-provenance file still says prepared references; it is preserved as preparation evidence, while the later terminal traces/results establish execution. The runner did not execute these references as extra calls or automatically collapse their different job/cache identities.

The published release is `bfe6e209358fe1e896beb7d229b9cc30db7957e7`. Handoff `018-execution-and-reuse-ready.json` matches SHA256 `63ff8dc668a16bbba7ca88ced4074cb9be07d7b10c633cd7a9d3f26864244fe2`. Every published report pin matches. Runtime semantics use seven immutable source files at `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`; the reader imports no project code or owner checker. Its byte-identical audit033 helper supplies JSON/hash, explicit-input reading and source-constant parsing only. Audit033 is unchanged.

Each completed job is independently bound to its pinned prepared packet, saved manifest, dispatch receipt, full result, completed parent build result and exact profile file. The reader verifies semantic job/config/profile/content hashes; full source records and individual document hashes; exact item selection/order; source/profile/method/cap/replicate identities; current renderer/builder bytes; and the recorded backend/model/reasoning/settings. Retrieval profiles bind the exact context and ordered options. All emitted passages are exact source substrings contained within individual permitted spans. Semantic profiles retain their input-bound embedding bundle without charging its production again. Hybrid profiles retain the pinned P1 content and original usage, and both the frozen-P1 parent job and hybrid build parent are in their manifest lineage.

For all 364 rows, the reader reconstructs the canonical consumer system, prompt and payload from the source constants and pinned profile/item, then compares actual started traces byte-for-byte. Exact numbered completed traces are read using the frozen runner filename rule and hashes in each terminal result; there is no directory scan. Response hashes and parsed-response/result equality are checked without publishing response text, probabilities, rationale, choices or scores. Result item/source/profile/settings/backend/cache bindings match. Each job has the expected attempts/completions, zero cached rows, zero uncertain attempts and no missing arms. The batch summaries agree with independently counted jobs and rows.

Recorded settings are model `gpt-6-luna`, medium reasoning, output limit 8,192, configured timeout 60 seconds, and generic caller temperature `0.0`. The frozen adapter identity/source records **temperature not sent**; no provider temperature is inferred. These are recorded execution bindings and source semantics, not an authenticated provider-origin record or capture of exact network traffic.

Cost sums use Decimal and unique canonical job IDs. Job receipt/result usage agrees and reproduces both batch totals. This is the saved conservative usage estimate, not an invoice. Parent extraction and embedding production costs are excluded from this prediction-only total and must remain charged at their original producer jobs. Nothing here clears unknown outcomes or reservations elsewhere in the campaign; no active ledger was opened.

The **168 richer-condition candidates remain proposed and unregistered in this pinned release**. Their public proposal explicitly records no accounting change. This audit verifies that distinction only; it does not follow richer source/config inputs, reconstruct richer equivalence, or infer later coordinator adoption or richer execution. They add neither jobs nor cost to the completed sparse result above.

Final evidence is `run-03/report.json`; the explicit inventory is `run-03/input-inventory.json`. It lists **2,609 named, hash-pinned private JSON files** and 12 public Git objects. Many private records are separate preparation copies with the same underlying data hashes. Every read file is rechecked at completion. Root can preserve exactly this inventory in its own private workspace; no raw copies are in this package. Environment-file, SQLite, unrelated jobs and private label pointers are not followed.

Runs 01 and 02 remain preserved. Run 02 adds the repeated-item denominator check; run 03 adds explicit frozen-P1 parent job/file binding for every hybrid. All three runs exit 0 with empty stderr; no failed execution attempt was discarded. Exact argv, minimal child environments, reader snapshots and logs are retained. No owner source or prior audit evidence was edited.

Reproduce from approved originals:

```sh
python3 -I -B read_control_execution.py \
  --evidence-root /path/to/control-execution-34 \
  --data-root /path/to/relocated-original-data-root \
  --recorded-data-root /recorded/original-data-root \
  --out /path/to/fresh-output
```

The original recorded data root is `/private/tmp`. After private preservation, the same reader supports `--archive-root /path/to/extracted-archive --preservation /path/to/receipt.json` instead of the two data-root arguments. The receipt must map each private recorded path/hash to one safe relative archive member with `kind: external`. Unlisted, changed, duplicate or escaping references are rejected. This task ran original-input mode; root owns preservation/replay. Output directories must be fresh. `SAFE_PACKAGE_MANIFEST.json` lists public code/metadata only, with no raw corpus, prompts, responses, profiles, labels or ledger contents.
