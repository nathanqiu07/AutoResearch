"""Round 2 (PROTOCOL.md "Amendment: round 2"): re-abstract every item into one fixed template
(situation / options considered / choice / reason) with a banned-word list = the 40 most discriminative words for
each side of round 1's bag-of-words model + genre words. Then build pairs as in round 1 and run the free gate:
a bag-of-words naive Bayes, trained with the pair's Owain work held out, picking his option.

    python3 r2_abstract.py abstract   -> r2_abstracted.jsonl, r2_leak.json
    python3 r2_abstract.py pairs      -> r2_pairs.jsonl, r2_gate_bow.json
"""
import collections
import json
import math
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import abstract as r1
import pairs as r1pairs
from common import CAPS, WORKERS, call, p, read_jsonl, started, write_jsonl

from autoresearch.llm import extract_json
from autoresearch.taste.textsim import tokens

BATCH, REDO_BATCH, ROUNDS = 12, 12, 2
TOP_K, MIN_DF = 40, 3
N_ARMS = 70  # 5 arms x 2 orders x 70 = 700 sonnet calls
GENRE = """effect effects transfer transferred performance method methods technique behavior behaviour success
benchmark evaluation evaluate evaluator assessment attack defense policy publish publication disclosure release
harm harmful safety risk trait preference phenomenon capability ability task tasks tool tools intervention treatment
mechanism generalize generalise generalization accuracy score metric""".split()
STEMS = ("evaluat", "generali", "transfer", "perform", "publish", "attack", "defen", "benchmark", "capabilit",
         "preferen", "phenomen", "mechanis", "harm")

SYSTEM = r1.SYSTEM
INSTRUCTION = """Below are research decisions made by several different researchers. Rewrite each one into the fixed
template below so that a reader cannot tell what field, topic, paper, organisation or person it comes from, nor what
kind of work it is: an experiment, a new procedure, a measurement suite, a write-up choice, or a decision about what
to share or fund must all read alike. Keep the trade-off that was faced and which way it was decided.

Template, one entry per item:
- "situation": one sentence, at most 30 words: the position the researcher was in when the decision came up.
- "options_considered": two or three short options separated by " / ", including the one taken. If the source names
  no alternative, give the plain opposite of what was done.
- "choice": one sentence, at most 25 words, starting with "Chose", saying which option was taken.
- "reason": one sentence, at most 25 words, giving the stated reason; if none is stated write "No reason stated."

Rules:
- Remove every domain noun and technical term: names of models, systems, datasets, procedures, organisations, people,
  papers and coined terms; and any wording that reveals the area.
- Use only plain generic words such as: the result, the claim, the finding, the check, the comparison, the setup,
  the change, the next step, the question, the work, the variant, the condition, the sample, the system.
- Never use any of these words or any form of them: {banned}.
- Add nothing that is not in the source. Never say who made the decision. Write every item in the same plain style.
{extra}
Return {{"items": [{{"id": ..., "situation": ..., "options_considered": ..., "choice": ..., "reason": ...}}, ...]}}
with one entry per input item, in input order.

ITEMS:
{items}
"""
STRICT = """- Some items list "forbidden_terms": words a previous rewrite kept. Use none of them nor any synonym or form of
  them."""
FIELDS = ("situation", "options_considered", "choice", "reason")


def banned_words():
    """Top TOP_K tokens per side by smoothed document-frequency log ratio on round 1's renderings, plus GENRE."""
    rows = [r for r in read_jsonl(p("abstracted.jsonl")) if not r["leak_final"]]
    df = {True: collections.Counter(), False: collections.Counter()}
    for r in rows:
        df[r["researcher"] == "owain_evans"].update(set(tokens(r["abstract_problem"] + " " + r["abstract_choice"])))
    n = {k: sum(1 for r in rows if (r["researcher"] == "owain_evans") == k) for k in (True, False)}
    lr = {t: math.log((df[True][t] + 1) / (n[True] + 2)) - math.log((df[False][t] + 1) / (n[False] + 2))
          for t in set(df[True]) | set(df[False]) if df[True][t] + df[False][t] >= MIN_DF}
    owain = sorted(lr, key=lambda t: (-lr[t], t))[:TOP_K]
    other = sorted(lr, key=lambda t: (lr[t], t))[:TOP_K]
    return {"owain_side": owain, "other_side": other, "genre": GENRE,
            "all": sorted(set(owain) | set(other) | set(GENRE))}


