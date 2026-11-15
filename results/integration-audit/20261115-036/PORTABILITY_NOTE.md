# Additive nested-directory portability fix

The executed `copy_private_checkpoint.py`, its manifest and receipts, and the retained checkpoint are unchanged. Independent review verified that the actual checkpoint's two directories already have mode 0700 and all 17 retained files have mode 0600. This fix concerns future manifests with deeper destination paths; it does not remedy an exposure of the current evidence.

With umask 022, the original per-file `mkdir(parents=True, mode=0o700)` creates the requested leaf directory with mode 0700 but can create an implicit intermediate directory with mode 0755. A one-byte synthetic destination `nested/leaf/file` reproduces that behavior.

The separate `copy_private_checkpoint_portable.py` creates each missing directory individually and sets its mode to 0700. It leaves existing parent directories alone. Source hash checks, exclusive destination/file creation, payload contents, manifest/receipt behavior and original-byte checks retain the original behavior. The old copier remains the exact program used for the historical checkpoint.

`probe_copy_permissions.py` exercises the real copier under an explicit child umask 022. It checks every new directory, copied file modes, the unchanged one-byte payload and source hash, and refusal to overwrite an existing destination or receipt. Its expected results are literal modes and the known SHA-256 of the synthetic byte. The old implementation exits 1 on the directory-mode assertion; the portable implementation exits 0. Commands, stdout/stderr, observations and hashes are preserved under `portability-regression/`.

Reproduce using fresh scratch directories on a POSIX system:

```sh
python3 -I -B probe_copy_permissions.py \
  --copier copy_private_checkpoint.py --out /path/to/fresh-old-probe
# Expected exit 1: the intermediate nested/ directory is 0755.

python3 -I -B probe_copy_permissions.py \
  --copier copy_private_checkpoint_portable.py --out /path/to/fresh-portable-probe
# Expected exit 0: every new directory is 0700.
```

No real archive was recopied, extracted or changed for this fix. The historical checkpoint still covers only packages 001–033 on the same machine. This additive note, portable copier and regression evidence are not retroactively inserted into that checkpoint. Its public Git archive still excludes later packages 034/035 and this package 036. The separate Git-blob verifier still needs a repository containing the pinned commit; the demonstrated recovered 032/033 readers use retained copies without original input paths.
