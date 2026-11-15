"""Full dated title list per researcher (all kept docs), input to the extrapolation card."""
import json
import os
import re

ROOT = "/Users/ethancai/Projects/Ongoing/AutoResearch/data/researchers"
W = os.path.dirname(os.path.abspath(__file__))
os.makedirs(W + "/timeline", exist_ok=True)
for slug in ("evan_hubinger", "samuel_bowman", "owain_evans", "ryan_greenblatt", "buck_shlegeris"):
    rows = [json.loads(line) for line in open(f"{ROOT}/{slug}/harvest_manifest.jsonl")]
    lines = []
    for r in rows:
        if r.get("reason") != "kept":
            continue
        head = open(f"{ROOT}/{slug}/corpus/{r['file']}", errors="ignore").read(3000)
        pos = re.search(r"^author_position: (.*)$", head, re.M)
        lines.append((r.get("date") or "undated", r["title"].replace("\n", " ")[:110], pos.group(1) if pos else ""))
    lines.sort()
    with open(f"{W}/timeline/{slug}.txt", "w") as f:
        for d, t, p in lines:
            f.write(f"{d} | {p} | {t}\n")
    print(slug, len(lines))
