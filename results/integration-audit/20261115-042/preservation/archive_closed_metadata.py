#!/usr/bin/env python3
"""Preserve/extract exactly the three approved closed profile204 metadata files.

No referenced path is followed. Preservation reads their bytes without parsing.
Extraction requires an explicitly pinned receipt and never falls back to sources.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import sys

SPECS = {
    "index": ("completion-provenance-index.json", "4681691129419c503c789efff4ad5aa66707b791004465823556844ed9d90461", 1719743),
    "supervisor": ("supervisor-terminal.json", "3646c813067dfce2c805e8de764e0d77c3b824d5ee2d4615304910c34a165076", 1384),
    "ledger": ("profile204-closed-ledger-snapshot-v1.json", "4e35ccbe5d9bcc2cd4e66bd624fc620fc2440cb8840d05667966325362e58960", 168877),
}
PRIVATE_REL = Path("runs/user-model-integration-audit/private")
ARCHIVE_NAME = "profile204-closed-metadata-20261115-v1.tar.gz"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def safe_member(name):
    p = PurePosixPath(name)
    if p.is_absolute() or len(p.parts) != 1 or name != p.name or name in ("", ".", "..") or "\\" in name:
        raise ValueError("Unsafe archive member")


def make_archive(files):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for name, body in sorted(files.items()):
            safe_member(name)
            info = tarfile.TarInfo(name)
            info.size = len(body); info.mode = 0o600; info.mtime = 0
            info.uid = info.gid = 0; info.uname = info.gname = ""
            tf.addfile(info, io.BytesIO(body))
    result = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=result, mtime=0, compresslevel=9) as gz:
        gz.write(raw.getvalue())
    return result.getvalue()


def verified_members(blob, expected):
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        entries = tf.getmembers()
        if [m.name for m in entries] != sorted(expected):
            raise ValueError("Archive member set, order or multiplicity differs")
        result = {}
        for m in entries:
            safe_member(m.name)
            if not m.isfile() or m.mode != 0o600 or m.uid != 0 or m.gid != 0 or m.mtime != 0 or m.uname or m.gname:
                raise ValueError("Unsafe or nondeterministic member metadata")
            body = tf.extractfile(m).read()
            pin, size = expected[m.name]
            if sha(body) != pin or len(body) != size:
                raise ValueError("Member bytes differ from pin")
            result[m.name] = body
        return result


def exclusive_write(path, body):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(body); stream.flush(); os.fsync(stream.fileno())
    if mode(path) != 0o600 or path.read_bytes() != body:
        raise ValueError("Written file bytes or mode differ")


def write_json_new(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, sort_keys=True); stream.write("\n")


def preserve(a):
    repo = a.repo.resolve(strict=True)
    parent = repo
    for part in PRIVATE_REL.parts:
        parent = parent / part
        if parent.is_symlink():
            raise ValueError("Symlink in private archive path")
        if not parent.exists():
            parent.mkdir(mode=0o700)
        if not parent.is_dir():
            raise ValueError("Private path is not a directory")
    if mode(parent) != 0o700:
        raise ValueError("Existing private directory is not0700")
    target = parent / ARCHIVE_NAME
    if target.exists() or target.is_symlink() or a.receipt.exists():
        raise FileExistsError("Archive or receipt already exists; no overwrites")
    argv = ["git", "--no-optional-locks", "-C", str(repo), "check-ignore", "--quiet", "--", str(PRIVATE_REL / ARCHIVE_NAME)]
    check = subprocess.run(argv, capture_output=True, text=True)
    if check.returncode != 0:
        raise ValueError("Target archive is not Git-ignored")
    originals = {}; metadata = []
    for role, (member, pin, size) in SPECS.items():
        p = getattr(a, role)
        if not stat.S_ISREG(p.lstat().st_mode):
            raise ValueError("Source is not a regular nonsymlink file")
        body = p.read_bytes()
        if sha(body) != pin or len(body) != size:
            raise ValueError("Source bytes differ from approved pin: " + role)
        originals[role] = body
        metadata.append({"role": role, "source_path": str(p), "archive_member": member, "sha256": pin, "size_bytes": size, "source_mode_before": oct(mode(p))})
    files = {SPECS[role][0]: body for role, body in originals.items()}
    expected = {member: (pin, size) for member, pin, size in SPECS.values()}
    archive = make_archive(files)
    if verified_members(archive, expected) != files:
        raise ValueError("Prepared archive member bytes differ")
    exclusive_write(target, archive)
    archived = verified_members(target.read_bytes(), expected)
    for entry in metadata:
        p = Path(entry["source_path"]); after = p.read_bytes()
        if after != originals[entry["role"]] or archived[entry["archive_member"]] != after:
            raise ValueError("Source changed or archived bytes differ")
        entry.update({"source_sha256_after": sha(after), "source_size_bytes_after": len(after), "archived_sha256": sha(archived[entry["archive_member"]]), "archived_size_bytes": len(archived[entry["archive_member"]]), "source_mode_after": oct(mode(p)), "source_bytes_unchanged": True, "member_mode": "0o600"})
    receipt = {"schema_version": "profile204-three-closed-snapshot-preservation-v1", "archive_path": str(target), "archive_sha256": sha(archive), "archive_size_bytes": len(archive), "archive_mode": oct(mode(target)), "private_directory_mode": oct(mode(parent)), "members": metadata, "member_count": 3, "uncompressed_input_bytes": sum(len(v) for v in originals.values()), "all_sources_before_after_equal": True, "all_archive_member_bytes_equal_sources": True, "git_ignore_argv": argv, "git_ignore_exit_code": check.returncode, "deterministic_format": {"tar": "USTAR", "member_order": "lexicographic", "uid": 0, "gid": 0, "uname": "", "gname": "", "member_mtime": 0, "member_mode": "0o600", "gzip_mtime": 0, "gzip_filename": "", "compresslevel": 9}, "preserver_sha256": sha(Path(__file__).read_bytes()), "scope": "Only the three released closed metadata snapshots; no referenced raw body, original database, profile, trace, source corpus, selection record or credentials.", "limits": ["Same-machine private retention only; external durable copy is root's separate task.", "Preservation proves exact saved bytes, not provider execution or owner content claims.", "Frozen042 retention proposal and original lstat observations are not regenerated or modified."]}
    write_json_new(a.receipt, receipt)
    print(json.dumps({"archive_sha256": receipt["archive_sha256"], "archive_size_bytes": len(archive), "member_count": 3, "all_sources_before_after_equal": True, "archive_mode": receipt["archive_mode"], "private_directory_mode": receipt["private_directory_mode"]}, sort_keys=True))


def extract(a):
    rb = a.receipt.read_bytes()
    if sha(rb) != a.receipt_sha256:
        raise ValueError("Wrong preservation receipt hash")
    receipt = json.loads(rb)
    expected = {member: (pin, size) for member, pin, size in SPECS.values()}
    if {(r["archive_member"], r["sha256"], r["size_bytes"]) for r in receipt["members"]} != {(m, h, n) for m, (h, n) in expected.items()} or len(receipt["members"]) != 3:
        raise ValueError("Receipt scope is not the approved three files")
    blob = a.archive.read_bytes()
    if sha(blob) != receipt["archive_sha256"] or len(blob) != receipt["archive_size_bytes"]:
        raise ValueError("Wrong archive hash or size")
    files = verified_members(blob, expected)
    a.out.mkdir(mode=0o700, parents=False, exist_ok=False)
    for member, body in files.items():
        exclusive_write(a.out / member, body)
    report = {"schema_version": "profile204-closed-metadata-extraction-v1", "archive_sha256": sha(blob), "receipt_sha256": sha(rb), "destination": str(a.out), "directory_mode": oct(mode(a.out)), "files": [{"member": member, "sha256": sha(body), "size_bytes": len(body), "mode": oct(mode(a.out / member))} for member, body in sorted(files.items())], "original_source_paths_read": False, "referenced_paths_followed": 0, "owner_code_imported": False}
    if a.report:
        write_json_new(a.report, report)
    print(json.dumps(report, sort_keys=True))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preserve")
    for key in ("repo", "index", "supervisor", "ledger", "receipt"):
        p.add_argument("--" + key, type=Path, required=True)
    x = sub.add_parser("extract")
    for key in ("archive", "receipt", "out"):
        x.add_argument("--" + key, type=Path, required=True)
    x.add_argument("--receipt-sha256", required=True)
    x.add_argument("--report", type=Path)
    a = ap.parse_args()
    if a.command == "preserve":
        preserve(a)
    else:
        extract(a)


if __name__ == "__main__":
    main()
