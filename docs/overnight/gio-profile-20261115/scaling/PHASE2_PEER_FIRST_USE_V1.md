# Peer-P7 preparation on unchanged phase 2 execution code

The new pure compiler supports the existing f6 driver peer contract. Six
synthetic P7 packet drafts pass the unchanged driver's preparation checks;
they cover 12 prediction call ceilings. Three fresh mock extraction instances
exercise current quote-only P7 construction. No provider calls were made.

The compiler source SHA256 is
`cdafe348558fbf2dfbede6e66608f02d39e858ba7aaf4727afaf49d71d7400aa`.
It is preparation code, separate from execution runtime
`f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`. The generated manifests keep
`code_sha=f6cd4fb5...`, and profiles remain original f6 instances. Do not edit
the frozen runtime or label an old profile with a new runtime. The coordinator
can prepare these drafts outside the runtime checkout and pass authorized
packets to the existing f6 driver. Preparation itself grants no authority.

## First use and exact freeze

From the Role09 checkout, this offline command loads the new compiler separately
while importing all execution dependencies from exact f6:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 docs/overnight/gio-profile-20261115/scaling/build-phase2-peer-fixture-v1.py /Users/giordanorogers/.codex/worktrees/gio-overnight-phase2-runtime/AutoResearch-overnight-control
```

It creates fresh synthetic P7 profiles, compiles, validates all six packets
with discarded in-memory test authority, and asserts that the historical
ordinary phase 2 fixture still recompiles exactly. It cannot call HTTP. Saved
drafts have null lease and authorization fields. The synthetic profiles'
`fit_usage.attempted_calls` counts mocked builder invocations, not API calls.

The resulting fixture is
`driver-fixture-phase2-peer-v1-a017ec9db3bfb02a1b189c4810582c538690d6ce9a8b698cb7003e919f1dc2dc.json`;
the filename is its file-byte SHA256. Its parent is the separately published
ordinary fixture `148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6`.
The fixture separately records compiler/helper/generator file hashes and the
unchanged f6 driver, runner, backend, contracts and original compiler hashes.

Compilation alone, with phase 2 modules first on `sys.path`:

```python
import importlib.util
import json
from pathlib import Path

role09 = Path("/Users/giordanorogers/.codex/worktrees/gio-overnight-scaling/AutoResearch-overnight-control")
loader = importlib.util.spec_from_file_location("autoresearch.taste.overnight.scaling_preparation",
    role09 / "autoresearch/taste/overnight/scaling.py")
compiler = importlib.util.module_from_spec(loader)
loader.loader.exec_module(compiler)
fixture = json.loads((role09 / "docs/overnight/gio-profile-20261115/scaling/driver-fixture-phase2-peer-v1-a017ec9db3bfb02a1b189c4810582c538690d6ce9a8b698cb7003e919f1dc2dc.json").read_text())
compiled = compiler.compile_driver_packets(fixture["manifest"], fixture["bindings"], runtime=fixture["runtime"],
    expected_manifest_hash="4b4f80485b7ec4758c9ccac4391689fdaaddac2e337a877f256d078246701fb2",
    expected_bindings_hash="1b2b4f49a34ff45a46f0d926756d61b8008098ca7b159b09140b10e933bd3824",
    expected_runtime_hash="22df457703a71ceab262ce967f4320e5c297e8f4ea0931a5e6cfa5c1376ae25a")
assert compiled["compilation_sha256"] == "3397aeb11ff45470b5a263c8e1090530d11d065293fdca44c0c84137f66fd2b2"
assert len(compiled["packets"]) == 6
assert compiled["estimates"]["max_attempts"] == 12
```

As with the ordinary fixture, absolute paths are frozen. Another host must
regenerate/rebind and freeze new digests; never rewrite saved profile lineage.

## Additional real-binding input

Start with the ordinary schema in `PHASE2_FIRST_USE_V1.md`. For a ready
`released-development-v2-p7-peers-v1` cell, add exactly:

```text
peer_parent_releases: [
  {researcher_id: <declared target or peer>, release_json: <exact UTF-8 parent file text>},
  ...
]
```

Order must match the sorted `release.parent_releases`. The coordinator supplies
only evaluator-approved original fit releases. The compiler checks each exact
text's SHA256 against that parent's declared file reference, rejects duplicate
JSON keys, verifies researcher identity and original release schema, and checks
that the derivative contains exactly the sorted union of parent records. It
retains full record and permitted-span hashes. Target `items`, `items_sha256`
and opaque `target_bundle_sha256` must match the target parent exactly.

Only the approved release fields are accepted. Known release counts/version/tier
metadata are allowed; `sources.heldout` may contain only dev/confirmation counts.
Item objects must have the exact label-free driver keys. Private target bundles,
scored rows, answer fields and generic extra JSON are not this interface. The
compiler checks supplied bytes and declarations; evaluator approval and source
attribution remain external authority, not something these local checks prove.

Both the saved profile config and prediction config preserve exactly
`approved_peer_sources`, `peer_policy` and `parent_releases`. Missing or changed
declarations fail. Peer releases are P7-only; ordinary releases/profiles reject
peer metadata. The driver independently reads and verifies referenced files.
No parent text is added to the consumer prompt by the compiler.

The frozen source condition differs from target-only evidence. Every P7 packet
records `scaling_peer_evidence.parents` with target/peer roles, source counts,
full-content UTF-8 byte counts and parent file hashes. These are full-source
counts, not rendered token use. Cross-manifest comparisons with target-only
controls **do not hold evidence constant**. Non-P7 candidates and controls are
explicitly unavailable in this peer-only fixture; they are not silently given
peer evidence or omitted from inventory.

A joint arm requires the respective S/M/L P7 extraction instance. B consumes
one exact fixed profile at every consumer level; C reuses exact S/L instances.
Access probes alone do not supply those builds. Selection, permitted inputs,
actual settings/limits, leases and execution remain coordinator responsibilities.
No result here establishes model ordering, fidelity, utility or a winning method.