def text_of(r):
    return " ".join(r[f] for f in FIELDS)


def option(r):
    return (f"Situation: {r['situation']}\nOptions considered: {r['options_considered']}\n"
            f"Choice: {r['choice']}\nReason: {r['reason']}")


def banned_hits(text, banned):
    toks = r1.words(text)
    norm_banned = {r1.norm(b) for b in banned}
    return sorted({t for t in toks if r1.norm(t) in norm_banned or t.startswith(STEMS)})


def render(batch, tag, banned, forbidden=None):
    payload = [{"id": r["id"], "problem": r["problem"], "did": r["did"],
                "alternatives_named": r["alternatives_named"], "stated_reason": r["stated_reason"],
                **({"forbidden_terms": forbidden[r["id"]]} if forbidden else {})} for r in batch]
    prompt = INSTRUCTION.format(banned=", ".join(banned), extra=STRICT if forbidden else "",
                                items=json.dumps(payload, ensure_ascii=False, indent=1))
    out = extract_json(call("sonnet", "r2_abstract", tag, prompt, SYSTEM)) or {}
    ids = {r["id"] for r in batch}
    return {o["id"]: {f: str(o[f]).strip() for f in FIELDS} for o in out.get("items") or []
            if isinstance(o, dict) and o.get("id") in ids and all(o.get(f) for f in FIELDS)}


def run_batches(rows, tag, banned, size, forbidden=None):
    batches = [rows[i:i + size] for i in range(0, len(rows), size)]
    with ThreadPoolExecutor(WORKERS) as ex:
        parts = list(ex.map(lambda ib: render(ib[1], f"{tag}{ib[0]}", banned, forbidden), enumerate(batches)))
    return {k: v for part in parts for k, v in part.items()}


def check(item, stop, banned):
    lk = r1.leaks({"title": item["title"], "abstract_problem": item["situation"] + " " + item["options_considered"],
                   "abstract_choice": item["choice"] + " " + item["reason"]}, stop)
    lk["banned"] = banned_hits(text_of(item), banned)
    lk["flag"] = lk["flag"] or bool(lk["banned"])
    return lk


