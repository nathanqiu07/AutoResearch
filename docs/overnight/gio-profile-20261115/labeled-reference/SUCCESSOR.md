# Small new-method successor

The coordinator authorized proposal `9d22bd02d5b70133144845274cc28e7980b880a7f76e971727d41423011e54f6` for the first two structurally eligible users in the frozen new-56 selection. This successor extends method coverage without rerunning their M0–M3 baselines. The active expansion remains on its separate immutable `63a2c21` runtime.

| User | History / validation / target | New arms | Cold call bound | Maximum dollars |
|---|---|---|---:|---:|
| prism:user666 | 7 / 5 / 6 | M4 full, M4 matched-five, M5, M6 | 517 | $1 |
| prism:user380 | 10 / 6 / 4 | M4 full, M4 matched-five, M5, M6 | 578 | $1 |

There are 10 recorded target pairs and 40 proposed new arm/target cells. Each job has an 1,800-second ceiling; the global deadline remains 2026-11-15 17:00 UTC. The coordinator alone supplies exact leases and dispatches, with at most two reference jobs concurrently. These bounds do not authorize a call.

M4 full uses all 7 or 10 history records, as the existing method does. M4 matched-five calls the existing history selector before the unchanged Bradley–Terry fit. This is a thin factory adapter, not a new feature map or fitter. M5 and M6 remain the existing bounded implementations with five selected history records and validation selection/filtering.

M7 is unavailable as a calibrated treatment. All 56 frozen new users have one validation conversation group, so the existing conversation partition produces zero calibration rows. The successor does not manufacture labels, split groups, or relabel an M6 duplicate as calibrated.

## Preparation and admission

`prepare-successor` accepts only the exact authorized proposal and one of the two preselected users. It verifies the original plan, development-only records, manifest, terminal report/completion, zero prior failures and zero uncertain reservations. It copies the approved successful cache into a new private packet; the original cache stays unchanged.

```sh
python3 scripts/overnight_labeled_reference.py prepare-successor \
  --proposal /absolute/private/proposal.json \
  --user prism:user666 \
  --destination /absolute/private/new-successor-packet
```

The new plan binds the runtime, proposal, prior plan, records, split manifest, initial cache manifest and every imported cache file. Admission checks that chain against the authorized proposal, so changing the plan hash cannot silently authorize different imported responses. It also enforces exact arms, settings, history policies, unavailable-method status and per-user limits.

A successor lease uses the existing role/provider/model/development fields and shared exclusive `claim_path`, plus:

```json
{
  "protocol": "newmethods-small-v1",
  "methods": ["m4_full", "m4_matched5", "m5", "m6"],
  "plan_sha256": "EXACT_NEW_PLAN_HASH",
  "max_usd": 1,
  "max_calls": 517,
  "max_seconds": 1800
}
```

For user380 the call ceiling is 578. The coordinator may tighten limits. Use the existing `run --plan ... --lease ...` command only after the coordinator issues the bound lease. Old leases and old runtime identities cannot authorize the successor.

## No-repeat evidence

Before a new network request, the backend hashes the actual endpoint and unauthenticated request body. This identity excludes backend class names and credentials. The unresolved prior user949 request, canonical wire hash `970b0250ee8dabc2697b1f9238e9af8fc6b97529d448c40db1cefd9cbc47df20`, is forbidden. The successor also consumes every admitted wire identity before dispatch, so a completed but invalid-JSON response cannot silently trigger another identical request later in the same job. An uncertain API outcome stops all further network calls in that job.

The two selected prior runs completed without failures or holds. Their 118 and 133 successful cache entries are imported by exact hash. A zero-network replay of M5 fitting used 105 and 127 cache hits respectively and needed no new request. M6 replay used the same known fit prefix, then stopped before its first new filter request; neither request matched the forbidden identity. No cache file changed during these checks.

Cache hits are reused evidence. Existing per-method counters combine imported and same-run cache hits; they do not give a separate exact imported-hit count for the complete run. Initial imported-entry counts and hashes are recorded separately. Completion receipts add a request-hash audit, backend charge count, and prediction-file hash alongside the existing conservative spend/hold summary. Backend charges are not automatically equivalent to HTTP dispatches.

## Interpretation and verification

This is a two-user method-feasibility comparison, not a ranking or paper reproduction. Compare M4 full separately from its matched-history control. Preserve invalid outputs, unavailable cells and cache reuse. Confidence remains uncalibrated. Original-eight, new-56, never-dispatched recovery and new-method phases remain distinct; recovery never overwrites original failures.

Boundary checks cover copied-lease replay, final exclusion, exact runtime/data/cache binding, mismatched settings, forbidden wire identities across backend classes, consumed-request blocking, cache reuse without dispatch and matched-five exposure without changing original M4. The repository suite is required before pushing. Independent review and final runtime/packet hashes accompany the coordinator handoff.
