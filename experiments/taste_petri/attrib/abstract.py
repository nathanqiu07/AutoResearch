"""Stage 1 (PROTOCOL.md "Items"): every post-T decision of Owain Evans and of Steinhardt, Carlini, Barnes, Marks,
rendered topic-neutral by sonnet, ~10 per call, mixed researchers per batch, one instruction for all.

Leak check: a rendering is flagged when it keeps a word 3-gram of its source doc title (not all stopwords) or
>= 2 distinct terms from its researcher's title stoplist (content words of all that researcher's corpus titles,
minus generic research words). Flagged items are re-rendered with the offending terms forbidden, up to two rounds;
items still flagged after that are marked `leak_final` and left out of pairing.

    python3 experiments/taste_petri/attrib/abstract.py      -> items.jsonl, abstracted.jsonl, leak.json
"""
import collections
import glob
import json
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor

from common import ROOT, TP, WORKERS, call, p, read_jsonl, write_jsonl

from autoresearch.llm import extract_json
from autoresearch.taste import timesplit
from autoresearch.taste.textsim import STOPWORDS

OTHERS = ["jacob_steinhardt", "nicholas_carlini", "elizabeth_barnes", "samuel_marks"]
BATCH, REDO_BATCH = 10, 12  # re-render batches are larger to stay inside the 50-call budget
GENERIC = set("""towards toward evaluating evaluation evaluations evaluate research results result approach case
study studies analysis method methods framework measuring measure understanding can how why what does make makes
less beyond when first part notes thought thoughts update updates one two three four half baked idea ideas agenda
report lessons learned clarifying role good better large small simple simply some many way ways work working
against without within across through toward their other more most really still need needs know think go
going get getting take taking look looking reply response comment comments question questions answer answers
open problem problems paper papers post posts introduction overview review intro note case cases do don
should could would might much like just even very also year years time times day days next last towards
system method intervention treatment condition measurement signal effect baseline control sample variant procedure
dataset data outcome claim hypothesis collaborator audience
ability access accuracy act action actually addition advice already another application applying approaching
arbitrary area argument asking available avoiding background behind belief believe best bound bounded break
building call called cannot change choice clean common comparing complete complex component concept conceptual
concrete confidence confident consideration constant contain content context correct criterion critical critique
current decision description design detailed difference different direction discussion domain early easily
effective efficiency efficient end enough error estimating estimation example exact expected experiment explain
explaining explanation exploring expression fact fail failure far fast feedback feel find finding focu framing
function fundamental future gain general give given goal group hard help high higher identical identifying impact
important improve improved improving increase increasing indicator infer information instance level life light
likely limitation line list little long lower making mapping matter mean meet metric mind move multiple narrow
natural number object objective order partial people perform performance person place possible practical practice
predict predicting prediction preference principle prior probably produce producing progress project proposal
property propertie public quality qualitative quantify quantifying random rate reading real realistic reduce reduced
reducing related relative release reliably require researcher right rigorou risk rule run sample save say scale
second selection sense setting shared short show side similarity single size source state statistic statistical
strong stronger structure studying subjective supporting task technique term test testing third tool trade
tradeoff true turn type uncertainty unknown useful validation value variance version win world worth write yet
yield behavior behavioral
""".split())
WORD = re.compile(r"[a-z0-9]+")

