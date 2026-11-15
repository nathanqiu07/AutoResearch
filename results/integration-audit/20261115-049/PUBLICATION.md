Audit 049 closes the coordinator-owned copy dependency from audit 046. The
coordinator retained all 27 approved payloads (175,124 bytes), plus five snapshot
metadata files (34,897 bytes), at commit
`fad097490d501719d1567bf07dc382faef413feb`. Root separately observed that exact
commit on the remote `codex/gio-overnight-00` branch.

The bounded verifier checks the exact local inventory, regular nonsymlink files,
payload hashes and sizes, copied proposal/decision, payload checksum mapping,
and destination stability. Its 110 enumerated checks pass. The report separately
shows all 32 files matching immutable Git objects at the stated commit, stable
HEAD and clean snapshot-scoped status. Root independently verifies those 32
actual Git objects and binds the 27 payload objects to audit 046's exact decision.

The initial verifier README and manifest correctly say remote publication was
not checked by that verifier. `root-remote-observation.json` and
`root-git-verification.json` supply the separate root checks. The complete final
package is bound by `checksums.json`; the verifier's earlier safe manifest covers
only its frozen eight-file core plus itself.

When reusing `verify_copy.py`, inspect the report's explicit Git fields as well
as its enumerated checks: the exit status covers the local checks, while Git
binding is a separate reported result. For this observation, exact tree inventory,
all-object equality and current-HEAD binding are all true. A local-copy success
alone is not a remote-publication claim.

The source bodies were hashed and compared, not imported, executed, semantically
re-reviewed or copied into this audit package. Original temporary source paths
and embedded private references were not read. The owner's original-immutability
statements remain owner assertions; matching the copies to previously approved
hashes does not establish continuous custody or a later original-file state.
The 27-line `SHA256SUMS` covers payloads only; all five metadata files are bound
separately to Git objects in the reports.

This verifies exact retention and publication, not historical execution, complete
dependency recovery, portability or scientific validity. No model calls, owner
edits or settings changes occurred. The audit-branch regression suite retained
with 047 passed 675 tests with two skipped before the joint publication; it is
separate from these destination/Git checks.
