# Terminal record retention

**The verified private archive union preserves all 132 indexed phase1 jobs and
all 84 original admissions in stopped batch `df4cbde…`.** It includes the
original 78 dispatched results and their complete started/terminal trace pairs,
plus six original non-dispatch receipts. The six later continuation outputs are
excluded from this stopped-batch retention. No unresolved required-record or
source dependency remains in the bounded inventory.

This is byte preservation and reconstruction verification, not another model,
content, cost, or scoring review. No provider calls, credential reads, active
SQLite reads/copies, active continuation output reads, raw corpus-tree traversal,
private evaluator label reads, or owner-source edits occurred.

## Private archives and union dependencies

New archives are under the audit worktree's ignored
`runs/user-model-integration-audit/private/` directory. Both have mode0600;
the directory has mode0700. Existing archives were unchanged.

| New archive | Members | Bytes | SHA256 |
| --- | ---: | ---: | --- |
| `terminal-phase1-semantic-20261115-v1.tar.gz` | 631 | 8,121,246 | `a1367bbf307d52ac076399477d2ef6c04a8ce36fe013c9d504748d7520a4de1e` |
| `terminal-phase2-stopped-df4cbde-20261115-v1.tar.gz` | 728 | 1,021,224 | `bf3b85a686cb96f5e18f3875d0c746e0f6ecd0d6242df8076b9e6aea764cf3b1` |

The phase1 archive adds the final28 semantic builds and28 semantic prediction
jobs, terminal index/accounting, exact source, coordination pointer snapshots,
and gaps in earlier phase1 admission/configuration retention. It is not a
standalone copy of all phase1 evidence. The complete union also requires:

| Existing dependency | Verified members | Archive SHA256 | Public receipt SHA256 |
| --- | ---: | --- | --- |
| Audit024, `control-20261115-v2.tar.gz` | 695 | `e246997edb4031f2e39f6db729ef35f9114858e19d6bded9a69150e82acc0f4d` | `6124618a66e857923748313af7c976ef5e19510768151c60871d6e57a8075c48` |
| Audit021, `semantic-20261115-v1.tar.gz` | 50 | `837da8db7193becbe776ae9c115bd73b399b23fda1c6a8dd0b7ca05593b464b2` | `9452e537f2daaba7dbb19209bfb7396c345c2b57b44c2dbcac4d1df60980431f` |
| Audit019, `pilot-20261115-v1.tar.gz` (also covers018 inputs) | 252 | `643f92df856165bd6378fbfc7c292b170d505ba3ace6e64d349368b8ee16a806` | `030a16073c7fdaff999cb27d4e0783ca276b0c58fb365a579bdae2ac8f46745a` |

Every member of these existing archives was independently rehashed against its
pinned receipt. Matching existing bytes were reused by reference, not copied
into new archives. The final inventory maps2,252 required reference records:
893 to verified existing archive members and1,359 to new members. These are
reference-record counts, not model-call counts or unique content hashes.

`private-preservation.json` is the complete public metadata receipt and coverage
matrix, SHA256
`6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8`.
Its216 job/admission rows each identify recoverable preparation, original
packet, source/profile/bundle bindings, dispatch receipt and, where dispatched,
manifest, claim, result, profile and traces. Shared batch/index/accounting
records and source trees are separately inventoried. All missing lists are
empty. The private tar files contain raw released material and must stay out
of Git and public evidence packages.

## Terminal and accounting boundaries

The phase1 completion index SHA
`d0acaae53d84e6ee5540279b5dbe2a1d4dda423e5403bed525054aa6e3535bad`
and final accounting receipt SHA
`4ca50af58323a420285f9e5e97168951df4daec549a75a9963e772f9c5cb4e9b`
record a closed phase1 with zero pending or uncertain requests. Its132 jobs
retain130 complete and2 invalid outcomes. The job records report142 attempts;
the two separately retained embedding-production attempts bring the accounting
receipt to144. These are recorded counts and estimates, not an invoice audit.

