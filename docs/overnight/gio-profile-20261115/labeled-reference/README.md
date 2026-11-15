# Recorded human-preference reference

This lane compares the existing M0–M3 implementations on eight development users from the PRISM PersonalRewardBench derivative. It tests recorded preference prediction. It does not measure research taste or downstream research utility, and it does not reproduce the original methods' papers.

## Evidence and frozen comparison

The source is `MichaelR207/prism_personalized_0125`. Its pair labels are derived from recorded human response ratings, then filtered for personalization and model disagreement. Those filters limit what this small reference can establish. The construction is described in [PersonalRewardBench, section 4](https://aclanthology.org/2025.acl-long.397.pdf); the upstream [PRISM collection](https://github.com/HannahKirk/prism-alignment) documents the human feedback origin. The local normalized cache and canonical manifest are pinned by file hashes in each private plan.

Canonical parent manifest ID: `b6e2453150fb5983052e393497e62c094aa44998796ecfd27817d05962c280c9`.

The seed-zero panel is fixed before calls:

| User | History | Validation | Target |
|---|---:|---:|---:|
| prism:user949 | 8 | 4 | 9 |
| prism:user903 | 14 | 7 | 9 |
| prism:user347 | 8 | 2 | 7 |
| prism:user681 | 18 | 5 | 9 |
| prism:user557 | 7 | 3 | 6 |
| prism:user480 | 9 | 6 | 6 |
| prism:user634 | 10 | 4 | 8 |
| prism:user671 | 10 | 2 | 3 |

This yields 174 staged records, 57 target choices and 228 target predictions across M0–M3. All methods use the existing `gpt-6-luna` backend with no reasoning or tools and at most 2,048 output tokens. History is capped at five, M2 hypotheses and M3 principles at two, and M2 exemplars at one. M0 has no history; M1 supplies history; M2 uses a bounded SynthesizeMe adaptation; M3 uses a bounded Inverse Constitutional AI adaptation. M2 uses validation labels for selection while M1/M3 do not, so this compares the existing full methods, not representation alone. No fit or prediction cache is transferred from earlier runs.

The conservative pre-cache bound is 1,343 requests. The requested ceiling is $5 OpenAI, 1,500 attempts, 3,600 seconds, one sequential process, with no admission after 2026-11-15 17:00 UTC. A coordinator-issued lease may tighten any limit. These ceilings alone do not authorize a launch.

Primary report: user-macro target accuracy, paired user differences versus M1 and a user-level bootstrap interval. Brier scores cover valid predictions only and must be read alongside failure counts. Existing usage is aggregate fit plus prediction; it is not separately timed or billed by phase. Inspect learned artifacts privately for empty profiles and report only counts. Equal/worse target accuracy, failures, empty profiles or improvement confined to validation count against added value. Eight users do not justify a general winner. A budget-truncated or uncertain run must be marked incomplete; remaining cells stay visible and cannot be silently dropped.

## Execution and controls

Run from the reserved branch at its recorded commit. Preparation hashes every source byte but parses only development rows, checks exact normalization and canonical membership, and writes a derived development-only manifest plus records and plan outside Git. All private files use mode 0600 and the packet directory uses 0700. Original manifest and final-use marker are not written.

```sh
python3 scripts/overnight_labeled_reference.py prepare \
  --source /absolute/private/prism.jsonl \
  --manifest data/prefdata/prism-splits.json \
  --destination /absolute/private/new-reference-packet
```

Prepare only after the runtime commit is final. The plan pins HEAD, Python version, the wrapper, all package Python files, both snapshots and the parent manifest. Do not edit the runtime after freezing the packet. The lease must bind the exact plan hash and use this shape (placeholders are not an executable lease):

```json
{
  "job_id": "COORDINATOR_ASSIGNED",
  "role": "10",
  "state": "authorized",
  "provider": "openai",
  "model": "gpt-6-luna",
  "plan_sha256": "EXACT_FROZEN_PLAN_SHA256",
  "max_usd": 5,
  "max_calls": 1500,
  "max_seconds": 3600,
  "deadline": "2026-11-15T17:00:00Z",
  "final_authorized": false,
  "user_partition": "dev",
  "methods": ["m0", "m1", "m2", "m3"],
  "claim_path": "/absolute/coordinator/claims/UNIQUE_JOB_ID.json"
}
```

The shared claim parent must already exist, and the claim must be outside the packet. Atomic exclusive creation consumes the lease before execution, including if the packet is copied. A crash does not reset this claim. Do not delete claims or retry; reconcile first and obtain a fresh lease. The backend reserves conservative cost before each request and stops further network calls after an uncertain outcome. It does not retry. Existing budget checks bound attempts and elapsed-time admission; an in-flight request may finish after the time boundary.

```sh
python3 scripts/overnight_labeled_reference.py run \
  --plan /absolute/private/new-reference-packet/plan.json \
  --lease /absolute/coordinator/exact-lease.json
```

The process reads `OPENAI_API_KEY` from its environment without printing it. Raw rows, labels, predictions, model artifacts and cache remain in the private packet. Share only aggregate metrics, code/input/report hashes, usage, errors and limitations. Preserve the entire packet, including failed attempts. Independent final holdout remains untouched.
