Audit 041 completes a narrow outside-worktree recovery copy of audit 039 at
`b35c0f8f47f40b28a0aa6338fb7f626ce0db2b0f`. The frozen preparation README and
commands remain unchanged; this note records root's subsequent copy and replay.

The destination is
`/Users/giordanorogers/.local/share/autoresearch/archives/gio-user-model-integration-audit/downstream039-b35c0f8`.
Its manifest SHA256 is
`4daf780ebdd3b2e53846273242840c44f8b599669dbe18db8b6ec8b01264ca29`.
Ten payload entries total 1,060,424 bytes; the copied manifest and receipt bring
the actual file count to twelve. All files are 0600 and directories 0700.
Original bytes remain unchanged.

The public archive contains exactly 141 committed files: 140 audit039 package
files and its handoff. Each matches its retained Git blob identity, SHA256 and
size. The 43,236-byte private archive adds the thirteen original records missing
from the existing owner archive; it is retained privately, never in this public
package. The public audit039 package already includes ninety missing runtime
source files. The separate owner payload remains an explicit dependency: 210
existing files serve 234 of the reader's 337 logical identities. The capsule
does not duplicate that payload, its three native `.eval` files or the sixteen
earlier private audit archives.

Root verifies the actual copied capsule, extracts its public tree into a fresh
private directory and runs the recovered reader using the copied private gap
archive and existing owner payload. A saved Python audit hook denies subprocess
and socket operations and access to the original checkout paths. All 1,316 checks
pass. The input inventory is byte-identical; all report fields and ordered arrays
match except invocation arguments and actual reader identity. The six input/CLI/
receipt substitutions reverse to the original reader bytes. Exact commands,
stdout/stderr, reports, comparisons and copy receipts are included under
`root-recovery/` and `root-copy.*`.

Ten new public-inventory controls and eleven reused extraction controls pass.
Separate independent review passes 784 preparation checks, eight additional
whole-capsule synthetic controls and 771 copied-location/saved-replay checks.
It verifies all 141 actual Git blobs, exact reused tools, twelve copied files,
permissions, immutable preparation inputs and root's report/inventory equality.
It hashes the private archive without parsing it and does not repeat the full
reader or open owner payload bodies. No actionable blocker was found.
The repository suite at `fb081ab230afd56a91cff1e699f3743813e63c35` also passes:
677 run, 675 passed, two skipped, exit 0 in 24.972 seconds. The test log is pinned.

The capsule contains the recovery tools and guide needed for this replay, but
the later root replay, repository-test and independent-review outputs were
created after its sealing and are not claimed to be inside it. The public 041
package records those later checks. This is same-machine retention, not an
off-device backup, original Git history, complete installed environment or
authenticated provider/invoice evidence. The unarchived Inspect normalizer and
later owner judging/accounting changes remain outside original039 scope.
No real model calls or model/settings changes occurred.
