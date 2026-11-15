"""past.dev live smoke test (board task pastdev-live-smoke; PLAN 10).

Writes N tagged facts of the kinds the system uses (OUTCOME, LABEL, BID), waits,
then recalls them by kind and by tag, and reports the recall rate: the share of
written facts that come back intact. The number goes into the README's past.dev
section; a low rate means cross-worker memory is lossy and must be reported so.

Needs PAST_API_KEY (the user supplies it; this script never prints it). Each run
writes only N short facts tagged with a fresh run id. `--local` runs the same
test against the local JSONL store (no network) to check the script itself.

    python3 scripts/pastdev_smoke.py --n 20 --wait 10 --out results/pastdev_smoke
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autoresearch.integrations.shared_memory import LocalSharedMemory, PastDevMemory, format_fact  # noqa: E402

KINDS = ("OUTCOME", "LABEL", "BID")


def run(shared, n: int, wait: float, tag: str) -> dict:
    written = {}
    for k in range(n):
        kind = KINDS[k % len(KINDS)]
        fid = f"{tag}-{k}"
        shared.write("smoke", format_fact(kind, smoke=tag, fid=fid, value=k))
        written[fid] = kind
    t_write = time.time()
    time.sleep(wait)
    found_by_kind, found_by_tag = set(), set()
    for kind in KINDS:
        for f in shared.facts("smoke-reader", f"{kind} smoke={tag}", kind, limit=max(50, 3 * n)):
            if f.get("smoke") == tag and f.get("fid") in written:
                found_by_kind.add(f["fid"])
    for r in shared.recall("smoke-reader", f"smoke={tag}", limit=max(50, 3 * n)):
        for fid in written:
            if f"fid={fid} " in r["content"] + " ":
                found_by_tag.add(fid)
    return {"backend": shared.backend, "tag": tag, "n_written": n, "wait_seconds": wait,
            "recall_by_kind": round(len(found_by_kind) / n, 4), "recall_by_tag": round(len(found_by_tag) / n, 4),
            "recall_any": round(len(found_by_kind | found_by_tag) / n, 4),
            "missing": sorted(set(written) - found_by_kind - found_by_tag),
            "seconds": round(time.time() - t_write, 1), "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--wait", type=float, default=10.0, help="seconds between writing and recalling (ingest lag)")
    ap.add_argument("--out", help="directory for the JSON result")
    ap.add_argument("--local", action="store_true", help="local JSONL store instead of past.dev (script check)")
    args = ap.parse_args(argv)
    tag = "smoke" + uuid.uuid4().hex[:10]
    if args.local:
        shared = LocalSharedMemory(os.path.join(tempfile.mkdtemp(), "smoke.jsonl"))
    else:
        if not os.environ.get("PAST_API_KEY"):
            raise SystemExit("PAST_API_KEY is not set: set it in your shell (or use --local)")
        shared = PastDevMemory(run_tag=tag)
    res = run(shared, args.n, args.wait, tag)
    print(json.dumps({k: v for k, v in res.items() if k != "missing"}, indent=1))
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        p = os.path.join(args.out, f"{res['backend'].replace('.', '_')}_{tag}.json")
        with open(p, "w") as f:
            json.dump(res, f, indent=1)
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
