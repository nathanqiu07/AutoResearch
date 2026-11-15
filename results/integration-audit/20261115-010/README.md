# Runner follow-up: one fixed, four remaining

Release `c840615c885464404147a1cdea12343569d331fc` adds full-document hashing and
retrieval binding after the runner audited in package 007. This retest does not
silently carry old findings forward.

Builder-visible document metadata is now bound: unchanged inputs complete;
changed metadata is rejected before claim; explicitly updating the document hash
changes job identity and completes. The old failure is fixed for this case.

Four cases remain reproduced: mutable validated items/settings, cached work past
the relative wall-time cap, a missing-cost-mode claim without result, and complete
profiles whose recorded extraction settings differ from actual calls. See
`findings.md` for exact before/after evidence and scope. These are generated
counterexamples, not observations of real campaign corruption.

Root independently repeated the probe. All 12 owner runner tests and the tested
concurrency/no-retry controls pass. All 160 pinned source hashes remain unchanged;
67 prior artifact hashes were also checked without changing the old package.
No real data, credentials, network, paid calls or owner-code edits were used.

`evidence/` and `root-confirmation/` preserve manifests, traces, claims, caches,
results, test logs and explicit fixed/remaining comparisons. `source/` retains the
source pin and relevant modules. Recreate the snapshot from the exact archive
arguments in `source/AUDIT_SOURCE.json`, copy that manifest to its root, then run
`reproduce.py --source-root SNAPSHOT --out NEW_OUTPUT` with a fresh directory.
Exit zero means reproduction completed, including the four remaining failures.
