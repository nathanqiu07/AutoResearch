The released recipe closes audit026's four recorded-only construction fields. Independent reconstruction matches **all 84 `profile_id`, 84 `config_id`, 84 `prompt_sha256`, and 84 `selected_spans_sha256` values** in the unchanged original construction report. Original-input replay passes 1,063 checks; replay from the existing verified private archive passes 1,097 checks. Both exit 0, with zero failed checks and zero model calls, and produce identical 84 reconstruction rows.

This is an additive follow-up to audit026. Its original findings correctly described the evidence available then. No original026 report, reader, fixture, root private receipt/replay, frozen runtime, profile, or owner checkout was changed.

The supplementary release is `3e4cc416b742cdd1a5e9193dee2b6b424279d691`. All three published Git object pins match:

| Supplement | SHA256 |
| --- | --- |
| `014-semantic-construction-recipe.json` | `7f23ebe84186c74d42c0a4f5c8f6a4c13f6de6765559e471dcab44061ab66302` |
| `014-recipe-ready.json` | `f86fc93783c97f30e8594c6e376883c97324dac463fabe005f540d3b0f2b4b91` |
| `014-semantic-recipe-replay.json` | `998cb216711e1bcf2549490987af8e2ea03d3757b2d6ca5ed3dd445968ab6552` |

The independent reader does not execute the owner's replay script, import project code, or use the owner's replay report as its result oracle. It uses the explicit recipe, original construction report and original approved inputs. The supplementary owner report is hash-verified and inventoried only.

The reader reconstructs the complete canonical profile body in memory from the frozen `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca` formulas in `contracts.py`, `baselines.py`, `retrieval.py`, and `consumer.py`. It reuses byte-identical audit026 reference functions for independent permission clipping, cosine ranking and UTF-8 passage packing. Literal version/schema constants are read from the pinned source AST without importing that code. The prompt/policy identity and composite renderer identity are recalculated from those frozen bytes.

Configuration has exactly the recipe's 16 fields. Documents remain the unchanged separate argument; the full embedding bundle and its original usage/provenance stay embedded in config. Ordered decision options remain unchanged. The extractor identity is exactly `{label: no-model-calls, class: NoCalls, model: construction-only, endpoint: ""}`, with no `base_url` attribute. The inert `NoCalls.complete` increments a counter then raises if invoked; the counter remains zero. No extractor, consumer, owner replay or project builder is invoked. Network operations are denied.

Selected-span IDs are independently computed from passage order, without additional sorting. Each projection uses the canonical JSON digest of the document ID, original start/end, and raw UTF-8 text SHA256; the ordered projection list is then canonically hashed. Exact iteration order is also checked: original index order, with caps 512, 2,048 and 8,192 in that order. All 84 content hashes, rendered byte counts, passage counts, method hashes and renderer hashes still match alongside the newly reconstructed IDs.

`run-01/report.json` records the original Git/approved-file replay. `run-02-private-replay/report.json` records the independent reader operating on the existing root-owned private preservation archive. Its 34 additional checks recheck the Git-object archive members at completion. The 84 public hash/count rows are identical between modes. `REPLAY_COMPARISON.json` records this equality. Both stderr logs are empty; there were no failed execution attempts in this follow-up.

The read inventory is bounded: 34 previously approved Git objects, two previously approved released bundles, and three new published metadata objects. The two source bundles are the same byte hashes already verified in audit026; their recipe paths differ from the earlier coordinator copies, but the recipe explicitly permits relocation by byte hash. No new corpus was read, no live ledger or labels were opened, and no source/query/vector/config/profile content is exported. `run-02-private-replay/input-inventory.json` is the exact inventory. The prior 52-input inventory is included as the read allowlist, not copied raw input.

These are the original **construction-stub** profile IDs. Production profile identities can differ when extractor/consumer identities or full config differ. The result does not establish actual prediction execution, saved-profile reuse, prediction quality, source approval, provider authenticity or billing. The recipe's historical origin and a past process's clean/detached state remain producer metadata. Those limits are unchanged; the four identity-reconstruction gaps are closed.

Portable replay from the approved originals:

```sh
python3 -I -B reproduce_recipe.py \
  --supplement-root /path/to/recipe-retest \
  --repo /path/to/repository-containing-original-pinned-objects \
  --coordinator-root /path/to/approved-coordinator-copy \
  --out /path/to/fresh-output
```

Replay from the existing verified private archive:

```sh
python3 -I -B reproduce_recipe.py \
  --supplement-root /path/to/recipe-retest \
  --archive-root /path/to/extracted-private-archive \
  --preservation /path/to/private-preservation.json \
  --coordinator-root /recorded/coordinator/root \
  --out /path/to/fresh-output
```

Output must not exist. The script and prior independent helper are hash-pinned. Commands, explicit minimal child environments, exit statuses, stdout/stderr, and exact reader snapshots are retained. `SAFE_PACKAGE_MANIFEST.json` lists only public metadata/code files in this follow-up. Private originals remain in the pre-existing audit-owned preservation archive; no new raw archive is needed.
