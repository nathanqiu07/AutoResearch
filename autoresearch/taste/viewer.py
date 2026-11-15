"""Portable, local-only viewer of recorded user-model runs (no inference)."""
from __future__ import annotations

import json
from pathlib import Path


FORMAT = "taste-run-bundle-v1"
MARKER = '<script id="embedded-run" type="application/json">null</script>'


def validate_bundle(bundle):
    """Reject missing or ambiguous provenance before displaying a run."""
    if not isinstance(bundle, dict) or bundle.get("format") != FORMAT:
        raise ValueError("expected taste-run-bundle-v1")
    if bundle.get("mode") not in ("offline_fixture", "live"):
        raise ValueError("bundle must explicitly label offline_fixture or live")
    for key in ("registration", "report"):
        if not isinstance(bundle.get(key), dict):
            raise ValueError("bundle requires %s object" % key)
    examples = bundle.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("bundle requires nonempty examples")
    for example in examples:
        if not isinstance(example, dict):
            raise ValueError("examples must be objects")
        if not all(isinstance(example.get(k), str) for k in ("user_id", "method")):
            raise ValueError("each example needs user_id and method")
        if not isinstance(example.get("history"), list):
            raise ValueError("each example needs history")
        for choice in example["history"] + [example.get("target")]:
            if not isinstance(choice, dict) or any(not isinstance(choice.get(k), str)
                    for k in ("context", "a_text", "b_text")):
                raise ValueError("choice requires context and both option texts")
        if example.get("actual") not in ("a", "b"):
            raise ValueError("example actual must be a or b")
        if example.get("prediction") is not None and not isinstance(example["prediction"], dict):
            raise ValueError("prediction must be an object or null")
        if example.get("artifacts") is not None and not isinstance(example["artifacts"], dict):
            raise ValueError("artifacts must be an object or null")
    json.dumps(bundle, allow_nan=False)
    return bundle


def build_viewer(bundle, output, template=None):
    """Embed a recorded bundle; preserve local file import and teaching content."""
    if isinstance(bundle, (str, Path)):
        bundle = json.loads(Path(bundle).read_text())
    validate_bundle(bundle)
    template = Path(template) if template else Path(__file__).resolve().parents[2] / "docs/user-models/workbench.html"
    page = template.read_text()
    if page.count(MARKER) != 1:
        raise ValueError("viewer template missing its unique empty embedded-run marker")
    payload = json.dumps(bundle, ensure_ascii=False, allow_nan=False)
    payload = payload.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    page = page.replace(MARKER, '<script id="embedded-run" type="application/json">' + payload + '</script>')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Results must remain auditable; never silently overwrite a previous viewer.
    with output.open("x") as stream:
        stream.write(page)
    return output
