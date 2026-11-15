"""Stage 2 (PROTOCOL.md "Items"): one pair per Owain decision = his abstracted decision + the nearest (TF-IDF cosine
on abstract_problem) unused, same-D-point decision of a randomly drawn other researcher. A second pairing per
Owain decision (different researcher) is added only if the first pass gives fewer than 80 pairs.

Budget subsets (results.md, deviations): `in_sonnet` keeps N_SONNET pairs and `in_haiku` N_HAIKU of those, each
cut by repeatedly dropping a random pair from the Owain work that has the most, so small works stay whole.

    python3 experiments/taste_petri/attrib/pairs.py      -> pairs.jsonl
"""
import collections
import random

from common import p, read_jsonl, write_jsonl

from autoresearch.taste.textsim import TfIdf, cosine

MIN_PAIRS, N_SONNET, N_HAIKU = 80, 90, 48
QUESTION = ("Two research decisions, each made by a different researcher. "
            "Which one did the researcher described below make?")


def option(r):
    return f"Problem: {r['abstract_problem']}\nDecision: {r['abstract_choice']}"


def trim(pairs, n, seed):
    rng, keep = random.Random(seed), list(pairs)
    while len(keep) > n:
        counts = collections.Counter(r["work"] for r in keep)
        top = max(counts.values())
        biggest = sorted(w for w, c in counts.items() if c == top)
        w = rng.choice(biggest)
        keep.remove(rng.choice([r for r in keep if r["work"] == w]))
    return {r["pair_id"] for r in keep}


def build_pairs(rows, passes, rng, fmt=option):
    tf = TfIdf(r["abstract_problem"] for r in rows)
    vec = {r["id"]: tf.vector(r["abstract_problem"]) for r in rows}
    his = [r for r in rows if r["researcher"] == "owain_evans"]
    others = [r for r in rows if r["researcher"] != "owain_evans"]
    used, pairs = set(), []
    for pas in range(passes):
        order = his[:]
        rng.shuffle(order)
        for h in order:
            taken = {q["opponent"] for q in pairs if q["his_id"] == h["id"]}
            pool = collections.defaultdict(list)
            for o in others:
                if o["point"] == h["point"] and o["id"] not in used and o["researcher"] not in taken:
                    pool[o["researcher"]].append(o)
            if not pool:
                continue
            opp = rng.choice(sorted(pool))
            best = max(pool[opp], key=lambda o: (cosine(vec[h["id"]], vec[o["id"]]), o["id"]))
            used.add(best["id"])
            his_side = rng.choice("ab")
            a, b = (h, best) if his_side == "a" else (best, h)
            pairs.append({"pair_id": f"{h['id']}|{best['id']}", "pass": pas, "work": h["work"],
                          "decision_point": h["point"], "his_id": h["id"], "other_id": best["id"], "opponent": opp,
                          "opponent_work": best["work"], "sim": round(cosine(vec[h["id"]], vec[best["id"]]), 3),
                          "his_text": fmt(h), "other_text": fmt(best),
                          "his_problem": h["abstract_problem"], "other_problem": best["abstract_problem"],
                          "context": QUESTION, "question": "", "a_text": fmt(a), "b_text": fmt(b),
                          "his_side": his_side})
        if len(pairs) >= MIN_PAIRS:
            break
    return pairs


def main():
    rows = [r for r in read_jsonl(p("abstracted.jsonl")) if not r["leak_final"]]
    pairs = build_pairs(rows, passes=2, rng=random.Random(0))
    sonnet = trim(pairs, N_SONNET, seed=1)
    haiku = trim([r for r in pairs if r["pair_id"] in sonnet], N_HAIKU, seed=2)
    for r in pairs:
        r["in_sonnet"], r["in_haiku"] = r["pair_id"] in sonnet, r["pair_id"] in haiku
    write_jsonl(p("pairs.jsonl"), pairs)
    print("pairs", len(pairs), "works", len({r["work"] for r in pairs}),
          "passes used", sorted({r["pass"] for r in pairs}))
    for name, flag in (("all", None), ("sonnet", "in_sonnet"), ("haiku", "in_haiku")):
        sub = [r for r in pairs if flag is None or r[flag]]
        print(name, len(sub), "works", dict(collections.Counter(r["work"] for r in sub)),
              "opponents", dict(collections.Counter(r["opponent"] for r in sub)),
              "points", dict(collections.Counter(r["decision_point"] for r in sub)))
    print("mean sim", round(sum(r["sim"] for r in pairs) / len(pairs), 3))


if __name__ == "__main__":
    main()