The original stopped preparation SHA is
`5d79f8f8a631c72e0ba8f1f38f3a3a961a39d513378e79673078a0141d1e091f`;
its terminal summary SHA is
`8b1e6a782fa5fe1b564c2b14e7a6a62677f0d1ab862fb373f3d1346e6ea2f690`.
It retains36 complete,38 invalid,2 empty,2 unavailable and6 not-dispatched
admissions. Both unavailable outcomes with uncertain usage remain consumed;
their failed trace records and claims are retained. No status was repaired,
reclassified or retried.

The stopped accounting snapshot SHA
`498e22da3e68ed8a08fccc3d4d6bdf741103af87999f703442d74f06f83032e6`
and separate continuation authorization SHA
`a9b150194ecff9a99ba86c7615fb00c3ee3eade5f684b99c4d8008ba95324e04`
are retained as frozen records. They preserve82 predecessor attempts,
0pending,2uncertain,85,457,190 known-spend nanos and19,078,625 retained-hold
nanos. The old ledger is stopped with holds, not reset or closed. The
continuation authorization is a boundary receipt; no continuation policy,
ledger, outputs or requests are followed through it.

Quiescence is supported by these terminal/index states and byte checks before
and after preservation, not chat activity. Historical per-job campaign
snapshots may have nonzero in-flight values; those are retained as historical
records rather than substituted for terminal batch state.

## Source and configuration recovery

New archives contain exact selective `git archive` source snapshots for both
recorded runtimes, including all tracked Python files under `autoresearch/`,
control Python scripts, and present root dependency/guidance files. Full file
hashes and exact archive argv are in the receipt.

| Runtime commit | Source files | Source tar SHA256 |
| --- | ---: | --- |
| `0dcd4b43b82a5a271d195e0bcc6b67695281f37c` | 91 | `ba70dfcfc2424346a64c05eae2ed6856f0c6f528c89114f7c86348ad38ebb60b` |
| `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca` | 92 | `573321eae5ef8765ef276d93ce684272057dde71f5a795d339573b142bc307c4` |

All covered jobs bind one of these two commits. Prepared/original packets,
contracts, profiles, released input snapshots and semantic bundles retain
configuration bytes. The existing021 archive supplies the separate producer
provenance. Original corpus paths embedded inside released files are not
followed. This preserves code/configuration evidence; it does not guarantee a
future provider environment or identical stochastic outputs.

`JOB_REGISTRY` and `PEER_REQUESTS` were copied into the private archive as
hash-recorded coordination snapshots. They are mutable pointer provenance,
not frozen experiment source or proof that an active continuation terminated.
Their unrelated references were not traversed.

## Verification and portable recovery

`preserve-01.invocation.json` records the exact successful preservation command;
all new original bytes and dependency archives were unchanged before/after.
Each new tar member was read back and checked. `verify_union.py` then verified
the entire archive union independently without opening any original data path.
The archive-only result is `archive-union-verification-01.json`; exact command
and output are in `verify-01.invocation.json` and `verify-01.stdout.txt`.

To verify after relocation, place the five private archives together and keep
the public024/021/019 receipts under a relocated audit repository root:

```sh
python3 -I -B verify_union.py --receipt private-preservation.json \
  --receipt-sha256 6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8 \
  --audit-root /path/to/audit-repository \
  --archive-root /path/to/private-archives --out /path/to/new-verification.json
```

The receipt maps every original identity to its archive/member and exact bytes;
archive paths need not retain their original machine prefix. No extraction,
backend or API call is needed for verification. Keep the private directory0700
and archives0600. The preserver refuses existing destination names, so rerunning
it is not a resume or permission to overwrite old evidence.

The first inventory plan found90 gaps in the earlier archive union:76 dispatch
receipts,4 original batches,4 contracts,4 batch claims and2 summaries. These
were not missing from the released originals. Exact terminal/source-defined
records were subsequently added, and the final full check found no remaining
gaps. Both prior plans and commands remain for provenance; neither is the
final completeness receipt.
