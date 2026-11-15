#!/usr/bin/env python3
"""Preserve only a hash-pinned audit inventory; never discover additional inputs.

Standard library only. Existing destinations are refused. This script reads no
model service, credentials, ledger, or labels. Its receipt contains metadata only.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked_bytes(path, record):
    require(stat.S_ISREG(path.lstat().st_mode), "input is not a regular file")
    raw = path.read_bytes()
    require(len(raw) == record["size_bytes"], "input size mismatch")
    require(sha(raw) == record["sha256"], "input hash mismatch")
    return raw


def exclusive_json(path, value):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", type=Path, required=True)
    p.add_argument("--inventory-sha256", required=True)
    p.add_argument("--expected-count", type=int, required=True)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--recorded-data-root", type=Path, required=True)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    inventory_raw = a.inventory.read_bytes()
    require(sha(inventory_raw) == a.inventory_sha256, "inventory hash mismatch")
    inventory = json.loads(inventory_raw)
    records = [r for r in inventory["files"] if r["kind"] == "external"]
    require(a.expected_count > 0 and len(records) == a.expected_count, "unexpected input count")
    require(len({r["path"] for r in records}) == len(records), "duplicate input path")
    require(not a.archive.exists() and not a.archive.is_symlink(), "archive already exists")
    require(not a.receipt.exists() and not a.receipt.is_symlink(), "receipt already exists")
    require(a.archive.resolve() != a.receipt.resolve(), "archive and receipt must differ")
    require(a.archive.parent.is_dir(), "archive parent must already exist")
    require(stat.S_IMODE(a.archive.parent.stat().st_mode) == 0o700, "private directory must be mode 0700")
    require(a.receipt.parent.is_dir(), "receipt parent must already exist")
    actual_root = a.data_root.resolve(strict=True)
    recorded_root = a.recorded_data_root
    require(recorded_root.is_absolute(), "recorded root must be absolute")
    bound = []
    for n, record in enumerate(records):
        recorded = Path(record["path"])
        require(recorded.is_absolute() and ".." not in recorded.parts, "invalid recorded path")
        relative = recorded.relative_to(recorded_root)
        require(recorded.suffix == ".json", "only approved JSON inputs accepted")
        actual = (actual_root / relative).resolve(strict=True)
        actual.relative_to(actual_root)
        checked_bytes(actual, record)
        bound.append((actual, dict(record, archive_member="inputs/%06d.json" % n)))
    # Exclusive creation occurs only after every source passes its expected pins.
    with os.fdopen(os.open(a.archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out:
        with gzip.GzipFile(fileobj=out, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for actual, record in bound:
                    raw = checked_bytes(actual, record)
                    member = tarfile.TarInfo(record["archive_member"])
                    member.size = len(raw)
                    member.mode = 0o600
                    member.mtime = 0
                    member.uid = member.gid = 0
                    member.uname = member.gname = ""
                    archive.addfile(member, io.BytesIO(raw))
        out.flush()
        os.fsync(out.fileno())
    require(stat.S_IMODE(a.archive.stat().st_mode) == 0o600, "archive mode mismatch")
    with tarfile.open(a.archive, "r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == len(bound), "archive member count mismatch")
        for member, (actual, record) in zip(members, bound):
            require(member.name == record["archive_member"], "archive member name mismatch")
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and ".." not in name.parts, "unsafe archive member")
            require(member.isfile() and member.mode == 0o600, "archive member type or mode mismatch")
            raw = archive.extractfile(member).read()
            require(len(raw) == record["size_bytes"] and sha(raw) == record["sha256"], "archive byte mismatch")
            checked_bytes(actual, record)
    require(a.inventory.read_bytes() == inventory_raw, "inventory changed during preservation")
    receipt = {
        "schema_version": "private-audit-preservation-v1",
        "archive_path": str(a.archive.resolve()),
        "archive_sha256": sha(a.archive.read_bytes()),
        "archive_bytes": a.archive.stat().st_size,
        "mode_octal": oct(stat.S_IMODE(a.archive.stat().st_mode)),
        "inventory_sha256": a.inventory_sha256,
        "files": [record for _, record in bound],
        "source_bytes_rechecked_unchanged": True,
        "archive_members_rechecked": len(bound),
        "preserver_sha256": sha(Path(__file__).read_bytes()),
        "scope": "Exact named approved private JSON inputs only; no discovery, models, SQLite, credentials, labels, or public raw content.",
    }
    exclusive_json(a.receipt, receipt)
    print(json.dumps({k: receipt[k] for k in ("archive_sha256", "archive_bytes", "mode_octal", "archive_members_rechecked", "source_bytes_rechecked_unchanged")}))


if __name__ == "__main__":
    main()
