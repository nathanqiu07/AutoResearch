This is the requested reference handoff for the existing closed-run inventory
owners. `HANDOFF.md` documents the precise consumed fields, private layout,
custody bindings, reuse rules, publication boundary and fixed assumptions in
the already published 042/044 workflow. It does not create or reconcile a new
inventory, review new scientific/source content, authorize copying, or execute
the old tools on new records.

The author pins 12 public source/summary files. Root separately binds all 12 to
immutable Git objects at `0dbcf0536f2b0ea747e9ff7b9cfb20b4397391d5`, including
exact hashes, sizes and line counts. The original author manifest covers its
two-file core plus itself; `checksums.json` covers this complete package.

The key approved identity tuple is exactly `path`, `sha256`, `roles`, and
`logical_size_bytes_observed`. The old binder checks the full allowed/excluded
partition separately from the copier's narrower controls. Several old schemas,
counts, pins, names and reuse assumptions are fixed to profile204; the tools
are not generic drop-in executables for the new closed inventories.

Existing roles 09/10 retain inventory ownership, role 04 defines typed custody,
and the coordinator authorizes an exact scope and names the copier. Full private
approvals, mappings and raw archives remain private. The handoff grants no access
to their bodies, live SQLite, credentials, unrelated paths or Git payload publication.
No private control, inventory, archive or payload was opened to prepare this guide.

The audit-branch regression log retained with 053 reports exit zero, 677 tests
run, 675 passed and two skipped before joint publication. Those ordinary repository
tests are separate from this static reference; no retention tool is executed here.