SYSTEM = "You rewrite research decisions as topic-neutral abstractions. Return only the JSON object asked for."
INSTRUCTION = """Below are research decisions made by several different researchers. Rewrite each one so that a reader
cannot tell what field, subfield, topic, paper, organisation or person it comes from, but can still see the research
trade-off that was faced and which way it was decided.

For each item return:
- "abstract_problem": the decision problem as a generic research trade-off (one or two sentences, at most 40 words).
- "abstract_choice": what was chosen, over what alternative when one is given, and the stated reason if any (one or
  two sentences, at most 45 words). Start it with "Chose to".

Rules:
- Remove every domain noun and technical term: names of models, systems, datasets, benchmarks, methods,
  organisations, people, papers, phenomena and coined terms; and any wording that reveals the area (for example
  AI, machine learning, language models, neural networks, training, fine-tuning, prompts, attacks, security,
  privacy, policy, labs, governments, biology).
- Use only generic research vocabulary: system, method, intervention, treatment, condition, measurement, signal,
  effect, baseline, control, sample, variant, procedure, dataset, outcome, claim, hypothesis, collaborator, audience.
- Keep the structure of the trade-off (for example speed vs rigour, breadth vs depth, a bold vs a hedged claim,
  a direct vs an indirect measurement, a natural vs a constructed setting, continue vs stop) and the direction chosen.
- Add nothing that is not in the source: no judgement, praise or new detail. Never say who made the decision.
- Write every item in the same plain style and at a similar length.
{extra}
Return {{"items": [{{"id": ..., "abstract_problem": ..., "abstract_choice": ...}}, ...]}} with one entry per input
item, in input order.

ITEMS:
{items}
"""
STRICT = """
- Some items list "forbidden_terms": words a previous rewrite kept that point to the area or the source. Use none of
  them, nor any synonym or morphological variant of them; describe the thing in generic words instead."""


def corpus_meta(slug):
    """file name -> front matter, for corpus docs with no Hobbhahn in the author list."""
    out = {}
    for path in glob.glob(os.path.join(ROOT, "data", "researchers", slug, "corpus", "*.txt")):
        fm = timesplit.front_matter(path)
        if "hobbhahn" not in fm.get("authors", "").lower():
            out[os.path.basename(path)] = fm
    return out


def norm(word):
    return word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word


def words(text):
    return WORD.findall(str(text).lower())


def stoplist(titles):
    return sorted({norm(w) for t in titles for w in words(t)
                   if len(w) > 2 and not w.isdigit() and w not in STOPWORDS and norm(w) not in GENERIC
                   and w not in GENERIC})


def trigrams(title):
    w = words(title)
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2) if not all(x in STOPWORDS for x in w[i:i + 3])}


def leaks(item, stop):
    text = f"{item['abstract_problem']} {item['abstract_choice']}"
    seq = " ".join(words(text))
    grams = sorted(g for g in trigrams(item["title"]) if f" {g} " in f" {seq} ")
    terms = sorted({norm(w) for w in words(text)} & set(stop))
    return {"title_3grams": grams, "stop_terms": terms, "flag": bool(grams) or len(terms) >= 2}


def load_items():
    rows = []
    owain_meta = corpus_meta("owain_evans")
    for r in read_jsonl(os.path.join(TP, "pairs_v2", "sources.jsonl")):
        rows.append({"id": "owain_evans:" + r["decision_id"], "researcher": "owain_evans", "point": r["point"],
                     "work": r["work"], "title": owain_meta[r["doc"]]["title"], "date": r["date"],
                     **{k: r[k] for k in ("problem", "did", "alternatives_named", "stated_reason")}})
    for r in read_jsonl(os.path.join(TP, "decisions_v2", "all.jsonl")):
        if r["split"] == "post" and r["researcher"] in OTHERS:
            rows.append({"id": f"{r['researcher']}:{r['decision_id']}", "researcher": r["researcher"],
                         "point": r["point"], "work": r["work_id"], "title": r["title"], "date": r["date"],
                         **{k: r[k] for k in ("problem", "did", "alternatives_named", "stated_reason")}})
    dropped = [r["id"] for r in rows if "hobbhahn" in json.dumps(r).lower()]
    rows = [r for r in rows if r["id"] not in dropped]
    assert len({r["id"] for r in rows}) == len(rows), "duplicate decision ids"
    return rows, dropped