def abstract_stage():
    rows, _ = r1.load_items()
    by_id = {r["id"]: r for r in rows}
    ban = banned_words()
    stops = {s: r1.stoplist(fm.get("title", "") for fm in r1.corpus_meta(s).values())
             for s in ["owain_evans", *r1.OTHERS]}
    order = rows[:]
    random.Random(0).shuffle(order)
    cur = {k: dict(v, round=0) for k, v in run_batches(order, "r2_r0_", ban["all"], BATCH).items()}
    log = {"banned": ban, "n_items": len(rows), "unrendered_round0": [r["id"] for r in rows if r["id"] not in cur],
           "rounds": []}

    def leaks():
        return {k: check({**by_id[k], **v}, stops[by_id[k]["researcher"]], ban["all"]) for k, v in cur.items()}

    for rnd in range(1, ROUNDS + 1):
        lk = leaks()
        flagged = [k for k, v in lk.items() if v["flag"]]
        log["rounds"].append({"round": rnd - 1, "flagged": len(flagged),
                              "banned_word": sum(1 for k in flagged if lk[k]["banned"]),
                              "title_3gram": sum(1 for k in flagged if lk[k]["title_3grams"]),
                              "2plus_stop_terms": sum(1 for k in flagged if len(lk[k]["stop_terms"]) >= 2),
                              "by_researcher": dict(collections.Counter(by_id[k]["researcher"] for k in flagged))})
        if not flagged:
            break
        room = (CAPS[("sonnet", "r2_abstract")] - started("sonnet", "r2_abstract")) * REDO_BATCH
        log["rounds"][-1]["re_rendered"] = min(room, len(flagged))
        flagged = flagged[:room]  # what the call budget leaves; the rest stay flagged and are excluded
        if not flagged:
            break
        forbidden = {k: sorted(set(lk[k]["stop_terms"]) | set(lk[k]["banned"])
                               | {w for g in lk[k]["title_3grams"] for w in g.split()}) for k in flagged}
        for k, v in run_batches([by_id[k] for k in flagged], f"r2_r{rnd}_", ban["all"], REDO_BATCH, forbidden).items():
            cur[k] = dict(v, round=rnd, forbidden=forbidden[k])
    lk = leaks()
    final = [k for k, v in lk.items() if v["flag"]]
    log["rounds"].append({"round": "final", "flagged": len(final),
                          "by_researcher": dict(collections.Counter(by_id[k]["researcher"] for k in final))})
    log["banned_hits_final"] = dict(collections.Counter(t for v in lk.values() for t in v["banned"]))
    out = [{**{f: by_id[k][f] for f in ("id", "researcher", "point", "work", "title", "date")}, **v,
            "leak": lk[k], "leak_final": lk[k]["flag"]} for k, v in cur.items()]
    write_jsonl(p("r2_abstracted.jsonl"), sorted(out, key=lambda r: r["id"]))
    with open(p("r2_leak.json"), "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in log.items() if k != "banned"}, indent=1))


def bow_gate(pairs, rows):
    """Multinomial naive Bayes (add-one), Owain vs others, trained on every rendering except the pair's two items
    and all of the pair's Owain work; correct if his option scores higher."""
    by_id = {r["id"]: r for r in rows}
    toks = {r["id"]: tokens(text_of(r)) for r in rows}
    out = []
    for pr in pairs:
        train = [r for r in rows if r["id"] not in (pr["his_id"], pr["other_id"])
                 and not (r["researcher"] == "owain_evans" and r["work"] == pr["work"])]
        c = {True: collections.Counter(), False: collections.Counter()}
        for r in train:
            c[r["researcher"] == "owain_evans"].update(toks[r["id"]])
        v = len(set(c[True]) | set(c[False]))
        n = {k: sum(x.values()) for k, x in c.items()}

        def s(i, c=c, n=n, v=v):
            return sum(math.log((c[True][t] + 1) / (n[True] + v)) - math.log((c[False][t] + 1) / (n[False] + v))
                       for t in toks[i])
        out.append({"pair_id": pr["pair_id"], "work": pr["work"], "correct": s(pr["his_id"]) > s(pr["other_id"])})
    assert all(by_id[pr["his_id"]]["researcher"] == "owain_evans" for pr in pairs)
    return out


def pairs_stage():
    rows = [dict(r, abstract_problem=r["situation"]) for r in read_jsonl(p("r2_abstracted.jsonl"))
            if not r["leak_final"]]
    prs = r1pairs.build_pairs(rows, passes=2, rng=random.Random(0), fmt=option)
    arms = r1pairs.trim(prs, N_ARMS, seed=1)
    for r in prs:
        r["in_name"], r["in_arms"] = True, r["pair_id"] in arms
    write_jsonl(p("r2_pairs.jsonl"), prs)
    gate = bow_gate(prs, rows)
    by_work = collections.defaultdict(list)
    for g in gate:
        by_work[g["work"]].append(g["correct"])
    from autoresearch.taste.track_eval import cluster_ci
    acc, lo, hi = cluster_ci(by_work)
    res = {"n_pairs": len(prs), "n_works": len(by_work), "bow_acc": round(acc, 3), "ci90": [round(lo, 3), round(hi, 3)],
           "arms_subset": len(arms), "opponents": dict(collections.Counter(r["opponent"] for r in prs)),
           "per_pair": gate}
    with open(p("r2_gate_bow.json"), "w") as f:
        json.dump(res, f, indent=1)
    print({k: v for k, v in res.items() if k != "per_pair"})


if __name__ == "__main__":
    {"abstract": abstract_stage, "pairs": pairs_stage}[sys.argv[1]]()
