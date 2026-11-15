# Portable committed baseline provenance audit

`reproduce.py` uses Python's standard library and local git. It reads the pinned
commit's objects, including the execution commit referenced by `CODE_VERSION`.
It never reads raw run directories, private reports, or working-tree evidence.
Git lazy fetching and replacement objects are disabled. No production files are
changed and no inference is run.

```sh
python3 reproduce.py --source-root /path/to/AutoResearch --source-commit FULL_COMMIT_SHA --out /path/to/new-output
```

The output directory must not already exist. It contains:

- `report.json`: file SHA256 hashes, three checksum checks, code-version checks,
  preparation/execution differences, runner/runtime source hashes, dependency
  metadata, and reconstruction limits.
- `findings.md`: readable findings generated from the report.
- `command.json`: exact invocation, tool SHA256, and exit code.
- `git-commands.json`: exact git commands, return codes, stderr, and stdout hashes.
  Missing runner files at the execution commit intentionally produce recorded
  nonzero git lookups; the corresponding report fields mark them absent.
- `stdout.txt`, `stderr.txt`: outcome streams from the reproducer.

Exit zero means the report was written. Inspect its checks; it does not assert
statistical comparability or a complete attestation of the execution environment.

The included `evidence/` run pins
`40f7db0d88e020aeea5dfeff591b71b8812ba0ad`. It found 22 artifact files, checksum
matches of 21/21, 6/6, and 6/6, and nine preserved preparation/execution differences.
It contains only committed-source evidence and new audit metadata.

Synthetic offline tests:

```sh
python3 -m unittest -v test_reproduce.py
```

All four tests passed. They check pinned-object reads despite later commits and
dirty/untracked working-tree files, missing/changed manifest entries,
missing-versus-null settings, and refusal to reuse an output directory.

The scope excludes interpreting awareness measurements. It also excludes any
verification of local raw logs or provider call records.
