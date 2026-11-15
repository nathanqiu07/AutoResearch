# Checkpoint recovery through audit 037

A new same-machine checkpoint retains the exact published audit tree at
`f6ef2ee9cf9af5ad3d889412291cd213a3575432` and 16 private input archives outside
the worktree. It is stored at the destination recorded in `copy-receipt.json`.
The previous checkpoint remains intact. Packages 038 and later, the complete
owner downstream archives, and the installed Python/provider environment are
outside this checkpoint.

The 20 manifest entries contain 60,591,548 bytes: 16 private archives, the public
Git archive, recovery instructions, the exact portable copier and the verifier.
Including the manifest and copy receipt, the destination has 22 regular files.
All files are mode 0600; the checkpoint and its private subdirectory are 0700.
The copy checks compare every destination hash with its source before and after
copying. The verifier additionally matches all 2,419 public files to actual Git
blob identities at the pinned commit. These checks verify retained bytes; they
do not rerun every historical experiment.

The public archive was safely recovered into a fresh directory. Audit 037 was
then replayed using only its recovered reader, helpers, source archive and the
checkpoint's private inputs. All 6,336 checks passed. The inventory is
byte-identical; reports match in every field and array except invocation paths
and the order of the 364 control/hybrid overlap assertions. An independent
comparison confirms exact assertion multiplicity and that no other assertion
family moved. Original temporary inputs and original Git source repositories
are not needed by that replay. The other 15 private archives were hash-verified
as copies; their member bodies were not all re-extracted during this checkpoint.

`public-archive.invocation.json`, `copy.invocation.json`,
`standalone-verification.invocation.json` and the four recovery/replay invocation
records preserve the commands and results. `root-verification.json` records the
additional permission, file-set and replay comparisons. `RECOVERY.md` explains
scope and recovery. The new `recover_public.py` helper is included in this audit
040 package; it was created after the external checkpoint was sealed and is not
claimed to be inside that checkpoint.

The main manifest SHA256 is
`ac6eb133abd7d0996812e951d7745d4da265cd3ede746ab841e4083530378320`.
The public archive SHA256 is
`f4be302b38f298637f2756eeec3d4d0a1707d2e0211290e29d08151bd9802317`.
Both originals and the older checkpoint's manifest/receipt pins remained
unchanged. No raw input or private archive is published in this package, and no
model/API call, model-setting change, owner-code edit or active-ledger read was
performed.

One inherited receipt sentence needs careful reading: the two-dispatch archive
in 035 has an overlap-limit sentence referring to the main 500-input copy. Its
explicit count, inventory and actual archive contain two inputs. This checkpoint
preserves that historical receipt unchanged and uses its exact two-member
archive, not the copied prose, to identify the payload.

Repository suite: 677 run, 675 passed, two skipped, exit 0 in 24.706 seconds at
source `f6ef2ee9cf9af5ad3d889412291cd213a3575432`. Independent review found no
actionable blocker. Its 17,197 mostly per-file assertions verify the exact
source/destination hashes, receipt joins, private permissions, public Git blobs
and saved replay comparison. Eleven synthetic recovery controls pass, including
nine rejection cases. The reviewer did not parse private archive member bodies
or rerun the full 037 reader; those recovery checks were performed by root.
