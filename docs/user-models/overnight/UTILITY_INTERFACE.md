# Future profile comparison: interface and readiness

Checkpoint checked against branch `codex/gio-filtered-icai`, publication commit `053aae78a965ef18b94a0adbd3a520f6069e2346`. This is a handoff, not a new run or a working profile-arm adapter.

## What works now

`scripts/gio_petri/run_baseline.py` accepts a frozen packet directory containing `seed.json`, `baseline.template.txt`, `settings.json`, `checksums.json`, and `review-instructions.txt` for the new review. It validates settings and hashes, records calls and costs, and runs only the baseline arm. Supplying a profile template in that directory does not activate a profile comparison: the arm loop is explicitly baseline-only.

The older `prepare.py` can prepare an ICAI template from an M3 model and its filtered-refit handoff. It requires nonempty principles and specific history/split checks. That is not a generic free-text profile interface and does not support the coordinator's new frozen contexts. Its reference to `run_pair.py` is a historical planned command; that runner does not exist here. Do not execute it as a ready comparison recipe.

## Minimal handoff for a future adapter

Provide these fit-only artifacts, without held-out content or labels:

| Input | Required content |
|---|---|
| Context | One UTF-8 text file with the exact researcher guidance to append to the auditor prompt; an opaque candidate ID and SHA-256. No fresh retrieval during the audit. |
| Release receipt | Evaluator's explicit fit-only release, source-group manifest hash, extraction method/version, and limitations. No unrestricted corpus copy. |
| Runtime receipt | Consumer implementation commit, prompt/rendering version, and exact rendered baseline and profile prompts with hashes. Record text escaping, token budget and any truncation; no silent clipping. |
| Comparison manifest | Development seed ID/text/hash; both arms; repeats/order; unchanged models, provider routes and generation settings; common turn allowance; frozen review instructions; allocation from the shared ledger and prior spend. |

The proposed intervention is one frozen guidance block in the **auditor's** context. Keep the original seed and common prompt unchanged. Do not insert the profile into the target or give the judge the candidate identity. The two arms may generate different environments; that is the intended effect being tested. A fixed seed does not mean identical generated environments or deterministic model outputs.

## Readiness and remaining work

**Not ready for an interpretable utility comparison. No honest completion time can be promised yet.** The latest baseline never presented the intended shutdown decision, then failed on target truncation. Its postmortem was rejected by the evidence validator. Publication includes all of those failures at `results/gio-baseline-review-02/`.

Two separate prerequisites remain:

1. Establish a common setup that actually presents the seed's required situation while leaving the target free to choose. Define the truncation/failure policy before running. Apply any approved setup change equally to both arms. Keep failed attempts in the record; do not reroll until a preferred outcome appears.
2. Add a scoped profile-arm adapter under Gio's scripts, with offline checks that only the intended context block differs, a shared budget, complete provenance, and blind review. The saved baseline alone does not provide that adapter.

Once both are verified, the earliest useful experiment is one matched baseline/profile pair as a feasibility check, with each arm's validity reported separately. It would not establish a reliable personalization gain. Any new paid execution needs its own frozen matrix and explicit allocation; this handoff does not spend funds or change the existing experiment.

Loop, scorer and budget ownership remain with the experiment owner. Corpus intake, source splits and held-out custody remain with the coordinator/evaluator. No researcher context or held-out data was read for this handoff.
