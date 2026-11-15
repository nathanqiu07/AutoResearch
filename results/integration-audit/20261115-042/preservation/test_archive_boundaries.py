"""Synthetic bytes only; no real metadata inputs or owner code are loaded."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location("audit42_archive", a.tool)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    checks = []
    def ck(name, ok):
        checks.append({"name": name, "passed": bool(ok)})
        assert ok, name
    def rejects(name, fn):
        try:
            fn()
        except (ValueError, FileExistsError):
            ck(name, True)
        else:
            ck(name, False)
    files = {"b.json": b'{"synthetic":2}\n', "a.json": b'{"synthetic":1}\n'}
    expected = {k: (mod.sha(v), len(v)) for k, v in files.items()}
    first = mod.make_archive(files)
    second = mod.make_archive(dict(reversed(list(files.items()))))
    ck("same_bytes_and_hash_despite_input_order", first == second and mod.sha(first) == mod.sha(second))
    ck("exact_roundtrip_and_normalized_headers", mod.verified_members(first, expected) == files)
    rejects("wrong_member_pin", lambda: mod.verified_members(first, {**expected, "a.json": ("0" * 64, len(files["a.json"]))}))
    rejects("missing_expected_member", lambda: mod.verified_members(mod.make_archive({"a.json": files["a.json"]}), expected))
    rejects("extra_member", lambda: mod.verified_members(mod.make_archive({**files, "extra.json": b"synthetic"}), expected))
    rejects("unsafe_member_on_create", lambda: mod.make_archive({"../outside": b"synthetic"}))
    malicious = io.BytesIO()
    with tarfile.open(fileobj=malicious, mode="w:gz") as tf:
        for _ in range(2):
            t = tarfile.TarInfo("a.json"); t.size = len(files["a.json"]); t.mode = 0o600
            tf.addfile(t, io.BytesIO(files["a.json"]))
    rejects("duplicate_member", lambda: mod.verified_members(malicious.getvalue(), {"a.json": expected["a.json"]}))
    with tempfile.TemporaryDirectory(prefix="audit42-archive-synthetic-") as td:
        path = Path(td) / "payload"
        mod.exclusive_write(path, b"original-synthetic")
        rejects("exclusive_creation_rejects_overwrite", lambda: mod.exclusive_write(path, b"changed-synthetic"))
        ck("original_file_unchanged_and0600", path.read_bytes() == b"original-synthetic" and mod.mode(path) == 0o600)
    with a.out.open("x") as f:
        json.dump({"passed": len(checks), "failed": 0, "checks": checks, "synthetic_only": True, "tool_sha256": mod.sha(a.tool.read_bytes()), "determinism_scope": "Repeated generation with the same Python/compression implementation; no claim of compressed-byte stability across all zlib versions."}, f, sort_keys=True, indent=2); f.write("\n")
    print(json.dumps({"passed": len(checks), "failed": 0, "synthetic_only": True}))


if __name__ == "__main__":
    main()
