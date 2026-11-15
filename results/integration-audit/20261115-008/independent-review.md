# Independent baseline/control audit review

Reviewer role: `parallel_gap_audit`, independent integration reviewer.
Conclusion: **no actionable correctness or false-claim finding within the stated
synthetic checks.** This is a review of the audit script and its retained evidence,
not a second execution of unchanged tests.

Reviewed `reproduce.py`, `run-01/report.json`, `run-01/observations.json`, saved
test logs, and the owning baseline/retrieval source in the isolated snapshot.
No source files were changed; no model calls, private data, or test reruns.

## Evidence and claim boundaries

- **No-profile/name-only:** lines 88-113 vary three synthetic researcher/source
  and metadata inputs while holding task, settings and the explicit name fixed.
  Exact empty/name-only personalization and full recorded requests are checked.
  The saved observations support invariance for these canaries. This does not
  claim universal invariance under every possible input; name-only intentionally
  preserves its name input.
- **Source provenance:** all seven saved fixture records have the same source
  allowlist/hash and 512-byte cap. The script explicitly checks source equality,
  exact character spans, permitted passage fields and serialized byte caps for
  raw evidence, lexical retrieval and profile retrieval. These are synthetic
  approved-set consistency checks, not evidence of evaluator-approved DEV data.
- **Frozen content:** summary and profile-retrieval content is compared exactly
  with the configured frozen content; reused profile ID and original fit usage
  are preserved. The fixture method is `fixture_plain_summary`. Actual P1 output
  integration remains untested and is correctly listed as pending.
- **Decision binding:** changed context and reversed option order are rejected
  before calls through `predict_baseline`. The generic `predict_profile` route
  is deliberately shown accepting a changed context. The report correctly treats
  this as a documented adapter/runner integration requirement, not a newly
  undisclosed integrated-runner defect or a guarantee that all call paths bind
  decisions.
- **Retrieval helper policy hash:** saved policy hashes match current registration
  metadata, and substituting a synthetic helper hash changes each derived policy
  hash. This verifies the helper hash's inclusion in policy metadata. It does not
  establish runtime drift rejection in the generic consumer; that stronger claim
  is not made by the report.
- **Limits:** semantic retrieval remains unavailable without calls. Actual P1,
  peer controls, approved DEV corpus, live accuracy and scaling remain explicitly
  untested. Role05 predates common contract fixes, so artifact regeneration on the
  integrated pinned renderer is still required.

## Verification of retained evidence

The saved log reports **18 tests passed**, exit code 0, from:

```sh
python3 -B -m unittest tests.test_overnight_retrieval tests.test_overnight_baselines
```

This is an inspected saved result, not an independently rerun test result.
I independently recalculated the script, fixture, source-pin and all 143 published
source-file hashes; they match the report and snapshot manifest.

- Source commit: `675f6d23a079c500ea43aaba1016545768f160fa`.
- Implementation commit: `8a310d50a211d5e77194e77fc06babc0b760816e`.
- Audit script SHA-256: `218e504459694e5585f40ef0c4c33fc47f972ab952c4347e7d7d8507436bb768`.
- Fixture SHA-256: `ccda86a7866f1aacb4f5e8817a2888a808023e38681c7b53ef722187c8735cee`.
- Source-pin SHA-256: `ec79ab7fcdf0ce67ac3c7d7b69cb0bc80c2e38719f8ce9d7fe977f620c7b0e61`.

Role attribution: independent reviewer `parallel_gap_audit`; this is not a
cryptographic signature or an endorsement of untested integrated behavior.
