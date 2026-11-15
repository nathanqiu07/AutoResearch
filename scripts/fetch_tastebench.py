"""Download Taste-Bench (wenbopan/taste-bench, revision v1.0) and convert it to the JSONL
that autoresearch.taste.tastebench reads.

The dataset is gated on Hugging Face: accept its terms at
https://huggingface.co/datasets/wenbopan/taste-bench while logged in, then make a read
token and either export HF_TOKEN or run `hf auth login`. The token is read, never printed.

    uv run --no-project --with pyarrow python -I scripts/fetch_tastebench.py
    uv run --no-project --with pyarrow python -I scripts/fetch_tastebench.py --subsets research engineering

Every converted row must pass tastebench.check_question, and the research subset must have
112 rows, or nothing is written. Output stays in data/tastebench/, which is gitignored.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autoresearch.taste.tastebench import check_question  # noqa: E402

REPO = "wenbopan/taste-bench"
REVISION = "v1.0"
EXPECTED_ROWS = {"research": 112, "engineering": 390}


def token():
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"].strip()
    path = os.path.join(os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface")), "token")
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    sys.exit("No Hugging Face token: export HF_TOKEN or run `hf auth login` (after accepting the dataset's terms).")


def download(path_in_repo, dest, tok):
    url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{path_in_repo}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(dest + ".part", "wb") as f:
            f.write(r.read())
    except urllib.error.HTTPError as e:
        hint = " (accept the dataset's terms on its Hugging Face page first)" if e.code in (401, 403) else ""
        sys.exit(f"HTTP {e.code} downloading {path_in_repo}{hint}")
    os.replace(dest + ".part", dest)


def convert(parquet_path, subset):
    """Rows of one subset as dicts, after checking every row and the row count."""
    import pyarrow.parquet as pq
    rows = pq.read_table(parquet_path).to_pylist()
    problems = [f"{r.get('id', '?')}: {p}" for r in rows for p in check_question(r)]
    if problems:
        sys.exit(f"{len(problems)} invalid rows in {subset}; first: " + "; ".join(problems[:5]))
    if len(rows) != EXPECTED_ROWS[subset]:
        sys.exit(f"{subset} has {len(rows)} rows, expected {EXPECTED_ROWS[subset]}")
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--subsets", nargs="+", choices=sorted(EXPECTED_ROWS), default=["research"])
    p.add_argument("--out-dir", default="data/tastebench")
    a = p.parse_args(argv)
    tok = token()
    os.makedirs(a.out_dir, exist_ok=True)
    download("export_manifest.json", os.path.join(a.out_dir, "export_manifest.json"), tok)
    for subset in a.subsets:
        parquet = os.path.join(a.out_dir, f"{subset}.parquet")
        download(f"data/{subset}/test-00000-of-00001.parquet", parquet, tok)
        rows = convert(parquet, subset)
        out = os.path.join(a.out_dir, f"{subset}.jsonl")
        with open(out + ".tmp", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        os.replace(out + ".tmp", out)
        print(f"{subset}: {len(rows)} questions -> {out}")


if __name__ == "__main__":
    main()
