Audit 030 found no discrepancy in the exercised frozen quote integration path. The final run checks **167 synthetic cases across P1–P8: 2,770 assertions pass, zero fail**. There were **161 calls to a local recording extractor and zero live calls**. The resulting profiles comprise 47 complete positive controls, 116 expected invalid results, and four expected unavailable results. Expected rejection statuses are retained as evidence, not counted as failed assertions.

The exact release is `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`. A fresh Git archive contains 160 public code/test/selected handoff files; SHA256 `af007b51ed1886213773c107b3900677fb9e4765f7b4811460f534b3553a4116`. Every extracted file was verified before execution and again afterward. No owner code was edited or mixed with another source version.

The exercised route is the frozen control driver's `_register`, followed by `runner.run_job`, `contracts.build_profile`, the registered family builder, shared quote resolver, family validation, shared post-resolution cap, and `consumer.prepare_payload`. The last step verifies availability and exact rendering without making a prediction call. This does **not** exercise the driver's packet preparation/release eligibility gates, real source approval, evaluator judgments, provider execution, or all possible document cases.

| Boundary | Result through each P1–P8 runner build |
| --- | --- |
| Unique exact Unicode quotation in one approved span | Complete; derived character offsets select the exact source substring |
| Two approved occurrences | Invalid `quote_ambiguous` |
| Duplicate text with only one permitted occurrence | Complete; the permitted occurrence is selected |
| Overlapping permissions around one occurrence | Complete; overlap does not manufacture ambiguity |
| Absent quote; known wrong document; unknown document | Invalid `quote_absent` or `quote_source_document`, as appropriate |
| Occurrence outside permission; quotation spanning adjacent permissions | Invalid `quote_unpermitted`; distinct spans are not joined |
| Collapsed whitespace or decomposed Unicode variant | Invalid `quote_absent`; no normalization or fuzzy repair |
| Fabricated offsets or even correct model-supplied offsets | Invalid `quote_source_shape`; quote-only sources are required |
| Valid citation followed by an absent citation | Invalid; original parsed content is preserved without partial offset insertion |
| Raw JSON exactly 2,048 bytes, larger after adding derived offsets | Invalid `personalization_cap_exceeded`; complete resolved content is retained |
| Matched positive trimmed to exactly 2,048 resolved bytes | Complete and available to the shared consumer |
| Marked inference under explicit-only / marked-inference policy | Rejected / accepted respectively |

The recorder also verifies that extraction payloads contain exactly the approved text segments, including their original offsets. Unpinned document metadata is absent. Each actual extraction has a preserved started trace and complete raw-response trace, raw response hash, one attempted call, and no retry. A successfully returned provider-shaped string can still yield an invalid profile: transport completion and valid extraction are distinct statuses.

Caller rules are intentionally different. P1–P6 accept absent `permitted_spans` as the documented whole-document convention; explicit empty spans resolve no quotation. P7/P8 reject missing or empty attributed spans before extraction, and reject mismatched speakers before extraction. A P7 target statement citing an otherwise valid peer quotation resolves mechanically but then fails `wrong_researcher_evidence`. These are tested caller-policy differences, not evidence of unauthorized access in real data.

The generic resolver preserves non-source extension keys. Each `sources` entry, or mapping containing `document_id`/`quote`, must have exactly those two keys. The family output schemas then reject extra top-level fields. Common configuration preserves unrecognized method-specific fields; the synthetic extension is retained in profile provenance but not sent in the extraction prompt. Neither generic extensibility nor the documented fallback is classified as a defect.

The adopted resolver is `unique-exact-permitted-quote-v1`; `contracts.py` is SHA256 `7d400887f7738f109c3c35c5949c12d4055310ee2d1fa8903b6f9edfaa336f76`. The shared renderer is `caee7409e57bf8270b9d2c5c8fd8830e8072d78070a5e2f794e421011ad1a36c`, computed from both consumer and contracts names/bytes. It matches the pinned role08 handoff, as do P7/P8 prompt identities. `SOURCE_MAP.json` records every P1–P8 registration, method module hash, prompt hash/version, source definition line, policy, and route. The shared-contract document ID is recorded in pinned handoffs; separate contract-document bytes were not reconstructed. This claim concerns actual frozen code behavior and identities.

Source callsites: `control/run_batch.py:233` registers only allowed module/hook pairs; `runner.py:233` performs the actual build; `contracts.py:234` applies the final content/cap check; `contracts.py:43` resolves quotations. Family entrypoints are `profiles_summary.py:192`, `profiles_principles.py:237`, and `profiles_hypotheses.py:269`; their source payload filters are at lines 90, 80, and 106. `consumer.py:28` blocks unavailable/invalid profiles and renders complete ones. Paths are relative to the packaged frozen source.

The first attempt stopped before imports completed: the audit's network-denial wrapper replaced the socket class, which Python's SSL module must subclass. The audit wrapper was corrected to deny operations without replacing that class. `run-01/reader-used.py`, invocation and logs retain that failed attempt; it is an audit-tooling error, not an owner-source failure. Run 02 preserves the first successful 150-case matrix. Final run 03 adds explicit policy/attribution controls and configuration assertions. No earlier evidence was rewritten.

Reproduce using Python's standard library:

```sh
mkdir frozen-source
tar -xf source.tar -C frozen-source
python3 -I -B reproduce.py \
  --source-root frozen-source \
  --source-manifest SOURCE_SNAPSHOT.json \
  --out fresh-output
```

The output directory must not exist. Original command, explicit minimal child environment, exit status, stdout/stderr, and reader snapshots are retained. Socket operations and subprocess creation inside the reader are denied. `run-03/report.json` is final. `synthetic-cases-run-03.tar.gz` preserves its synthetic inputs, local lease records, manifest, profile, result and traces; run 02 has its own preserved archive. These are invented fixtures only. No environment/credential files, private corpus, labels, active ledger, or real runtime inputs were read. No live entrypoint was invoked.

`SAFE_PACKAGE_MANIFEST.json` explicitly lists the files intended for packaging. Extracted source and duplicate case directories remain staging conveniences and are omitted from that manifest. The archives contain the same verified bytes. This closes the bounded integrated quote-mechanics gap left by audit023, while entailment, extraction quality, real source permission/attribution and actual-run evidence remain outside this result.
