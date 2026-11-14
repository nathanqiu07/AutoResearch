"""WS B: keep every user model in shared memory, which is past.dev when PAST_API_KEY is set.

The loop loads `data/researchers/<slug>/usermodel.json` (research/advisor.load_user_model).
`push` stores that file in shared memory (integrations/shared_memory.get_shared_memory), and
`pull` rebuilds the file from memory, so a worker or a later run that only has past.dev
gets the same model. Each saved model is stored as numbered parts, one fact each:

    USERMODEL researcher=<slug> sha=<sha256 of the file> saved=<UTC time> part=<i> of=<n>
    <base64 of that part of the file>

Base64 keeps the bytes exact if the store trims or reflows whitespace. `pull` writes the
newest version whose parts are all present and whose bytes match its sha, so a partial
or altered copy is never written.

    python3 -m autoresearch.taste.usermodel_store push --researcher <slug>
    python3 -m autoresearch.taste.usermodel_store pull --researcher <slug>
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, Optional

from ..integrations.shared_memory import SharedMemory, get_shared_memory

AGENT = "taste-store"
# shortcut: past.dev's size limit per fact and whether recall returns whole facts are untested
# (task pastdev-live-smoke); 1500 characters per part is a guess to revisit after that smoke.
PART_CHARS = 1500
# shortcut: one recall of this many rows. A researcher with more stored parts than this can
# miss the newest version; page the recall or prune old versions when that happens.
RECALL_LIMIT = 500
HEADER = re.compile(r"USERMODEL researcher=(\S+) sha=([0-9a-f]{64}) saved=(\S+) part=(\d+) of=(\d+)\n")


def push(shared: SharedMemory, slug: str, path: str) -> str:
    """Store the user model file at `path` under `slug`. Returns the file's sha256."""
    with open(path, "rb") as f:
        body = f.read()
    sha = hashlib.sha256(body).hexdigest()
    saved = datetime.now(timezone.utc).isoformat()
    encoded = base64.b64encode(body).decode()
    parts = [encoded[i:i + PART_CHARS] for i in range(0, len(encoded), PART_CHARS)] or [""]
    for i, part in enumerate(parts, 1):
        shared.write(AGENT, f"USERMODEL researcher={slug} sha={sha} saved={saved} part={i} of={len(parts)}\n{part}",
                     label=f"usermodel:{slug}", metadata={"researcher": slug, "sha256": sha})
    return sha


def pull(shared: SharedMemory, slug: str, dest: str) -> Optional[str]:
    """Write the newest intact copy of `slug`'s user model to `dest` and return its sha256.
    Returns None, and writes nothing, when memory holds no intact copy."""
    versions: Dict[str, dict] = {}
    for row in shared.recall(AGENT, f"USERMODEL researcher={slug}", limit=RECALL_LIMIT):
        m = HEADER.search(row["content"])
        if not m or m.group(1) != slug:
            continue
        sha, saved, part, of = m.group(2), m.group(3), int(m.group(4)), int(m.group(5))
        text = row["content"][m.end():].strip()
        v = versions.setdefault(sha, {"saved": saved, "of": of, "parts": {}})
        # recall can also return excerpts of a fact; the longest copy of a part is the whole one
        if len(text) > len(v["parts"].get(part, "")):
            v["parts"][part] = text
    for sha, v in sorted(versions.items(), key=lambda kv: kv[1]["saved"], reverse=True):
        if len(v["parts"]) != v["of"]:
            continue
        try:
            body = base64.b64decode("".join(v["parts"][i] for i in range(1, v["of"] + 1)), validate=True)
        except (binascii.Error, KeyError):
            continue
        if hashlib.sha256(body).hexdigest() != sha:
            continue
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(body)
        os.replace(tmp, dest)
        return sha
    return None


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m autoresearch.taste.usermodel_store",
                                description="Push a researcher's usermodel.json to shared memory, or pull it back.")
    p.add_argument("action", choices=["push", "pull"])
    p.add_argument("--researcher", required=True, help="slug under --root")
    p.add_argument("--root", default="data/researchers")
    p.add_argument("--shared-path", default="runs/shared_memory.jsonl",
                   help="local store used when PAST_API_KEY is not set (the same default as `research`)")
    a = p.parse_args(argv)
    shared = get_shared_memory(a.shared_path)
    path = os.path.join(a.root, a.researcher, "usermodel.json")
    if a.action == "push":
        print(f"pushed {path} to {shared.backend}: sha256 {push(shared, a.researcher, path)}")
        return
    sha = pull(shared, a.researcher, path)
    if sha is None:
        sys.exit(f"no intact user model for {a.researcher} in {shared.backend}")
    print(f"pulled {a.researcher} from {shared.backend} to {path}: sha256 {sha}")


if __name__ == "__main__":
    main()
