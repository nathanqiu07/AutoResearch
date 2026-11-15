# Consumer diagnostic

Question: on a small fresh development panel, does a stronger consumer predict
preferences more reliably, and does the correct person's full history improve
prediction compared with no history and count-matched wrong-person history?

This is separate from the Petri demo critical path. It selects no automatic winner.

## Frozen design

- Eight previously unused PRISM development users; four targets each; two models
  (`gpt-6-luna`, `gpt-6-sol`); three arms; 192 planned predictions.
- The canonical manifest and the earlier 64-user manifest determine eligibility.
  User and target IDs are selected by fixed hash order, before the source is read.
  An earlier live pilot used user949, already excluded by the 64-user manifest.
- Users form four donor pairs with equal full-history counts. Own and wrong arms
  use every canonical history example for their respective person. No truncation.
  The wrong arm preserves the donor's identity and recorded labels.
- Same native UserModel prompt, target context, option order, no tools,
  reasoning `none`, and 2,048 output tokens for both models. Six conditions rotate
  across fixed target blocks. No response cache or automatic retry.
- Final-user rows are not parsed. Within-user target answers are sealed in a
  separate file and enter scoring only after execution. Selection never uses them.
- Primary metric: accuracy within each user, then equal-user average, counting
  all planned failures or unavailable predictions as wrong. Delivery is separate.
  Own-minus-none and own-minus-wrong differences are descriptive; donor pairing
  makes a simple user bootstrap conditional and incomplete as population inference.
- Character-length control: choose the longer raw Python string; ties choose A.
  Evaluate once per unique target, after execution, rather than once per condition.

Expected evidence: Sol may improve delivered prediction quality; correct-user
history may beat both controls. Equal/worse accuracy, lower delivery, or only a
length advantage counts against useful personal conditioning in this setup.

The donor count match does not match topics, token length, task or label mix.
Eight people and four choices each are a diagnostic, not an independent final
test, proof of research taste, or a comparison of profile extraction methods.

## Execution contract

`scripts/gio_recovery/consumer_probe.py prepare` writes a new private packet
outside Git. It captures exact native requests, hashes source/runtime bytes,
and computes a conservative sum of existing backend per-request reservations.
The coordinator must allocate that exact plan before `run`.

The lease is JSON with these fields:

```json
{
  "state": "authorized",
  "lane": "05",
  "job_id": "COORDINATOR_ASSIGNED",
  "plan_sha256": "EXACT_PRIVATE_PLAN_SHA256",
  "user_partition": "dev",
  "final": false,
  "models": ["gpt-6-luna", "gpt-6-sol"],
  "arms": ["none", "own", "wrong"],
  "max_calls": 192,
  "max_usd": "NUMBER_NO_GREATER_THAN_PLAN_MAX_USD",
  "max_seconds": 3600,
  "deadline": "2026-11-15T19:45:00Z",
  "claim_path": "/absolute/coordinator/fresh-claim.json",
  "ledger_path": "/absolute/coordinator/existing-ledger.sqlite",
  "ledger_policy": {
    "max_usd": "EXACT_EXISTING_LEDGER_NUMERIC_CAP",
    "deadline": "EXACT_EXISTING_LEDGER_DEADLINE",
    "max_inflight": 1
  }
}
```

One sequential process makes at most one provider request at a time. The shared
DollarLedger is coordinator-created. The runner claims the lease atomically;
copied packets cannot reuse it. All raw inputs, responses, traces and individual
outcomes stay private. Native JSON validation failures remain scored failures.
An uncertain transport outcome retains its reservation and stops the lane.
The report counts per-model usage once; repeated shared-ledger snapshots are not
added. A process crash leaves a consumed claim and explicit planned inventory;
it grants no retry. Do not edit runtime files after preparing the packet.

```sh
python3 scripts/gio_recovery/consumer_probe.py prepare \
  --source PRIVATE_CANONICAL_PRISM_JSONL --source-sha256 VERIFIED_SOURCE_HASH \
  --manifest data/prefdata/prism-splits.json \
  --used-manifest PRIVATE_PRIOR64_MANIFEST --destination NEW_PRIVATE_PACKET
python3 scripts/gio_recovery/consumer_probe.py run \
  --plan PRIVATE_PACKET/plan.json --lease COORDINATOR_LEASE.json
python3 -m unittest tests.test_gio_recovery_consumer_probe -v
```

The tests exercise real native prompts, full histories, final-row exclusion,
finite leases, exact wire bodies, invalid JSON accounting, uncertain transport
holds, once-only execution, and failure-inclusive statistics. Only transport is
faked; passing tests are not model evidence.
