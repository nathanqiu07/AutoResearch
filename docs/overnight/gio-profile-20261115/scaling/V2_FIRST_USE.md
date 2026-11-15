# V2 fixture verification

Code commit: `073195b0caf697ab031ebdd3298e9d02cb94ae0b`. All packet leases and authorization sources are null.
The packet fixture is synthetic; its pinned dependency runtime is79874f7.
It does not reuse the later live runtime or a live profile. Absolute input
references point to checksummed synthetic blobs in this checkout. On another
host, regenerate with `driver_fixture` from the test module and retain new
binding/compilation digests; do not silently rewrite a frozen packet.

From the repository root:

```python
import json
from pathlib import Path
from autoresearch.taste.overnight.scaling import compile_driver_packets
from autoresearch.taste.overnight.contracts import digest

fixture = json.loads(Path("docs/overnight/gio-profile-20261115/scaling/driver-fixture-v2-ddc8d974e654be1ce2d7c8b28249e36d920bd60559288619a3785e4f55489031.json").read_text())
compiled = compile_driver_packets(fixture["manifest"], fixture["bindings"],
    runtime=fixture["runtime"], expected_manifest_hash="02e7de86ce6d87e17c5ea3997d6998667b6cb6a81ae021a7d0aeb58e116b01d6",
    expected_bindings_hash="3897d16c91c473a1c83de832934a9035c9a0d6188b7bfba9bcfdac0bc03e2c5f", expected_runtime_hash="cb957917786396ccfdda3f7985f2cdd329836a6a6e8e7a485403e0f69946119c")
assert compiled["compilation_sha256"] == "b69dcce0cfb4e79d8cb3af89374562ade5315f1fd57aa7a9d251e3f17c45c46c"
assert len(compiled["packets"]) == 18
assert compiled["estimates"]["max_attempts"] == 33
assert all(p["packet"]["lease"] is None for p in compiled["packets"])
```

This runs pure preparation checks, makes no calls, and grants no authority.
File checksums and the released pilot/source-group report are in
`docs/overnight/gio-profile-20261115/scaling/verification-v2-0f76533642462df4a8938eda099dbb16dab2b1a7365e808ef73ed130068e15a9.json`.
