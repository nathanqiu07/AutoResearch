"""usage: python3 verify.py [slug ...]  (default: every slug in selection.json)

Check every map-step quote appears verbatim (modulo whitespace / quote-mark style) in its source doc.
Writes evidence/<slug>.jsonl with only the verified items, each tagged with doc id and date."""
import glob
import json
import os
import re
import sys

W = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("—", "-"), ("–", "-"), (" ", " ")):
        s = s.replace(a, b)
    s = re.sub(r"[*_`#>\\]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def found(q, doc):
    if q in doc:
        return True
    parts = [p for p in re.split(r"\s*(?:\.\.\.|…|\[\.\.\.\])\s*", q) if p]
    return len(parts) > 1 and all(len(p) > 15 and p in doc for p in parts)


def main():
    sel = {s["slug"] + "/" + s["file"][:-4]: s for s in json.load(open(W + "/selection.json"))}
    os.makedirs(W + "/evidence", exist_ok=True)
    stats = json.load(open(W + "/verify_stats.json")) if os.path.exists(W + "/verify_stats.json") else {}
    for slug in sys.argv[1:] or sorted({k.split("/")[0] for k in sel}):
        out, ok, bad = [], 0, 0
        for path in sorted(glob.glob(f"{W}/map/{slug}/*.json")):
            s = sel[slug + "/" + os.path.basename(path)[:-5]]
            doc = norm(open(s["path"], errors="ignore").read())
            for it in json.load(open(path)).get("items", []):
                if found(norm(it.get("quote", "")), doc):
                    ok += 1
                    out.append(dict(it, doc_id=s["file"][:-4], title=s["title"], date=s["publishedDate"] or "undated",
                                    author_position=s["author_position"], doc_kind=s["kind"]))
                else:
                    bad += 1
        with open(f"{W}/evidence/{slug}.jsonl", "w") as f:
            for o in out:
                f.write(json.dumps(o) + "\n")
        stats[slug] = dict(docs=len(glob.glob(f"{W}/map/{slug}/*.json")), verified=ok, rejected=bad)
    print(json.dumps(stats, indent=1))
    json.dump(stats, open(W + "/verify_stats.json", "w"), indent=1)


if __name__ == "__main__":
    main()
