# Recovering the published integration-audit evidence

This checkpoint preserves audit evidence through commit 4694966339a58a463234fa6044a007fb01c743ca (packages 001–033). Later packages require later checkpoints. It contains 12 hash-pinned private input archives and a Git-generated archive of the published audit evidence, readers, source snapshots, findings, handoffs and two audit tests. No original artifacts were moved or deleted.

Verify every file against manifest.json before use. Keep private/ private. Safely extract public-evidence-4694966.tar.gz into an empty recovery directory, rejecting absolute paths, traversal and links. Its public contents reproduce the published paths. Consult each package README and its preservation receipt for the required raw archive and source version. Commands use fresh output directories; do not execute live runtime backends or overwrite historical evidence.

For terminal recovery verification, run results/integration-audit/20261115-032/verify_union_portable.py from the recovered public tree, passing its private-preservation.json and receipt SHA 6e433a9eda60440d63982f60cd960d23b3282ce02f11c17a2bfedf22727a6cb8, --audit-root as that tree and --archive-root as this checkpoint's private directory. No raw extraction or API access is needed. Package 033 can be repeated after safe extraction of memory-execution-20261115-v1.tar.gz using its README command. Other packages document their own input remapping and scope.

These private archives contain exactly the named audit input subsets. The separate full downstream04 owner archive is indexed in package 029; it is not duplicated here. Some methods require restoring frozen source paths as documented. This copy does not preserve an entire Python environment or guarantee provider availability or identical stochastic outcomes.

The checkpoint is outside the temporary worktree but on the same machine. It survives worktree cleanup; it is not off-device or disaster-recovery storage. Files are mode 0600, directories 0700. Retain this directory when relocating the study.
