# Phase 2 scaling preparation: ordinary releases

The unchanged frozen runtime `f6cd4fb5a7c9bc2fdf1f154f6ad4fda18df174ca`
accepts all 18 ordinary-release synthetic packet drafts through its driver
preparation checks. No API calls were made. Published drafts retain null leases
and authorization sources. In-memory test placeholders were discarded.

The remaining real-input dependency is the coordinator's frozen method/profile
selection and evaluator-approved release. The safe first-P1 metadata index is
not a selection or a complete binding: it lacks approved item bodies and full
source-record hashes. Role09 did not open the referenced private profiles,
sources, targets or labels. Sol/Astra medium access probes prove access only;
they do not supply S/M/L extraction artifacts or fidelity results.

The new peer-P7 release schema is a concrete adapter gap at this checkpoint.
It needs the separately assigned compiler fix; never replace a peer-P7 profile
with a target-only one to make this example pass. CLI and utility remain with
their separate owners.

## Verify the new synthetic freeze

Run with phase 2 modules, even when the fixture lives in the Role09 checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 docs/overnight/gio-profile-20261115/scaling/build-phase2-fixture-v1.py /Users/giordanorogers/.codex/worktrees/gio-overnight-phase2-runtime/AutoResearch-overnight-control
```

This regenerates the same fixture on this host, builds six new P1/P2 artifacts
using fixed mock responses through the current quote resolver, builds two
zero-call controls, compiles, and tests the exact f6 driver. It does not edit
the frozen runtime or rehash historical profiles. Transport is blocked.
Its synthetic profile `fit_usage.attempted_calls=1` denotes one mocked builder
invocation, not a provider call. All six synthetic responses are identical by
construction and cannot establish model quality or an ordering.

The parent fixture file hash is
`ddc8d974e654be1ce2d7c8b28249e36d920bd60559288619a3785e4f55489031`.
Only its synthetic design, source text and item schedule are reused. The new
fixture file is `driver-fixture-phase2-v1-148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6.json`.
Its filename is its SHA256. New profiles preserve the current builder, prompt,
quote-resolution records, source records and runtime identity.

For compilation alone, with the phase 2 checkout first on `sys.path`:

```python
import json
from pathlib import Path
from autoresearch.taste.overnight.scaling import compile_driver_packets

fixture = json.loads(Path("/Users/giordanorogers/.codex/worktrees/gio-overnight-scaling/AutoResearch-overnight-control/docs/overnight/gio-profile-20261115/scaling/driver-fixture-phase2-v1-148b4274513083ac96ef46608f6917f057829c41b435223a57009fe97fe000d6.json").read_text())
compiled = compile_driver_packets(fixture["manifest"], fixture["bindings"], runtime=fixture["runtime"],
    expected_manifest_hash="392b1c0b4066edd0e789e14105ddb4fc1f2854775b0bc1a84ac6bfd0776b2880",
    expected_bindings_hash="af74654c2a073d77602dfd244da6c8362971e1b767ce20a02ddc24ac5047f58e",
    expected_runtime_hash="b1e76e672aafacba429a40f536fd493a1a0831005063288b05893726070b142b")
assert compiled["compilation_sha256"] == "7b2c22b4ef75372c301610e5980fd2a323ca8f87b37cfd72f44f8b5cb801b9c5"
assert len(compiled["packets"]) == 18
assert all(p["packet"]["lease"] is None for p in compiled["packets"])
```

Absolute file references bind this checkout. On another host regenerate and
freeze new binding/compilation digests; do not silently alter frozen references.

## Real input boundary after selection

Prepare one design per researcher, evidence tier, cap, replicate and approved
source condition. `build_manifest(design, profiles)` binds all ordered items,
contexts/options, full source records including permitted spans, profile bytes,
backend settings, prompts, common runtime and byte caps. Numeric caps are UTF-8
byte bounds, not measured tokenizer counts. Do not copy the synthetic hashes,
IDs, contract digest, limits or diagnostic receipts into a real design.

Supply one binding for every unique manifest cell:

```text
ready: {cell_id, status:"ready", release_ref:{path,sha256}, release,
        jobs:[{item_ids:[ordered IDs], profile_ref:{path,sha256}, profile,
               origin_job_id, registration:{module,function},
               limits:{max_calls,max_seconds,max_usd,timeout}}]}
absent: {cell_id, status:"unavailable", reason}
```

The ordinary release has `schema_version:"released-development-v2"`, the exact
scope in `runtime`, `researcher_id`, `sources:{documents,source_manifest,
allowed_source_manifest_hash}`, `items` and `items_sha256`. Items have exactly
`item_id,researcher_id,context,options,option_order_id`; no answers. Keep the
evaluator's entire approved release file and hash. Every supplied profile must
be a complete original `neutral-profile-v1` artifact under f6, with its actual
origin build job and file hash. Job partitions preserve all frozen items once
and in order. The driver independently verifies referenced file bytes.

Declare S/M/L separately as luna/sol/astra public API IDs, not parameter counts
or established capability levels. Pin callable `temperature,max_tokens` for
extraction and consumption separately, and the full backend-enforced settings.
The fixture uses 256 extraction / 128 consumer output-token limits; those are
synthetic and differ from the access probes' 8192. In f6, medium is explicit,
temperature is not sent, implicit caching has TTL 30m, and the pricing version
is `openai-standard-short-context-30m-cache-write-1.25x-2026-11-15`.

Study A needs a separately built profile for each declared extractor/consumer
level. B consumes one exact neutral profile at all consumer levels; no extraction
is repeated. C crosses the already frozen S/L extraction instances. D consumes
the approved fixed raw-evidence condition and its own preregistered judgment
subset/withholding receipts. Missing extraction instances remain absent arms.
Identical executions can serve multiple study arms without extra calls; retain
their aliases in scoring. Profile reuse does not change the study estimand.

Freeze `manifest_sha256`, `digest(bindings)` and `digest(runtime)` externally
before compilation. The coordinator reviews requested ceilings, grants actual
allocation/lease fields, then uses the existing driver's prepare/execute flow.
Role09's preparation does not grant authority or create a scheduler. The runtime
deadline remains `2026-11-15T17:00:00Z`; rebuilding a fixture does not extend it.

Runtime file-byte SHA256 pins are embedded in the fixture. Backend file SHA is
`6ece37e0a623e8d0a7e3b916925532d1c239a0a82269d98cc2d40fb8563a232d`;
its enforced identity uses the distinct canonical-text digest
`77365132d15e60702b1e4b4f3a17bfd0bfeb05f661d9856c8e02e0179af4a6bd`.
Renderer identity is `caee7409e57bf8270b9d2c5c8fd8830e8072d78070a5e2f794e421011ad1a36c`.
Do not substitute one hash convention for another.
