# Original-eight method followup

This is an exploratory followup on the same original eight development users. The cohort was fixed earlier, but this followup was proposed after baseline outcomes were observed. It is not an outcome-blind confirmation or a new baseline run. The source remains a recorded response-preference reference: human-rating-derived pairwise labels with model-based filtering. It is not necessarily direct binary elicitation, model-generated target labels, researcher taste, or research utility.

The approved proposal has SHA256 `d251373fe3da7e25ad44e590b2ff518d8ab72c193647d0181c0ab77f7c989d16`. Protocol `original-first8-v1` preserves all 228 planned cells across M4 full history, M4 matched five, M5 and M6. There are 176 currently attemptable cells, 34 permanently withheld hybrid cells for users949/634, and 18 conditional user903 hybrid cells. M7 is unavailable: each user's validation choices have one conversation group, leaving no separate calibration group. Unavailable arms remain explicit failed rows in fidelity output; unscheduled packets remain in the coordinator's planned-cell inventory.

M4 full history uses the existing Bradley–Terry method. Its matched-five control passes the same selected five history examples used by the other methods. M5 and M6 use the existing implementations unchanged, with a wrapper that allows component fitting only from imported response caches. M6's existing validation filter runs after that cache-only fit guard ends. These are existing adaptations, not paper reproductions. Model, prompts, history caps, seed, metrics and method settings match the approved proposal.

## Immutable preparation

Prepare each user into a fresh private directory after the runtime commit is final:

```sh
python3 scripts/overnight_labeled_reference.py prepare-first8 \
  --proposal /absolute/private/approved-proposal.json \
  --user prism:user347 \
  --destination /absolute/private/new-packet
```

Preparation and admission verify the approved original plan/report/completion, exact selected records, canonical lineage and the 887-entry original cache map. The original packet's uncertain hold is preserved; successful cache entries do not make the whole source packet successful. Component replay uses temporary copies and must finish with zero backend calls, no cache mutation, and identical artifacts. Every packet carries private source copies, selected records, cache manifests, typed exclusions and exact runtime hashes.

User903 may supply `--recovery-evidence /absolute/private/recovery-evidence.json`. That evidence contains `{path, sha256}` references named `plan`, `terminal`, `diagnostics_verified`, `envelope_claim`, `envelope_terminal`, `events` and `cache_manifest`. The plan must be the already leased original903 recovery. Its terminal must have known usage and zero holds. Diagnostic claim, terminal, events and exact plan bindings are checked. The cache manifest is a separately frozen **post-terminal snapshot**, not an artifact claimed to have been emitted by the old runtime. The coordinator must inspect its copied bytes and issue a lease for the resulting exact packet. Original and recovery cache maps may merge only when overlapping filenames have identical bytes. Both component fits must then replay from the merged cache. Without this proof, the two hybrid arms remain unavailable.

All nine historical unknown identities are bound using their two exact hash conventions. The consumed user634 fit is also denied. Every actual recovery903 request identity is denied on fresh dispatch, including known invalid-JSON responses; successful cached responses may still be reused. A historical denial halts later network admission and is recorded separately in the completion receipt. New-protocol request uniqueness consumes an invalid-JSON M4 feature response, so matched-five cannot issue it again.

## Limits and handoff

| User | Dollar cap | Fresh-call cap | Hybrid admission |
|---|---:|---:|---|
| 949 | 0.08 | 30 | unavailable |
| 903 | 0.08 / 1.48 | 39 / 260 | conditional recovery proof |
| 347 | 0.11 | 50 | cached fits required |
| 681 | 0.19 | 88 | cached fits required |
| 557 | 0.10 | 46 | cached fits required |
| 480 | 0.13 | 58 | cached fits required |
| 634 | 0.04 | 21 | unavailable |
| 671 | 0.07 | 35 | cached fits required |

The current panel sums to $0.80 and 367 calls; conditional903 raises that to $2.20 and 588 calls. These are proposed maximum reservations, not actual charges or execution authority. Each packet has a 1,800-second cap. The finite coordinator scheduler starts two packets serially, then admits at most two concurrently. The latest packet start is 16:29 UTC and the deadline is 17:00 UTC, November15. Current primary recovery takes priority. Stop new admissions on an additional unknown, invalid accounting, diagnostic failure, or historical denial; drain admitted work and retain holds. Never retry or restart automatically.

The coordinator is the only dispatcher. A lease binds the exact plan, protocol, methods, bounds and unique external claim path. The shared observer must explicitly allow the new runtime pin before calls. Local offline preparation is not authorization.

## Reporting

Keep original baseline, new56 expansion, recovery903, earlier two-user method followup and this original-eight followup separate. Report delivery over all228 planned cells, complete paired user/choice comparisons and exclusions. Include full-history versus matched-five exposure, fixed method order, missingness, empty profiles, uncalibrated confidence and validation-selection differences. No small-panel ranking establishes a general winner.

Report aggregate fit-and-predict usage. Completion receipts bind request identities, final report and prediction hashes, initial/final cache maps, new cache entries and cached-fit proof. External observer events distinguish actual transport from wrapper attempts. Cache hits and repeated cached outputs are reused evidence, not independent new observations. Matched-five may require zero incremental feature calls after full-history M4 while still having a nonzero standalone cost. The original shared-user cache and the new per-user copies have different cache topology.
