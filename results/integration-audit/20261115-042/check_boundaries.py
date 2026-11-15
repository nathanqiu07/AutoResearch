#!/usr/bin/env python3
"""Synthetic controls and bounded metadata-only cross-check of the042 proposal."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def sha(b):
    return hashlib.sha256(b).hexdigest()


def collect_hash_strings(x):
    if isinstance(x, str):
        if re.fullmatch(r"[0-9a-f]{64}", x):
            yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from collect_hash_strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from collect_hash_strings(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(); s = a.stage
    results = []
    def ck(name, value):
        results.append({"name": name, "passed": bool(value)})
        assert value, name
    spec = importlib.util.spec_from_file_location("audit42_mapper", s / "map_retention.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    h = "a" * 64
    fixture = {"scalar_source_path": "/synthetic/forbidden.sqlite", "label": "synthetic ignored text", "refs": [{"path": "/synthetic/one.json", "sha256": h}, {"path": "/synthetic/one.json", "sha256": h}]}
    extracted = list(mod.refs(fixture))
    ck("scalar_database_path_not_followed", len(extracted) == 2 and all(x[1] == "/synthetic/one.json" for x in extracted))
    ck("duplicate_occurrences_preserved", {x[0] for x in extracted} == {"/refs/0", "/refs/1"} and len({x[1:] for x in extracted}) == 1)
    ck("json_pointer_escaping", list(mod.refs({"a/b~c": {"path": "/synthetic/a", "sha256": h}}))[0][0] == "/a~1b~0c")
    try:
        list(mod.refs({"path": "/synthetic/a", "sha256": "wrong"}))
    except ValueError:
        rejected = True
    else:
        rejected = False
    ck("malformed_reference_hash_rejected", rejected)
    commands = []
    with tempfile.TemporaryDirectory(prefix="audit42-synthetic-") as td:
        t = Path(td); payload = t / "metadata.json"; payload.write_text("{}\n")
        pins = t / "pins.json"
        pins.write_text(json.dumps({"inputs": [{"role": "completion", "path": str(payload), "sha256": "0" * 64, "size_bytes": 3}]}))
        argv = [sys.executable, str(s / "map_retention.py"), "--pins", str(pins), "--out", str(t / "out")]
        p = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
        ck("wrong_metadata_pin_fails_before_map_output", p.returncode != 0 and "pinned_metadata:completion" in p.stderr and not (t / "out").exists())
        argv = [sys.executable, str(s / "summarize_scope.py"), "--map", str(payload), "--map-sha256", "0" * 64, "--out", str(t / "scope.json")]
        p = subprocess.run(argv, capture_output=True, text=True)
        commands.append({"argv": argv, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
        ck("wrong_map_pin_fails_before_scope_output", p.returncode != 0 and "Wrong retention-map hash" in p.stderr and not (t / "scope.json").exists())
    pins = json.loads((s / "input-pins.json").read_bytes())
    catalog_hash_superset = set(); documents = {}
    for e in pins["inputs"]:
        b = Path(e["path"]).read_bytes()
        ck("input_pin:" + e.get("relative_path", e["role"]), sha(b) == e["sha256"] and len(b) == e["size_bytes"])
        d = json.loads(b)
        if e["role"] == "archive_metadata":
            catalog_hash_superset.update(collect_hash_strings(d))
        else:
            documents[e["role"]] = (e, d)
    # Independent iterative walk does not call mapper.refs.
    expected = Counter()
    for role, (e, d) in documents.items():
        expected[e["path"], e["sha256"]] += 1
        queue = [d]
        while queue:
            v = queue.pop()
            if isinstance(v, list):
                queue.extend(v)
            elif isinstance(v, dict):
                if "path" in v:
                    ck("explicit_reference_shape", set(v) == {"path", "sha256"})
                    expected[v["path"], v["sha256"]] += 1
                queue.extend(v.values())
    m = json.loads((s / "run-02/retention-map.json").read_bytes())["inputs"]
    actual = Counter({(r["path"], r["sha256"]): len(r["logical_occurrences"]) for r in m})
    ck("independent_reference_identity_multiset", expected == actual)
    ck("no_hash_overlap_even_against_catalog_hash_superset", not ({h for _, h in expected} & catalog_hash_superset))
    ck("3022_logical_2822_content_3637_occurrences", len(expected) == 3022 and len({h for _, h in expected}) == 2822 and sum(expected.values()) == 3637)
    by_content = {}
    for row in m:
        obs = row["observed_lstat"]
        ck("regular_file_stat_recorded", obs["kind"] == "regular")
        ck("same_content_size", row["sha256"] not in by_content or by_content[row["sha256"]] == obs["size_bytes"])
        by_content[row["sha256"]] = obs["size_bytes"]
    ck("deduplicated_estimate", sum(by_content.values()) == 108070501)
    scope = json.loads((s / "scope-proposal.json").read_bytes())
    ck("category_logical_count_partition", sum(v["logical_files"] for v in scope["mutually_exclusive_categories"].values()) == len(m))
    ck("category_size_partition", sum(v["deduplicated_bytes_estimate"] for v in scope["mutually_exclusive_categories"].values()) == sum(by_content.values()))
    ck("prefix_logical_count_partition", sum(v["logical_files"] for v in scope["path_prefixes"].values()) == len(m))
    ck("four_context_refs_held", len(scope["hold_before_copy"]) == 4 and any("richer-fit-paired-selection" in r["path"] for r in scope["hold_before_copy"]))
    out = {"schema_version": "profile204-mapper-boundary-checks-v1", "check_counts": {"passed": len(results), "failed": 0}, "synthetic_control_count": 6, "checks": results, "synthetic_commands": commands, "limits": "Cross-check reads only25 pinned metadata inputs and saved map/scope outputs. No payload hashes, runtime imports, raw body copies, active ledger, labels or model calls."}
    with a.out.open("x") as f:
        json.dump(out, f, sort_keys=True, indent=2); f.write("\n")
    print(json.dumps({"check_counts": out["check_counts"], "synthetic_control_count": 6}))


if __name__ == "__main__":
    main()
