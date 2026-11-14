"""Real user messages, the reference the discriminator compares against.

Put JSONL files with a "text" field (one real first user message per line)
in data/real_corpus/. `fetch_hf_rows` pulls a small sample from a public
Hugging Face dataset through the datasets-server rows API, only when you
run the `corpus` command yourself."""
from __future__ import annotations

import glob
import json
import os
import urllib.parse
import urllib.request
from typing import List

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "real_corpus")


def load_corpus(root: str = ROOT, min_chars: int = 40, max_chars: int = 3000) -> List[str]:
    out = []
    for p in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        with open(p) as f:
            for line in f:
                if line.strip():
                    t = json.loads(line).get("text", "")
                    if min_chars <= len(t) <= max_chars:
                        out.append(t)
    return out


def fetch_hf_rows(dataset: str, config: str, split: str, n: int, extract, root: str = ROOT,
                  name: str = "corpus") -> str:
    """extract(row) -> str|None picks the first user message from a row."""
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, f"{name}.jsonl")
    got, offset = 0, 0
    with open(path, "w") as fh:
        while got < n and offset < n * 10:
            q = urllib.parse.urlencode({"dataset": dataset, "config": config, "split": split,
                                        "offset": offset, "length": 100})
            with urllib.request.urlopen(f"https://datasets-server.huggingface.co/rows?{q}", timeout=60) as r:
                rows = json.loads(r.read()).get("rows", [])
            if not rows:
                break
            for row in rows:
                t = extract(row.get("row", {}))
                if t and got < n:
                    fh.write(json.dumps({"text": t}) + "\n")
                    got += 1
            offset += 100
    return path


def wildchat_first_user(row) -> str:
    conv = row.get("conversation") or []
    if row.get("language") not in (None, "English"):
        return ""
    for turn in conv:
        if turn.get("role") == "user":
            return turn.get("content", "")
    return ""
