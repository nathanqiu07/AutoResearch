"""PersonalRewardBench adapter. Preserve released user and conversation splits."""
from __future__ import annotations

import json
import time
import urllib.error
from dataclasses import asdict, dataclass
from pathlib import Path

from .usermodel import Choice, digest

DATASETS = {"arena": "MichaelR207/chatbot_arena_personalized_0125",
            "prism": "MichaelR207/prism_personalized_0125"}


@dataclass(frozen=True)
class PreferenceRecord:
    choice: Choice
    dataset: str
    user_split: str
    choice_split: str
    upstream_split: str


def normalize_row(row, dataset, outer_split, seed=0) -> PreferenceRecord:
    if dataset not in DATASETS or outer_split not in ("train", "validation", "test"):
        raise ValueError("unknown dataset or outer user split")
    inner = {"train": "history", "val": "val", "validation": "val", "test": "test"}
    if row.get("split") not in inner:
        raise ValueError("unknown within-user split %r" % row.get("split"))
    context = row.get("context")
    if not isinstance(context, list) or any(not isinstance(t, dict) or
            not isinstance(t.get("role"), str) or not isinstance(t.get("content"), str) for t in context):
        raise ValueError("context must contain role/content turns")
    context = json.dumps([{"role": t["role"], "content": t["content"]} for t in context], ensure_ascii=False)
    user, group = row.get("user_id"), row.get("conversation_id")
    if user is None or group is None:
        raise ValueError("user_id and conversation_id are required")
    chosen, rejected = row.get("chosen", {}).get("content"), row.get("rejected", {}).get("content")
    identity = digest([dataset, str(user), str(group), context, chosen, rejected])
    flip = int(digest([seed, identity])[:8], 16) % 2 == 1
    c = Choice(dataset + ":" + str(user), context, rejected if flip else chosen,
               chosen if flip else rejected, "b" if flip else "a", source="prb_" + dataset,
               example_id=identity, group_id=dataset + ":" + str(user) + ":" + str(group))
    return PreferenceRecord(c, dataset, "test" if outer_split == "test" else "dev",
                            inner[row["split"]], outer_split)


def content_key(choice):
    return digest([choice.user_id, choice.context, sorted([choice.a_text, choice.b_text])])


def drop_exact_repeats(records):
    """Keep one copy of a choice the same person made twice with the same answer.

    PRISM repeats a few rows and conversations verbatim. Scoring both copies would count
    one decision twice. Repeats that disagree on the answer or cross a partition are kept,
    so build_manifest still rejects them.
    """
    groups = {}
    for r in records:
        c = r.choice
        chosen = c.a_text if c.chosen == "a" else c.b_text
        groups.setdefault((content_key(c), r.user_split, r.choice_split, chosen), []).append(r)
    kept, removed = [], []
    for group in groups.values():
        group.sort(key=lambda r: (r.choice.example_id, r.choice.group_id))
        kept.append(group[0])
        removed += [{"example_id": r.choice.example_id, "group_id": r.choice.group_id,
                     "duplicate_of": group[0].choice.example_id} for r in group[1:]]
    return kept, removed


def build_manifest(records, seed=0):
    records = list(records)
    users, seen, groups, content_groups = {}, set(), {}, {}
    for r in records:
        c = r.choice
        if c.identity in seen:
            raise ValueError("duplicate preference example: " + c.identity)
        seen.add(c.identity)
        u = users.setdefault(c.user_id, {"dataset": r.dataset, "partition": r.user_split,
                                        "upstream_split": r.upstream_split,
                                        "history": [], "val": [], "test": []})
        if (u["partition"] != r.user_split or u["upstream_split"] != r.upstream_split or
                u["dataset"] != r.dataset):
            raise ValueError("user crosses dataset/user partition boundary")
        if r.choice_split not in ("history", "val", "test"):
            raise ValueError("invalid choice partition")
        boundary = (r.user_split, r.choice_split)
        if c.group_id in groups and groups[c.group_id] != boundary:
            raise ValueError("conversation crosses choice partition boundary")
        groups[c.group_id] = boundary
        # Catch a repeated query under another conversation ID for the same person.
        content = content_key(c)
        if content in content_groups:
            raise ValueError("duplicate preference content")
        content_groups[content] = boundary
        u[r.choice_split].append(c.identity)
    for u in users.values():
        for split in ("history", "val", "test"):
            u[split].sort()
    source_digest = digest(sorted([asdict(r) for r in records], key=lambda r: r["choice"]["example_id"]))
    result = {"version": 1, "seed": seed, "policy": "upstream_users_and_conversations",
              "sources": DATASETS, "source_digest": source_digest,
              "users": dict(sorted(users.items())), "n_examples": len(seen)}
    result["manifest_id"] = digest(result)
    return result


def write_manifest(path, manifest):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x") as f:
            f.write(text)
    except FileExistsError:
        if json.loads(path.read_text()) != manifest:
            raise ValueError("split manifest already exists with different content")


def save_records(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def load_records(path):
    records = []
    with Path(path).open() as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                d["choice"] = Choice(**d["choice"])
                records.append(PreferenceRecord(**d))
    return records


def download_dataset(dataset, cache_root, seed=0, fetch=None):
    """Fetch public rows with page caching; refuse truncated or incomplete records.

    The older corpus helper discards row truncation metadata and stops by row count;
    preference evaluation needs complete conversations and both partition levels.
    No final labels are sent to a model by this loader.
    """
    import urllib.parse
    import urllib.request
    if dataset not in DATASETS:
        raise ValueError("unknown preference dataset")
    root = Path(cache_root) / dataset
    root.mkdir(parents=True, exist_ok=True)

    def network(endpoint, params):
        url = "https://datasets-server.huggingface.co/" + endpoint + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.load(response)

    def get(endpoint, params):
        path = root / (digest([endpoint, params]) + ".json")
        if path.exists():
            return json.loads(path.read_text())
        for attempt in range(8):
            try:
                data = (fetch or network)(endpoint, params)
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 7:
                    raise
                time.sleep(min(300, 5 * 2 ** attempt))
        with path.open("x") as f:
            json.dump(data, f)
        return data

    splits = get("splits", {"dataset": DATASETS[dataset]})["splits"]
    records = []
    for split in splits:
        offset, total = 0, None
        while total is None or offset < total:
            page = get("rows", {"dataset": DATASETS[dataset], "config": split["config"],
                                "split": split["split"], "offset": offset, "length": 100})
            if total is not None and total != page["num_rows_total"]:
                raise ValueError("dataset row count changed during download")
            total = page["num_rows_total"]
            if not page["rows"] and offset < total:
                raise ValueError("incomplete preference dataset page")
            for entry in page["rows"]:
                if entry.get("truncated_cells"):
                    raise ValueError("truncated preference row; cannot evaluate faithfully")
                records.append(normalize_row(entry["row"], dataset, split["split"], seed))
            offset += len(page["rows"])
    if not records:
        raise ValueError("empty preference dataset")
    return records
