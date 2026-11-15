"""Exercise real copier permissions with one synthetic byte and umask 022.

The old copier must fail the all-directories-0700 assertion for nested/leaf/file.
No retained evidence or real archive is read or copied. Output must be fresh.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

PAYLOAD_SHA256 = "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(copier, manifest, source, destination, receipt):
    argv = [sys.executable, "-I", "-B", str(copier), "--manifest", str(manifest),
            "--manifest-sha256", digest(manifest), "--source-root", str(source),
            "--destination", str(destination), "--receipt", str(receipt)]
    completed = subprocess.run(argv, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        preexec_fn=lambda: os.umask(0o022))
    return {"argv": argv, "exit_code": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copier", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source = args.out / "source"
    source.mkdir()
    original = source / "synthetic.bin"
    original.write_bytes(b"a")
    manifest = args.out / "manifest.json"
    manifest.write_text(json.dumps({"source_commit": "synthetic-permission-test",
        "files": [{"source": "synthetic.bin", "destination": "nested/leaf/file",
                   "sha256": PAYLOAD_SHA256, "size_bytes": 1}]}) + "\n")
    destination = args.out / "fresh/parents/checkpoint"
    receipt = args.out / "receipt.json"
    copy = run(args.copier, manifest, source, destination, receipt)
    assert copy["exit_code"] == 0, "Synthetic copy did not complete"
    payload = destination / "nested/leaf/file"
    assert payload.read_bytes() == original.read_bytes() == b"a"
    assert digest(payload) == digest(original) == PAYLOAD_SHA256
    before = {str(p.relative_to(destination)): digest(p) for p in destination.rglob("*") if p.is_file()}
    existing_destination = run(args.copier, manifest, source, destination, args.out / "new-receipt.json")
    assert existing_destination["exit_code"] != 0 and not (args.out / "new-receipt.json").exists()
    assert before == {str(p.relative_to(destination)): digest(p) for p in destination.rglob("*") if p.is_file()}
    existing_receipt = run(args.copier, manifest, source, args.out / "uncreated-checkpoint", receipt)
    assert existing_receipt["exit_code"] != 0 and not (args.out / "uncreated-checkpoint").exists()
    assert digest(original) == PAYLOAD_SHA256
    directories = [args.out / "fresh", args.out / "fresh/parents", destination,
                   destination / "nested", destination / "nested/leaf"]
    modes = {str(p.relative_to(args.out)): oct(stat.S_IMODE(p.stat().st_mode)) for p in directories}
    files_private = all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in destination.rglob("*") if p.is_file())
    result = {"schema_version": "checkpoint-permission-regression-v1", "synthetic_only": True,
        "copier_sha256": digest(args.copier), "probe_sha256": digest(Path(__file__)),
        "child_umask": "0o022", "payload_bytes": 1, "payload_sha256": digest(payload),
        "directory_modes": modes, "all_copied_files_0600": files_private,
        "exclusive_existing_destination_rejected": True, "exclusive_existing_receipt_rejected": True,
        "source_and_existing_destination_unchanged": True,
        "copy": copy, "existing_destination_attempt": existing_destination,
        "existing_receipt_attempt": existing_receipt}
    (args.out / "observations.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("payload_sha256", "directory_modes", "all_copied_files_0600")}, sort_keys=True))
    assert files_private, "Every copied file must be 0600"
    assert all(value == "0o700" for value in modes.values()), "Every newly created intermediate directory must be 0700"


if __name__ == "__main__":
    main()
