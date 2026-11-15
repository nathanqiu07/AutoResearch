"""Contrastive pre-T profiles of Owain Evans (P0-P4). usage: python3 build.py STAGE

Stages, in order (each reads the previous stage's files and is free to rerun, thanks to the cache):
  map     one sonnet call per pre-T doc: contrasts vs a field default, axis evidence, candidate new axes
  verify  keep only items whose quote is verbatim in the doc -> evidence.jsonl
  reduce  one sonnet call: <=12 distinctive claims, each with a field-default contrary -> claims.json
  gate    10 blind haiku votes per claim (5 per order, agreement.py's prompt) -> gate.jsonl
  axes    one sonnet call: the 14 trade-off axes plus induced axes -> axes.json
  vector  one sonnet call: P4 from the rendered P1 and P2 cards
  render  write P0.md, P1.md, P2.md, P4.md (quotes swapped in from evidence, never typed by a model)
  leak    post-T leakage check -> leak_check.json
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import common
from common import p, read_jsonl, write_jsonl
from autoresearch.taste import agreement, tradeoffs

sys.path.insert(0, p("..", "profiles", "_work"))
from verify import found, norm  # noqa: E402  (read-only reuse of the profiles pipeline's quote check)

MAX_CHARS = 160000
MAX_P4_WORDS = 250
WORKERS = 6
VOTES_PER_ORDER = agreement.VOTES_PER_ORDER


def axes_bank():
    return tradeoffs.load_bank(p("..", "..", "..", tradeoffs.BANK_PATH))


def map_docs():
    return [d for d in common.pre_t_docs() if d["file"] not in common.SKIP_DOCS]


def strip_refs(txt):
    m = re.search(r"\n#+\s*References\s*\n|\nReferences\n", txt)
    return txt[:m.start()] if m and m.start() > len(txt) * 0.4 else txt


def stage_map():
    template = open(p("prompts", "map.txt")).read()
    axes = "\n".join(f'  - {r["axis"]}: 1 = {r["pole_1"]} | 2 = {r["pole_2"]}' for r in axes_bank())

    def one(d):
        prompt = (template.replace("{TITLE}", d["title"]).replace("{DATE}", d["date"]).replace("{YEAR}", d["date"][:4])
                  .replace("{KIND}", d["kind"]).replace("{POS}", d["position"]).replace("{AXES}", axes)
                  + strip_refs(common.doc_text(d["file"]))[:MAX_CHARS])
        try:
            out = common.json_obj(common.call("sonnet", prompt, "You extract research taste. Output only JSON.",
                                              tag="map:" + d["file"][10:50]))
        except (RuntimeError, ValueError) as e:
            print("FAIL", d["file"], e)
            return None
        return dict(out, file=d["file"])

    with ThreadPoolExecutor(WORKERS) as pool:
        maps = [m for m in pool.map(one, map_docs()) if m]
    json.dump(maps, open(p("maps.json"), "w"), indent=1, ensure_ascii=False)
    print(len(maps), "docs mapped")


def stage_verify():
    docs = {d["file"]: d for d in common.pre_t_docs()}
    ev, stats = [], {"kept": 0, "dropped": 0}
    for m in json.load(open(p("maps.json"))):
        d, text = docs[m["file"]], norm(common.doc_text(m["file"]))
        for kind in ("contrasts", "axes", "new_axes"):
            for it in m.get(kind) or []:
                if found(norm(it.get("quote", "")), text):
                    stats["kept"] += 1
                    ev.append(dict(it, kind=kind, doc=d["file"], title=d["title"], date=d["date"],
                                   position=d["position"]))
                else:
                    stats["dropped"] += 1
    prefix = {"contrasts": "C", "axes": "A", "new_axes": "N"}
    count = {}
    for e in ev:
        count[e["kind"]] = count.get(e["kind"], 0) + 1
        e["id"] = f'{prefix[e["kind"]]}{count[e["kind"]]}'
    write_jsonl(p("evidence.jsonl"), ev)
    stats.update(count)
    json.dump(stats, open(p("verify_stats.json"), "w"), indent=1)
    print(stats)


def evidence():
    return {e["id"]: e for e in read_jsonl(p("evidence.jsonl"))}


def stage_reduce():
    items = [e for e in evidence().values() if e["kind"] == "contrasts"]
    lines = [f'{e["id"]} [{e["date"]}; {e["dpoint"]}; distinct={e["distinct"]}; {e["attribution"]}] '
             f'default: {e["default"]} || his choice: {e["choice"]} || why: {e.get("why", "")}' for e in items]
    prompt = open(p("prompts", "reduce_p1.txt")).read().replace("{ITEMS}", "\n".join(lines))
    out = common.json_obj(common.call("sonnet", prompt, "You synthesise research taste. Output only JSON.",
                                      tag="reduce_p1"))
    ids = {e["id"] for e in items}
    for c in out["claims"]:
        c["evidence"] = [i for i in c["evidence"] if i in ids]
    json.dump(out, open(p("claims.json"), "w"), indent=1, ensure_ascii=False)
    print(len(out["claims"]), "claims")


class Haiku:
    """The llm agreement.votes expects: complete() returns the bare JSON reply."""
    label = "claude-cli:haiku"

    def complete(self, prompt, max_tokens=50, temperature=1.0):
        r = common.call("haiku", prompt, "You are a helpful assistant.", tag="gate")
        m = re.search(r"\{[^{}]*\}", r)
        return m.group(0) if m else r


def stage_gate():
    claims = json.load(open(p("claims.json")))["claims"]

    def one(c):
        v = agreement.votes(Haiku(), c["context"], c["his_option"], c["default_option"], k=VOTES_PER_ORDER)
        row = {"key": c["id"], "votes": v}
        s = agreement.share(row)
        return dict(id=c["id"], votes=v, share_his=round(s, 3), lopsided=agreement.lopsided(row),
                    verdict="consensus" if s > agreement.THRESHOLD else
                    "contrarian" if s < 1 - agreement.THRESHOLD else "taste")

    with ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(one, claims))
    write_jsonl(p("gate.jsonl"), rows)
    for r in rows:
        print(r["id"], r["share_his"], r["verdict"])


AXIS_CONTEXT = "An AI-safety researcher is choosing how to approach their next research project."


def stage_gate_axes():
    """The same blind gate on the induced axes (his pole vs the other pole), to label them, not to drop them."""
    ax = json.load(open(p("axes.json")))

    def one(a):
        his, other = (a["pole_a"], a["pole_b"]) if a["his_pole"] == "a" else (a["pole_b"], a["pole_a"])
        v = agreement.votes(Haiku(), AXIS_CONTEXT, his, other, k=VOTES_PER_ORDER)
        s = agreement.share({"key": a["name"], "votes": v})
        return dict(name=a["name"], votes=v, share_his=round(s, 3),
                    verdict="consensus" if s > agreement.THRESHOLD else
                    "contrarian" if s < 1 - agreement.THRESHOLD else "taste")

    with ThreadPoolExecutor(WORKERS) as pool:
        rows = list(pool.map(one, ax["induced"]))
    write_jsonl(p("gate_axes.jsonl"), rows)
    for r in rows:
        print(r["name"], r["share_his"], r["verdict"])


def decisions_pre_t():
    """Pre-T decisions from pre-T, non-Hobbhahn docs, with a check that the quote is verbatim."""
    docs = {d["file"]: d for d in common.pre_t_docs()}
    out, texts = [], {}
    for r in read_jsonl(common.os.path.join(common.DATA, "extraction", "decisions.jsonl")):
        if not (r.get("date") and r["date"] < common.T and r["doc"] in docs and r.get("did")):
            continue
        if r["doc"] not in texts:
            texts[r["doc"]] = norm(common.doc_text(r["doc"]))
        alts = r.get("alternatives_named")
        alts = alts if isinstance(alts, list) else [alts] if alts else []
        out.append(dict(r, alternatives_named=alts, title=docs[r["doc"]]["title"],
                        quote_verified=found(norm(r.get("quote") or ""), texts[r["doc"]])))
    return out


def stage_axes():
    ev = evidence()
    bank = axes_bank()
    axis_lines = []
    for r in bank:
        its = [e for e in ev.values() if e["kind"] == "axes" and e["axis"] == r["axis"]]
        body = "\n".join(f'{e["id"]} [{e["date"]}] pole {e["pole"]} strength {e["strength"]}: "{e["quote"]}"'
                         for e in its)
        axis_lines.append(f'## {r["axis"]} ({r["question"]}) 1 = {r["pole_1"]} | 2 = {r["pole_2"]}\n'
                          + (body or "(no evidence)"))
    new = [f'{e["id"]} [{e["date"]}] {e["name"]}: a = {e["pole_a"]} | b = {e["pole_b"]}; his pole {e["his_pole"]}'
           for e in ev.values() if e["kind"] == "new_axes"]
    dec = [f'{r["decision_id"]} [{r["date"]} {r["point"]}] problem: {r["problem"]} || did: {r["did"]}'
           + (f' || not: {"; ".join(map(str, r["alternatives_named"]))}' if r["alternatives_named"] else "")
           for r in decisions_pre_t() if r["quote_verified"]]
    prompt = (open(p("prompts", "axes.txt")).read().replace("{AXES}", "\n\n".join(axis_lines))
              .replace("{NEW}", "\n".join(new)).replace("{DECISIONS}", "\n".join(dec)))
    out = common.json_obj(common.call("sonnet", prompt, "You synthesise research taste. Output only JSON.",
                                      tag="reduce_axes"))
    json.dump(out, open(p("axes.json"), "w"), indent=1, ensure_ascii=False)
    print(len(out["axes"]), "bank axes,", len(out["induced"]), "induced")


def cite(eid, ev, dec):
    if eid in ev:
        e = ev[eid]
        return f'> "{e["quote"]}" -- `{e["doc"][:-4]}` ({e["date"]}; {e["position"]} author)'
    r = dec[eid]
    return f'> "{r["quote"]}" -- `{r["doc"][:-4]}` ({r["date"]}; decision {eid})'


def render_claims(claims, ev):
    out = []
    for i, c in enumerate(claims, 1):
        out.append(f'{i}. **{c["claim"]}**\n   - Generic default: {c["default_option"]}\n'
                   f'   - His choice: {c["his_option"]}')
        out += ["   " + cite(e, ev, {}) for e in c["evidence"][:2]]
    return "\n".join(out)


def stage_render():
    ev, claims = evidence(), json.load(open(p("claims.json")))["claims"]
    gate = {r["id"]: r for r in read_jsonl(p("gate.jsonl"))}
    for c in claims:
        c["gate"] = gate[c["id"]]
    kept = [c for c in claims if c["gate"]["verdict"] != "consensus"]
    dropped = [c for c in claims if c["gate"]["verdict"] == "consensus"]
    head = ("How this researcher's choices differ from what a typical strong ML-safety researcher would do. "
            "In a blind test, a judge with no information about the researcher did not reliably pick his "
            "choice over the generic default on any of these; on most it picked the default.\n\n")
    open(p("P1.md"), "w").write(head + render_claims(kept, ev) + "\n")
    open(p("P0.md"), "w").write(
        "Research preferences of this researcher, with the generic alternative each one is set against.\n\n"
        + render_claims(dropped, ev) + "\n")

    ax, dec = json.load(open(p("axes.json"))), {r["decision_id"]: r for r in decisions_pre_t()}
    lines = ["Where this researcher sits on research trade-offs (pole, strength, evidence).", ""]
    for a in ax["axes"]:
        if a["pole"] in ("none", None):
            continue
        lines.append(f'- **{a["axis"]}**: {a["position"]} ({a["strength"]})')
        lines += ["  " + cite(e, ev, dec) for e in a["evidence"][:1]]
    lines += ["", "Further axes, induced from his decisions:"]
    for a in ax["induced"]:
        lines.append(f'- **{a["name"]}** ({a["pole_a"]} vs {a["pole_b"]}): {a["position"]} ({a["strength"]})')
        lines += ["  " + cite(e, ev, dec) for e in a["evidence"][:1]]
    open(p("P2.md"), "w").write("\n".join(lines) + "\n")


def stage_vector():
    prompt = (open(p("prompts", "vector.txt")).read().replace("{P1}", open(p("P1.md")).read())
              .replace("{P2}", open(p("P2.md")).read()))
    paras = common.call("sonnet", prompt, "You write concise researcher profiles.", tag="vector").strip().split("\n\n")
    # The prompt orders habits by predictive weight, so an over-long reply is cut from the end.
    while len(" ".join(paras).split()) > MAX_P4_WORDS:
        paras.pop()
    open(p("P4.md"), "w").write("\n\n".join(paras) + "\n")
    print(len(" ".join(paras).split()), "words,", len(paras), "habits")


def _words(text):
    return re.findall(r"[a-z0-9][a-z0-9.\-]*[a-z0-9]|[a-z0-9]", norm(text))


def _ngrams(words, n):
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def stage_leak():
    """Two checks. Provenance: every source the outputs draw on is dated < T and not Hobbhahn's.
    Text: no 8-word run of a post-T doc, and no title 3-gram or bigram that only post-T docs contain,
    appears in any output; the bigram hits are listed for a by-eye read since most are chance."""
    docs = common.corpus_docs()
    ok = {d["file"] for d in common.pre_t_docs()}
    maps = [m["file"] for m in json.load(open(p("maps.json")))]
    ev = read_jsonl(p("evidence.jsonl"))
    bank = read_jsonl(p("decisions_pre_t.jsonl"))
    prov = {"mapped_docs": len(maps), "mapped_not_pre_t": [f for f in maps if f not in ok],
            "evidence_not_pre_t": [e["id"] for e in ev if e["doc"] not in ok or e["date"] >= common.T],
            "bank_not_pre_t": [r["decision_id"] for r in bank if r["doc"] not in ok or r["date"] >= common.T],
            "latest_evidence_date": max(e["date"] for e in ev), "latest_bank_date": max(r["date"] for r in bank)}

    pre_words = [_words(common.doc_text(d["file"])) for d in docs if d["pre_t"]]
    post = [d for d in docs if not d["pre_t"]]
    post_words = [_words(common.doc_text(d["file"])) for d in post]
    pre8 = set().union(*(_ngrams(w, 8) for w in pre_words))
    pre2 = set().union(*(_ngrams(w, 2) for w in pre_words))
    pre3 = set().union(*(_ngrams(w, 3) for w in pre_words))
    post8 = set().union(*(_ngrams(w, 8) for w in post_words)) - pre8
    post2 = set().union(*(_ngrams(w, 2) for w in post_words)) - pre2
    title3 = set().union(*(_ngrams(_words(d["title"]), 3) for d in post)) - pre3
    prompts = " ".join(open(p("prompts", f)).read() for f in sorted(common.os.listdir(p("prompts"))))
    prompt2 = _ngrams(_words(prompts), 2)
    outputs = ["P0.md", "P1.md", "P2.md", "P4.md", "claims.json", "axes.json"]
    text = {}
    for f in outputs:
        w = _words(open(p(f)).read())
        text[f] = {"post_t_8gram_runs": sorted(_ngrams(w, 8) & post8),
                   "post_t_title_3grams": sorted(_ngrams(w, 3) & title3),
                   "post_t_only_bigrams_for_review": sorted((_ngrams(w, 2) & post2) - prompt2)}
    w = _words(" ".join(_text_bank(r) for r in bank))
    text["decisions_pre_t.jsonl"] = {"post_t_8gram_runs": sorted(_ngrams(w, 8) & post8),
                                     "post_t_title_3grams": sorted(_ngrams(w, 3) & title3)}
    out = {"cutoff": common.T, "provenance": prov, "text": text}
    json.dump(out, open(p("leak_check.json"), "w"), indent=1)
    print(json.dumps(prov, indent=1))
    for f, r in text.items():
        print(f, {k: len(v) for k, v in r.items()}, r.get("post_t_only_bigrams_for_review", [])[:40])


def _text_bank(r):
    return " ".join(str(r[k]) for k in ("problem", "did", "stated_reason", "quote")) + " " + " ".join(
        map(str, r["alternatives_named"]))


STAGES = {"leak": stage_leak, "gate_axes": stage_gate_axes, "map": stage_map, "verify": stage_verify, "reduce": stage_reduce, "gate": stage_gate,
          "axes": stage_axes, "render": stage_render, "vector": stage_vector}

if __name__ == "__main__":
    STAGES[sys.argv[1]]()
