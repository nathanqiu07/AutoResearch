"""SynthesizeMe for Marius Hobbhahn (PROTOCOL.md), every stage through common.py's re-pointed Owain modules.

    python3 run.py decisions                      # pre-T paper decisions -> profiles_contrastive/decisions_pre_t.jsonl
    python3 run.py test sources|context|leak|context2|propose|his|same|propose2|pairs|real|taste|confirm|fair|his2|assemble
    python3 run.py select                         # e2_v4's sample rule -> e2_v4/pairs.jsonl, pair_ids.json
    python3 run.py pairs paper|informal STAGE...  # synthme/pairs.py stages (or "all")
    python3 run.py fit paper|informal|all
    python3 run.py arms ARM...                    # M0s NAME S_paper S_inf S_all ANTI0 on the test pairs
    python3 run.py report
"""
import collections
import json
import os
import random
import sys

import common as C


def decisions():
    """profiles_contrastive.build.decisions_pre_t for him: pre-T, `did` set, quote checked with verify.found.
    Unlike Owain's, his own docs are not banned (he is the subject) and OFF_TOPIC_DOCS are left out."""
    verify = C._load("hob_verify", os.path.join(C.TP, "profiles", "_work", "verify.py"))
    v2 = C.test_pipeline().v2
    docs = v2.corpus()
    out, texts, skipped = [], {}, collections.Counter()
    for r in C.read_jsonl(os.path.join(v2.DATA, "extraction", "decisions.jsonl")):
        if not (r.get("date") and r["date"] < C.T and r["doc"] in docs and r.get("did")):
            continue
        if any(k in r["doc"] for k in C.OFF_TOPIC_DOCS):
            skipped[r["doc"]] += 1
            continue
        if r["doc"] not in texts:
            texts[r["doc"]] = verify.norm(docs[r["doc"]][1])
        alts = r.get("alternatives_named")
        alts = alts if isinstance(alts, list) else [alts] if alts else []
        out.append(dict(r, alternatives_named=alts, title=docs[r["doc"]][2].get("title", ""),
                        quote_verified=verify.found(verify.norm(r.get("quote") or ""), texts[r["doc"]])))
    C.write_jsonl(os.path.join(C.HERE, "profiles_contrastive", "decisions_pre_t.jsonl"), out)
    print("pre-T decisions", len(out), "quote verified", sum(r["quote_verified"] for r in out),
          "works", len({C.work_of(r["doc"]) for r in out}), "off-topic skipped", sum(skipped.values()), dict(skipped))


def test(stage):
    v4 = C.test_pipeline()
    if stage == "sources":
        return v4.v2.sources()
    fn = {"context2": lambda: v4.context("2"), "leak2": v4.leak}.get(stage) or getattr(v4, stage)
    fn()


SEED, N_PAIRS = 0, 96


def select():
    """e2_v4/run.py select(): spread N_PAIRS evenly over works, seeded sample within each work."""
    pairs = C.read_jsonl(os.path.join(C.TEST_DIR, "pairs.jsonl"))
    by_work = collections.defaultdict(list)
    for r in pairs:
        by_work[r["work"]].append(r)
    quota, left = {}, N_PAIRS
    for i, w in enumerate(sorted(by_work, key=lambda w: len(by_work[w]))):
        quota[w] = min(len(by_work[w]), left // (len(by_work) - i))
        left -= quota[w]
    rng = random.Random(SEED)
    chosen = [r for w in sorted(by_work) for r in rng.sample(sorted(by_work[w], key=lambda r: r["pair_id"]), quota[w])]
    C.write_jsonl(os.path.join(C.HERE, "e2_v4", "pairs.jsonl"), chosen)
    with open(os.path.join(C.HERE, "e2_v4", "pair_ids.json"), "w") as f:
        json.dump({"seed": SEED, "n": len(chosen), "quota": quota, "pair_ids": [r["pair_id"] for r in chosen]}, f, indent=1)
    print(json.dumps(quota, indent=1), len(chosen))


def arms(names):
    F = C.synthme_fit()
    for a in names:
        F.test(a)
    base = [os.path.join(C.HERE, f"test_{a}.json") for a in F.CACHED]
    if all(map(os.path.exists, base)):  # fit.py's report reads the baselines from e2_v4/results.json
        preds = [x for path in base for x in json.load(open(path))["predictions"]]
        with open(os.path.join(C.HERE, "e2_v4", "results.json"), "w") as f:
            json.dump({"predictions": preds}, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "decisions":
        decisions()
    elif cmd == "test":
        for st in args:
            print("== test", st, flush=True)
            test(st)
    elif cmd == "select":
        select()
    elif cmd == "pairs":
        P = C.synthme_pairs()
        for st in (["context", "leak", "context2", "leak2", "propose", "his", "same", "pairs", "real", "split"]
                   if args[1:] == ["all"] else args[1:]):
            print("==", args[0], st, flush=True)
            P.STAGES[st](args[0])
    elif cmd == "fit":
        C.synthme_fit().fit(args[0])
    elif cmd == "arms":
        arms(args)
    else:
        C.synthme_fit().report()
