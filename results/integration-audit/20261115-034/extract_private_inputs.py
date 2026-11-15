#!/usr/bin/env python3
"""Extract and verify exactly a pinned preservation receipt, in a new private root."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--preservation", type=Path, required=True)
    p.add_argument("--preservation-sha256", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    raw = a.preservation.read_bytes()
    require(sha(raw) == a.preservation_sha256, "receipt hash mismatch")
    receipt = json.loads(raw)
    require(sha(a.archive.read_bytes()) == receipt["archive_sha256"], "archive hash mismatch")
    require(a.archive.stat().st_size == receipt["archive_bytes"], "archive size mismatch")
    require(not a.out.exists() and not a.out.is_symlink(), "output already exists")
    expected = receipt["files"]
    with tarfile.open(a.archive, "r:gz") as archive:
        members = archive.getmembers()
        require(len(members) == len(expected), "unexpected member count")
        require(len({r["archive_member"] for r in expected}) == len(expected), "duplicate member")
        for member, record in zip(members, expected):
            relative = PurePosixPath(member.name)
            require(member.name == record["archive_member"], "member name mismatch")
            require(member.isfile() and member.mode == 0o600, "member type or mode mismatch")
            require(not relative.is_absolute() and ".." not in relative.parts, "unsafe member path")
        a.out.mkdir(mode=0o700)
        for member, record in zip(members, expected):
            target = a.out / member.name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.resolve().relative_to(a.out.resolve())
            raw = archive.extractfile(member).read()
            require(len(raw) == record["size_bytes"] and sha(raw) == record["sha256"], "member byte mismatch")
            with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as f:
                f.write(raw)
            require(target.read_bytes() == raw and stat.S_IMODE(target.stat().st_mode) == 0o600, "extraction mismatch")
    print(json.dumps({"archive_sha256": receipt["archive_sha256"], "extracted_regular_files": len(expected), "root_mode": oct(stat.S_IMODE(a.out.stat().st_mode)), "all_files_mode": "0o600", "all_bytes_match": True}))


if __name__ == "__main__":
    main()
