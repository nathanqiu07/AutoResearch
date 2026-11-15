# Closed scaling/ownswap byte-preservation receipt

The authorized copy retained **1,814 allowed records as 1,526 distinct objects**.
The 15 excluded source paths were not opened. Verified logical bytes total
84,896,695; distinct object bytes total 65,622,971. These totals were explicitly
approved by the user for the coordination chats and this repository receipt.

The copier verified every allowed source before and after reading and compared
bytes before deduplication. A separately implemented destination-only checker
verified the actual copied controls, mappings, archive inventory, content and
permissions. The saved checker then passed from an unrelated working directory
with isolated Python, without relying on its temporary preparation files.

The exact executed copier and checker are included with their synthetic tests.
Run the self-contained tests from this directory on Python 3.9+ with POSIX file
semantics:

```sh
python3 -B -m unittest -v test_closed_copy test_adversarial test_destination
```

All 64 tests pass: 22 author cases, 13 independent adversarial cases and 29
independent-verifier cases. The adversarial tests reuse the author fixture
constructor; their schedules and assertions are separate. The repository suite
also passed 675 tests with two skips, separately from these artifact tests.

The first real invocation stopped before the copy phase because root invoked
the copier through a symlink alias. The canonical-path retry used unchanged
reviewed code and passed. Both execution records are included. A later reviewer
setup error confused an archive-relative path with a bundle-relative path; the
recovery summary records the correction. Raw private preparation evidence remains
retained locally.

This establishes bounded byte preservation, not semantic validity, model
performance, full experiment replayability or an off-device backup. Unresolved
trace references and packing/sparse/promotion dependencies are not closed by
this copy. No previous archive was read or reused, no model was called, and no
production model or settings changed.

Private paths, raw archive hashes, original controls/mappings and archive contents
are excluded. Actual destination verification requires privately held location
and authority information. The older archive-metadata sharing request remains
separate and held. Public source hashes in this receipt identify the included
code; they are not private archive hashes.

`checksums.json` binds the public files. The publication review distinguishes
preexisting public audit attribution from private archive/control identities.
