# Independent loader-delta review

**Reviewer role:** independent audit reviewer (`parallel_gap_audit`).
**Review date:** 2026-11-15. **Conclusion:** no actionable correctness or false-claim finding in the reviewed delta.
This is a role attribution, not a cryptographic signature.

Scope: the uncommitted changes to `scripts/user_model_audit/profile_audit.py` and
`tests/test_user_model_profile_audit.py` relative to
`0ebcf7b19bacca64c1bd22a2c4383f39edf889d8` in
`/Users/giordanorogers/.codex/worktrees/gio-integration-audit/AutoResearch-gio-auditor-setup`.
The delta adds the real adviser directory loader, compares direct/adviser request
conditioning, and probes rejection of changed backend label, endpoint, and class.
Previously reviewed issues were not reopened.

## Independently executed checks

With the reviewed checkout as the working directory:

```sh
python3 -B -m unittest tests.test_user_model_profile_audit
```

**Reviewer observation:** 11 tests passed; exit code 0; unittest reported 0.505s.
The output was observed in the review tool transcript, not retained as a separate
log file by this reviewer. Tests were not rerun to produce this record.

The reviewer inspected both reports in
`results/integration-audit/20261115-003/observations/`. Their tool hashes match the
reviewed tool and preserved tool snapshot. All nine fixtures in each report
(M0–M7 plus synthetic calibrated M7) show preserved artifacts, matching direct and
adviser request sequences, no adviser errors, rejection of all three mismatched
backend identities, and zero recording-transport calls during guard checks.
These are inspected saved results, not a second execution of that fixture matrix.

Two additional offline fault injections were independently executed in memory
using `unittest.mock.patch` on `research.advisor.load_user_model` and the synthetic
M3 fixture. No production file was changed:

1. After normal directory loading, wrap only that model's `predict` to append
   ` CHANGED` to its context before invoking the original method. The resulting
   `team_loader.conditioning_matches_direct` was **false**, as required.
2. Have the patched directory loader reuse the first correct recording transport
   when subsequent mismatch variants are supplied. The resulting
   `backend_guard_checks` were **{"label": false, "endpoint": false, "class": false}**,
   correctly exposing the bypass.

Both injected probes exited successfully after asserting the expected failures
of the audit checks. They used recording-only transports and temporary canonical
`usermodel.json` files; no external backend or real user artifact was used.

## Exact hashes

Reviewed tool SHA-256:
`da3d154866a2d865ad49a307cb7cd525a6f930ff1633d6a5e3842d78ef0f83df`

Reviewed test-file SHA-256:
`e9c7a5e026eed8f4eeeebb6fa99790ef48c9dea3181f0dc68b6636d06dea739c`

The following source hashes are taken from the inspected 003 reports. Complete
Python source hash maps remain in those reports.

| Report | Source commit | `autoresearch/research/advisor.py` SHA-256 | `autoresearch/taste/usermodel.py` SHA-256 |
|---|---|---|---|
| main_derived | `0ebcf7b19bacca64c1bd22a2c4383f39edf889d8` | `114216c12ef676d7e0f0d4ae79f19cd6fafaa5107296886d99caa919679aaa69` | `ad49c33ef359d8b11b792d8ba80397b8b6f13b316edd0892cef82c39cec9d506` |
| pilot_draft | `9616fe8a3c550664d8aae0b72c938d936c0a7347` | `71331d6d92db646a052f8595f280ec04a1438f1b139c74161438e63a791a85a2` | `b91842902d5d80fb9c6e960d384b67d342e2481f22a93be42a21907ec8c8b7ca` |

## Limits

This review supports preserved saved artifacts and request conditioning through
the actual directory loader under synthetic responses. It does not establish
live-provider compatibility, prediction equivalence under real responses,
calibrated confidence, personal preference accuracy, research improvement, or
Petri execution. Passing fixtures do not exhaust all possible serialized inputs.
The identity shim and synthetic-only limits remain explicit in the reports.

**Signed by role:** independent audit reviewer (`parallel_gap_audit`).
