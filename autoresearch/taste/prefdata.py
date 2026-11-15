"""PersonalRewardBench adapter. Preserve released user and conversation splits."""
from __future__ import annotations

import json
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


def _content_key(record):
    c = record.choice
    return digest([c.user_id, c.context, sorted([c.a_text, c.b_text])])


def deduplicate_records(records):
    """Remove only agreeing repeats within one partition; retain an occurrence audit.

    Option order and input order do not determine which record survives. Labels are
    compared by selected text because an A/B reversal changes the label letter.
    """
    records = list(records)
    grouped, identities, conversations = {}, {}, {}
    for record in records:
        content = _content_key(record)
        c = record.choice
        if c.identity in identities and identities[c.identity] != content:
            raise ValueError("preference ID reused for different content")
        identities[c.identity] = content
        boundary = (record.dataset, record.user_split, record.choice_split, record.upstream_split)
        if c.group_id:
            if c.group_id in conversations and conversations[c.group_id] != boundary:
                raise ValueError("conversation crosses a dataset or partition boundary")
            conversations[c.group_id] = boundary
        grouped.setdefault(content, []).append(record)
    unique, removed = [], []
    duplicate_groups = 0
    for content, repeats in sorted(grouped.items()):
        boundaries = {(r.dataset, r.user_split, r.choice_split, r.upstream_split) for r in repeats}
        if len(boundaries) != 1:
            raise ValueError("duplicate preference content crosses a dataset or partition boundary")
        selected = {r.choice.a_text if r.choice.chosen == "a" else r.choice.b_text for r in repeats}
        if len(selected) != 1:
            raise ValueError("duplicate preference content has conflicting chosen text")
        ordered = sorted(repeats, key=lambda r: (r.choice.identity, r.choice.group_id, digest(asdict(r))))
        kept = ordered[0]
        unique.append(kept)
        duplicate_groups += int(len(ordered) > 1)
        for record in ordered[1:]:
            removed.append({"content_digest": content, "kept_id": kept.choice.identity,
                            "removed_id": record.choice.identity,
                            "kept_group_id": kept.choice.group_id,
                            "removed_group_id": record.choice.group_id,
                            "user_id": kept.choice.user_id, "dataset": kept.dataset,
                            "user_split": kept.user_split, "choice_split": kept.choice_split,
                            "upstream_split": kept.upstream_split})
    audit = {"version": 1, "policy": "agreeing_content_within_partition",
             "input_count": len(records), "retained_count": len(unique),
             "removed_count": len(removed), "duplicate_group_count": duplicate_groups,
             "removed": removed}
    return unique, audit


def _validate_deduplication(audit, records):
    if (not isinstance(audit, dict) or audit.get("version") != 1 or
            audit.get("policy") != "agreeing_content_within_partition"):
        raise ValueError("invalid deduplication audit format")
    for key in ("input_count", "retained_count", "removed_count", "duplicate_group_count"):
        if type(audit.get(key)) is not int or audit[key] < 0:
            raise ValueError("deduplication audit counts must be nonnegative integers")
    removed = audit.get("removed")
    if (not isinstance(removed, list) or audit["retained_count"] != len(records) or
            audit["removed_count"] != len(removed) or
            audit["input_count"] != len(records) + len(removed)):
        raise ValueError("deduplication audit counts do not match retained records")
    retained = {r.choice.identity: r for r in records}
    contents = set()
    for entry in removed:
        if not isinstance(entry, dict) or not isinstance(entry.get("kept_id"), str):
            raise ValueError("invalid deduplication audit entry")
        kept = retained.get(entry["kept_id"])
        if kept is None:
            raise ValueError("deduplication audit references a missing retained ID")
        expected = {"content_digest": _content_key(kept), "kept_group_id": kept.choice.group_id,
                    "user_id": kept.choice.user_id, "dataset": kept.dataset,
                    "user_split": kept.user_split, "choice_split": kept.choice_split,
                    "upstream_split": kept.upstream_split}
        if any(entry.get(key) != value for key, value in expected.items()):
            raise ValueError("deduplication audit disagrees with retained content or partition")
        if (not isinstance(entry.get("removed_id"), str) or not entry["removed_id"] or
                not isinstance(entry.get("removed_group_id"), str) or
                (entry["removed_id"] in retained and entry["removed_id"] != entry["kept_id"])):
            raise ValueError("invalid removed occurrence in deduplication audit")
        contents.add(entry["content_digest"])
    if audit["duplicate_group_count"] != len(contents):
        raise ValueError("deduplication audit duplicate-group count does not match removals")


def build_manifest(records, seed=0, deduplication=None, provenance=None):
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
        content = digest([c.user_id, c.context, sorted([c.a_text, c.b_text])])
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
    if deduplication is not None:
        _validate_deduplication(deduplication, records)
        result["deduplication"] = json.loads(json.dumps(deduplication, allow_nan=False))
    if provenance is not None:
        result["provenance"] = json.loads(json.dumps(provenance, allow_nan=False))
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


def download_dataset(dataset, cache_root, seed=0, fetch=None, allow_duplicates=False):
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
        data = (fetch or network)(endpoint, params)
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
    if allow_duplicates:
        unique, audit = deduplicate_records(records)
        build_manifest(unique, seed, audit)
    else:
        build_manifest(records, seed)  # validate before the caller persists any split
    return records
