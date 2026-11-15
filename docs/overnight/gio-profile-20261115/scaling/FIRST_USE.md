# First-use fixture validation

This exact fixture contains only opaque synthetic IDs and hashes. It is a declared
comparison packet for audit review, not evidence of actual conditioning. Its code
commit is `2da3325b50def22865080aa3833cdf4783303bd8`.

File SHA256: `8632bc01a21f14d3982688768586cdd8086861c357defe5c4ec235996efee1d4`.
Externally retained manifest digest: `20f3f9d51a917035ee590398ae57b7a9004b68746a50633d758faa6e398213f2`.

Run from the repository root (no calls or data reads):

```python
import json
from pathlib import Path
from autoresearch.taste.overnight.scaling import validate_manifest, result_inventory

path = Path("docs/overnight/gio-profile-20261115/scaling/synthetic-8632bc01a21f14d3982688768586cdd8086861c357defe5c4ec235996efee1d4.json")
manifest = json.loads(path.read_text())
frozen = "20f3f9d51a917035ee590398ae57b7a9004b68746a50633d758faa6e398213f2"
validate_manifest(manifest, expected_manifest_hash=frozen)
inventory = result_inventory(manifest, [], expected_manifest_hash=frozen)
assert len(manifest["arms"]) == 22
assert len(manifest["cells"]) == 18
assert len(inventory) == 22
assert all(row["status"] == "missing-result" for row in inventory)
```

To build a new synthetic plan, import `synthetic_inputs` from
`tests.test_overnight_scaling_manifest` and call `build_manifest(spec, profiles)`.
That creates a new plan, with its own externally retained digest; it does not
replace this fixture or authorize any jobs. Real inputs must come from their
owners after freezing. The evaluator should join assigned cell results by cell ID
and preserve full per-item statuses; no score or label is supplied here.
