# Private evidence retained outside the worktree

A verified checkpoint now preserves the published audit evidence through commit
`4694966339a58a463234fa6044a007fb01c743ca`, covering packages 001–033, at:

`/Users/giordanorogers/.local/share/autoresearch/archives/gio-user-model-integration-audit/checkpoint-4694966`

It contains 12 private input archives, a Git-generated public evidence archive,
and recovery instructions plus the exact copier. Fifteen named files were copied
and reverified; all originals remain unchanged. The copy is 25,478,343 bytes
excluding its manifest and receipt. Public archive contents match all 2,047
selected committed Git blobs, not merely a newly generated checksum list.

Files are mode 0600 and new directories 0700. The checkpoint survives removal of
the audit worktree. It remains on the same machine and is **not an off-device
backup**. Later packages 034 and onward are not included. The separate full
owner archive for downstream04 is referenced by the public evidence but is not
duplicated here.

Recovery was exercised using only the copied evidence and recovered public tree.
The terminal verifier reproduces all 2,252 record references byte-identically;
the memory reader reproduces all 477 checks and its exact inventory, with only
recorded argv differing. No original temporary input paths, model calls or
active ledgers are needed for these two replay checks. This verifies those
recovery paths; it does not rerun every historical audit or preserve a complete
Python environment.

See `RECOVERY.md`, `copy-manifest.json`, `copy-receipt.json` and `verification.json`
for the inventory, scope and reconstruction procedure. All raw archives remain
private; this published package contains only metadata, source and commands.

Independent review verified the copy and found a future nested-directory edge
case in the historical copier. The additive portable copier fixes it, with an
expected failing old-script probe and passing new-script probe repeated by root.
The actual checkpoint already had the correct modes and remains unchanged.
See `PORTABILITY_NOTE.md`; use the portable variant for future deeper layouts.
The standalone Git-blob verifier requires a Git repository containing the pinned
commit, while the demonstrated 032/033 recovery readers use the retained files.
