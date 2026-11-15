"""Keep grill interviews (taste/grill.py) and the user model they patch in shared memory,
which is past.dev when PAST_API_KEY is set and a local JSONL store otherwise
(integrations/shared_memory.get_shared_memory). Answers given before one overnight run
then steer every later run, on any machine or worker, not only the laptop they were typed on.

Files are stored with taste/usermodel_store's hash-checked, base64-part format, one key per file:
    <slug>/grill/<task>/{meta.json,questions.jsonl,answers.jsonl}
    <slug>/usermodel.json, <slug>/usermodel.base.json
plus a manifest key `<slug>/grill-manifest` listing them, so `pull` knows what exists.

`pull` never loses local work: a .jsonl file is merged (local rows, then remote rows not
already present), and any other file is written only when it is missing locally (or --force).
`push` sends only files whose sha changed since the last push (`<slug>/grill/.synced.json`).

    python3 -m autoresearch.taste.grill_store push    --researcher <slug>
    python3 -m autoresearch.taste.grill_store pull    --researcher <slug>
    # before an overnight run: pull, interview (grill run ... --apply), push
    python3 -m autoresearch.taste.grill_store prerun  --researcher <slug> -- --task eval_awareness [grill run args]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
import tempfile
from typing import Dict, List, Optional

from ..integrations.shared_memory import SharedMemory, get_shared_memory
from . import usermodel_store
from .researcher import DEFAULT_ROOT

SYNCED = ".synced.json"
TOP_FILES = ("usermodel.json", "usermodel.base.json")
GRILL_FILES = ("meta.json", "questions.jsonl", "answers.jsonl")


def _sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def local_files(root: str, slug: str) -> List[str]:
    """Paths relative to <root>/<slug> of every file this store keeps."""
    base = os.path.join(root, slug)
    rels = [f for f in TOP_FILES if os.path.exists(os.path.join(base, f))]
    for name in GRILL_FILES:
        rels += sorted(os.path.relpath(p, base) for p in glob.glob(os.path.join(base, "grill", "*", name)))
    return rels


def _manifest_key(slug: str) -> str:
    return f"{slug}/grill-manifest"


def push(shared: SharedMemory, root: str, slug: str, force: bool = False) -> List[str]:
    """Store changed files and the manifest. Returns the relative paths sent."""
    base = os.path.join(root, slug)
    synced_path = os.path.join(base, "grill", SYNCED)
    synced: Dict[str, str] = json.load(open(synced_path)) if os.path.exists(synced_path) else {}
    rels, sent = local_files(root, slug), []
    for rel in rels:
        path = os.path.join(base, rel)
        sha = _sha(path)
        if force or synced.get(rel) != sha:
            usermodel_store.push(shared, f"{slug}/{rel}", path)
            synced[rel] = sha
            sent.append(rel)
    if sent or force:
        known = sorted(set(rels) | set(pull_manifest(shared, slug)))
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(known, f)
        try:
            usermodel_store.push(shared, _manifest_key(slug), f.name)
        finally:
            os.unlink(f.name)
    os.makedirs(os.path.dirname(synced_path), exist_ok=True)
    with open(synced_path, "w") as f:
        json.dump(synced, f, indent=1)
    return sent


def pull_manifest(shared: SharedMemory, slug: str) -> List[str]:
    with tempfile.TemporaryDirectory() as d:
        dest = os.path.join(d, "manifest.json")
        if usermodel_store.pull(shared, _manifest_key(slug), dest) is None:
            return []
        rels = json.load(open(dest))
    # only paths this store writes, never outside <root>/<slug>
    return [r for r in rels if isinstance(r, str) and not os.path.isabs(r) and ".." not in r.split("/")
            and (r in TOP_FILES or (r.startswith("grill/") and os.path.basename(r) in GRILL_FILES))]


def _merge_jsonl(local: str, remote: str) -> bool:
    """Append remote rows missing from local. Returns whether local changed."""
    with open(local) as f:
        mine = [l.rstrip("\n") for l in f if l.strip()]
    with open(remote) as f:
        theirs = [l.rstrip("\n") for l in f if l.strip()]
    have = set(mine)
    new = [l for l in theirs if l not in have]
    if new:
        with open(local, "a") as f:
            f.write("".join(l + "\n" for l in new))
    return bool(new)


def pull(shared: SharedMemory, root: str, slug: str, force: bool = False) -> List[str]:
    """Bring stored files into <root>/<slug>. Returns the relative paths written or merged."""
    base, changed = os.path.join(root, slug), []
    for rel in pull_manifest(shared, slug):
        dest = os.path.join(base, rel)
        exists = os.path.exists(dest)
        if exists and not (force or rel.endswith(".jsonl")):
            continue
        with tempfile.TemporaryDirectory() as d:
            tmp = os.path.join(d, os.path.basename(rel))
            if usermodel_store.pull(shared, f"{slug}/{rel}", tmp) is None:
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if exists and rel.endswith(".jsonl") and not force:
                if _merge_jsonl(dest, tmp):
                    changed.append(rel)
            else:
                os.replace(tmp, dest)
                changed.append(rel)
    return changed


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    passthrough = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    p = argparse.ArgumentParser(prog="python3 -m autoresearch.taste.grill_store",
                                description="Sync grill interviews and the patched user model with shared memory "
                                            "(past.dev when PAST_API_KEY is set).")
    p.add_argument("action", choices=["push", "pull", "prerun"])
    p.add_argument("--researcher", required=True)
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.add_argument("--shared-path", default="runs/research_memory/shared.jsonl",
                   help="local store used when PAST_API_KEY is not set (where `research` keeps it by default)")
    p.add_argument("--force", action="store_true", help="push everything / overwrite local files on pull")
    a = p.parse_args(argv)
    shared = get_shared_memory(a.shared_path)
    if a.action in ("pull", "prerun"):
        got = pull(shared, a.root, a.researcher, a.force)
        print(f"pulled from {shared.backend}: {got or 'nothing new'}")
    if a.action == "prerun":
        from . import grill
        args = ["run", "--researcher", a.researcher, "--root", a.root] + passthrough
        if "--apply" not in args:
            args.append("--apply")
        grill.main(args)
    if a.action in ("push", "prerun"):
        sent = push(shared, a.root, a.researcher, a.force)
        print(f"pushed to {shared.backend}: {sent or 'nothing changed'}")


if __name__ == "__main__":
    main()
