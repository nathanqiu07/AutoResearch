The released sparse index reconciles to **612 unique jobs**: 330 builds and 282
prediction jobs. Its 1,036 completed prediction rows comprise 672 personalized
rows from 48 complete extracted profiles, plus the 364 control/hybrid rows
already audited in 034. The 28 P1 rows audited in 033 are inside those 672 rows,
so this closes bindings for 644 additional personalized rows; it does not add
new observations to the historical study.

All 96 planned extraction cells match frozen 035 by cell identity, build job,
result hash and outcome: 48 complete, 39 invalid, 7 empty and 2 unavailable.
The complete profiles each feed one 14-item prediction job. The other 48 cells
have no prediction jobs/results in this index. Thus the planned core grid has
1,344 prediction slots, 672 delivered rows and 672 absent rows. Invalid, empty
and uncertain extraction outcomes remain visible; they are not silently turned
into completed predictions. The separate hybrid-cap512 omission remains 28
not-dispatched rows in the released metadata.

The reader reconstructed all 672 personalized effective prompts and their
1,344 started/completed traces. Each raw trace hash is checked before parsing.
It binds the full serialized profile, selected profile admission, build parent,
source documents and manifest, item/order, semantic job/config, method and
renderer source identity, backend/model/settings, cache key, parsed response
and saved result. It does not import owner runtime code or an owner checker.
The shared runtime is exactly f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca; 92 source
files are pinned in the public code archive.

All 612 indexed result files were read and hash-checked. For the 364 previously
audited control/hybrid rows, exact result-row bytes and ordered trace hashes
match the pinned 034 report; 037 does not repeat their full trace semantics.
For the 28 previously audited P1 rows, result, payload/settings/backend and both
trace hashes match 033. The 112 control aliases and 84 memory references remain
non-additive mappings. Their underlying rows are already in the 1,036 total.
Richer aliases, their later adoption and repeat runs are outside this index and
audit.

Summing `result.usage.attempted_calls` once per indexed job gives **1,132 recorded
usage attempts**: 96 extraction attempts and 1,036 prediction attempts. This is
not an authenticated count of physical HTTP requests. The 234 control/hybrid
builds record zero calls. Known study estimates sum to **$0.266053750**, with
**$0.019078625** still held for the two uncertain outcomes, giving a recorded
known-plus-held bound of **$0.285132375**. Cumulative batch ledger snapshots are
not summed. These totals exclude neutral probes, embedding production and other
historical jobs; they do not establish provider billing or a current campaign
balance.

The requested literal request-equivalence check uses only prompt, system,
caller settings, backend identity and configured timeout hashes. Item ID/order
remain member metadata and do not split groups. All 672 personalized executions
form distinct groups of size one. A synthetic control with different item IDs
and identical execution fields groups together; changing the prompt splits it.
This is exact recorded-input equality only, with no semantic grouping,
independent-judgment claim or inference about interchangeable stochastic
outcomes. Every execution and its recorded job cost remains counted.

The final run passes **6,336 checks over 2,222 pinned private inputs**. Eleven
synthetic guard/grouping controls pass. The first attempt's retained failure was
in audit comparison formatting: 033 includes a configured-timeout hash that the
initial 037 comparison omitted. All 672 personalized trace pairs had passed
before that assertion. Adding the computed timeout hash resolved the audit
comparison; no owner artifact changed. Later candidate checks strengthened
selection/contract binding and corrected the grouping key to exclude metadata
IDs. Original attempts remain saved, and final row evidence and input inventory
are identical to the first fully passing run.

The index supplies trace hashes but omits paths. Root explicitly authorized the
fixed f6 runner derivation used in 033/034: from the referenced result's job-ID
directory, read only `traces/%04d-started.json` and `%04d-complete.json`, each
with its ordered result hash. The exact source lines/hash and derived references
are in the report. No directories were scanned, no alternate paths were tried,
and no hashless trace or unreferenced manifest sibling was opened.

These are saved-artifact consistency findings. They do not authenticate a
provider, score predictions, assess profile quality or researcher fidelity, or
repeat extraction quote-policy validation. No private evaluator labels, scoring
report, active ledger, credentials or live API were accessed. Public evidence
contains metadata and hashes; raw profiles, prompts, sources and response prose
remain private.