def render(batch, tag, forbidden=None):
    payload = [{"id": r["id"], "problem": r["problem"], "did": r["did"],
                "alternatives_named": r["alternatives_named"], "stated_reason": r["stated_reason"],
                **({"forbidden_terms": forbidden[r["id"]]} if forbidden else {})} for r in batch]
    prompt = INSTRUCTION.format(extra=STRICT if forbidden else "", items=json.dumps(payload, ensure_ascii=False,
                                                                                    indent=1))
    out = extract_json(call("sonnet", "abstract", tag, prompt, SYSTEM)) or {}
    got = {}
    for o in out.get("items") or []:
        if isinstance(o, dict) and o.get("id") in {r["id"] for r in batch} and o.get("abstract_problem") \
                and o.get("abstract_choice"):
            got[o["id"]] = {"abstract_problem": o["abstract_problem"].strip(),
                            "abstract_choice": o["abstract_choice"].strip()}
    return got


def run_batches(rows, tag, forbidden=None, size=BATCH):
    batches = [rows[i:i + size] for i in range(0, len(rows), size)]
    with ThreadPoolExecutor(WORKERS) as ex:
        parts = list(ex.map(lambda ib: render(ib[1], f"{tag}{ib[0]}", forbidden), enumerate(batches)))
    return {k: v for part in parts for k, v in part.items()}


def main():
    rows, dropped = load_items()
    write_jsonl(p("items.jsonl"), rows)
    stops = {}
    for slug in ["owain_evans", *OTHERS]:
        stops[slug] = stoplist(fm.get("title", "") for fm in corpus_meta(slug).values())
    order = rows[:]
    random.Random(0).shuffle(order)  # mixed researchers in every batch
    out = run_batches(order, "r0_")
    missing = [r for r in order if r["id"] not in out]
    if missing:  # a batch that lost items: re-ask for those alone, in new batches
        out.update(run_batches(missing, "r0retry_"))
    by_id = {r["id"]: r for r in rows}
    log = {"n_items": len(rows), "per_researcher": dict(collections.Counter(r["researcher"] for r in rows)),
           "dropped_hobbhahn": dropped, "stoplist_sizes": {k: len(v) for k, v in stops.items()},
           "unrendered_round0": [r["id"] for r in rows if r["id"] not in out], "rounds": []}
    cur = {k: dict(v, round=0) for k, v in out.items()}

    def check():
        return {k: leaks({**by_id[k], **v}, stops[by_id[k]["researcher"]]) for k, v in cur.items()}

    for rnd in (1, 2):
        lk = check()
        flagged = [k for k, v in lk.items() if v["flag"]]
        log["rounds"].append({"round": rnd - 1, "flagged": len(flagged),
                              "by_researcher": dict(collections.Counter(by_id[k]["researcher"] for k in flagged)),
                              "with_title_3gram": sum(1 for k in flagged if lk[k]["title_3grams"]),
                              "with_2plus_terms": sum(1 for k in flagged if len(lk[k]["stop_terms"]) >= 2)})
        if not flagged:
            break
        forbidden = {k: sorted(set(lk[k]["stop_terms"]) | {w for g in lk[k]["title_3grams"] for w in g.split()
                                                           if w not in STOPWORDS}) for k in flagged}
        redo = run_batches([by_id[k] for k in flagged], f"r{rnd}_", forbidden, REDO_BATCH)
        for k, v in redo.items():
            cur[k] = dict(v, round=rnd, forbidden=forbidden[k])
    lk = check()
    final_flag = [k for k, v in lk.items() if v["flag"]]
    log["rounds"].append({"round": "final", "flagged": len(final_flag),
                          "by_researcher": dict(collections.Counter(by_id[k]["researcher"] for k in final_flag))})
    log["stop_term_hits_final"] = dict(collections.Counter(t for v in lk.values() for t in v["stop_terms"])
                                       .most_common(30))
    abstracted = [{**{f: by_id[k][f] for f in ("id", "researcher", "point", "work", "title", "date")}, **v,
                   "leak": lk[k], "leak_final": lk[k]["flag"]} for k, v in cur.items()]
    write_jsonl(p("abstracted.jsonl"), sorted(abstracted, key=lambda r: r["id"]))
    log["stoplists"] = stops
    with open(p("leak.json"), "w") as f:
        json.dump(log, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in log.items() if k != "stoplists"}, indent=1))


if __name__ == "__main__":
    main()
