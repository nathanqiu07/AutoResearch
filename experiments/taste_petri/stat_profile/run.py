"""Learned statistical profile: a multinomial naive Bayes trained only on pre-T decisions (Owain Evans vs the
four decisions_v2 researchers), scored on the attrib/ post-T pairs. No model calls.

Tests whether a profile *learned from his past decisions* attributes his later decisions, where the LLM-written
profiles did not beat the bare name. Text views: raw (problem + did + reason), attrib round-1 abstraction,
attrib round-2 template abstraction.
"""
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOKEN = re.compile(r"[a-z]{3,}")
STOP = set("the and for with that this from into their them they was were are has have had not but its our can "
           "which what when then than also more most such each other about over only both will would should could "
           "these those there been being after before while where whether".split())


def read(path):
    return [json.loads(line) for line in open(path) if line.strip()]


def tokens(text):
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


def raw_text(d):
    return " ".join(str(d.get(k) or "") for k in ("problem", "did", "stated_reason"))


def train(docs_by_class):
    counts = {c: Counter(t for d in docs for t in tokens(d)) for c, docs in docs_by_class.items()}
    vocab = set().union(*counts.values())
    totals = {c: sum(cnt.values()) for c, cnt in counts.items()}
    return counts, totals, len(vocab)


def loglik(model, cls, text):
    counts, totals, v = model
    return sum(math.log((counts[cls][t] + 1) / (totals[cls] + v)) for t in tokens(text))


def margin(model, text):
    return loglik(model, "owain", text) - loglik(model, "other", text)


def cluster_ci(rows, n=2000, seed=0):
    by = defaultdict(list)
    for work, ok in rows:
        by[work].append(ok)
    works = list(by)
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        sample = [x for w in (rng.choice(works) for _ in works) for x in by[w]]
        stats.append(sum(sample) / len(sample))
    stats.sort()
    return stats[int(0.05 * n)], stats[int(0.95 * n)]


def main():
    owain_pre = read(ROOT / "profiles_contrastive/decisions_pre_t.jsonl")
    others_pre = [d for d in read(ROOT / "decisions_v2/all.jsonl") if d["split"] == "pre"]
    model = train({"owain": [raw_text(d) for d in owain_pre], "other": [raw_text(d) for d in others_pre]})

    raw = {d["id"]: raw_text(d) for d in read(ROOT / "attrib/items.jsonl")}
    views = {
        "raw": (read(ROOT / "attrib/pairs.jsonl"), lambda p, side: raw[p[f"{side}_id"]]),
        "abstract_r1": (read(ROOT / "attrib/pairs.jsonl"), lambda p, side: p[f"{side}_text"]),
        "template_r2": (read(ROOT / "attrib/r2_pairs.jsonl"), lambda p, side: p[f"{side}_text"]),
    }
    out = {"train": {"owain_pre": len(owain_pre), "others_pre": len(others_pre)}, "views": {}}
    for name, (pairs, text) in views.items():
        rows = [(p["work"], margin(model, text(p, "his")) > margin(model, text(p, "other"))) for p in pairs]
        acc = sum(ok for _, ok in rows) / len(rows)
        lo, hi = cluster_ci(rows)
        out["views"][name] = {"pairs": len(rows), "works": len({w for w, _ in rows}), "acc": round(acc, 3),
                              "ci90": [round(lo, 3), round(hi, 3)]}
    counts, totals, v = model
    lift = {t: math.log((counts["owain"][t] + 1) / (totals["owain"] + v))
            - math.log((counts["other"][t] + 1) / (totals["other"] + v))
            for t in set(counts["owain"]) | set(counts["other"]) if counts["owain"][t] + counts["other"][t] >= 8}
    ranked = sorted(lift, key=lift.get)
    out["top_owain_words"] = ranked[-25:][::-1]
    out["top_other_words"] = ranked[:25]
    (HERE / "results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
