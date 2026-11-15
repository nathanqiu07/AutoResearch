"""Prepare pinned PRISM Parquet using optional pyarrow; runtime stays stdlib-only."""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autoresearch.taste.prefdata import (normalize_row, deduplicate_records, build_manifest,
                                       write_manifest, save_records, load_records)

REVISION = "a03cab5122c397f1307ed092423a05732cc2aa93"
DATASET = "MichaelR207/prism_personalized_0125"


def prepare(cache, output, manifest_path, seed=0):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("Preparation only: install pyarrow with python -m pip install pyarrow") from exc
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    records, sources = [], []
    for split in ("train", "validation", "test"):
        path = cache / (split + ".parquet")
        url = "https://huggingface.co/datasets/%s/resolve/%s/data/%s-00000-of-00001.parquet" % (DATASET, REVISION, split)
        if not path.exists():
            # Publish only complete downloads. Source revision never follows main.
            tmp = path.with_suffix(".part")
            with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.replace(path)
        rows = pq.read_table(path).to_pylist()
        sources.append({"split": split, "url": url, "rows": len(rows),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        records.extend(normalize_row(row, "prism", split, seed) for row in rows)
    records, audit = deduplicate_records(records)
    provenance = {"dataset": DATASET, "revision": REVISION, "files": sources,
                  "reader": "pyarrow", "input_fields": ["user_id", "conversation_id", "context", "chosen", "rejected", "split"]}
    manifest = build_manifest(records, seed, audit, provenance)
    output = Path(output)
    if output.exists() and build_manifest(load_records(output), seed, audit, provenance) != manifest:
        raise ValueError("existing records differ; choose a new output path")
    write_manifest(manifest_path, manifest)
    if not output.exists():
        save_records(output, records)
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", default="runs/prefdata/parquet/prism/" + REVISION)
    p.add_argument("--output", default="runs/prefdata/prism.jsonl")
    p.add_argument("--manifest", default="data/prefdata/prism-splits.json")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    m = prepare(args.cache, args.output, args.manifest, args.seed)
    print(json.dumps({"manifest_id": m["manifest_id"], "n_users": len(m["users"]),
                      "n_examples": m["n_examples"], "removed": m["deduplication"]["removed_count"],
                      "revision": REVISION}, indent=2))


if __name__ == "__main__":
    main()
