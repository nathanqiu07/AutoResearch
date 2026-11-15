"""P3: his k pre-T decisions most similar to a context, by TF-IDF cosine (autoresearch.taste.textsim).

The bank is decisions_pre_t.jsonl, written by `python3 retrieve.py build`: decisions dated before T
from pre-T, non-Hobbhahn corpus docs whose quote is verbatim in the doc. Building reads the corpus;
retrieving reads only the bank."""
import json
import os
import sys
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
from autoresearch.taste.textsim import TfIdf, cosine  # noqa: E402

BANK = os.path.join(HERE, "decisions_pre_t.jsonl")
FIELDS = ("point", "problem", "did", "alternatives_named", "stated_reason", "quote", "date", "doc", "decision_id")


def _text(r):
    return " ".join([r["problem"], r["did"], *map(str, r["alternatives_named"]), r.get("stated_reason") or ""])


@lru_cache(maxsize=1)
def _index():
    with open(BANK) as f:
        bank = [json.loads(line) for line in f if line.strip()]
    tf = TfIdf(_text(r) for r in bank)
    return bank, tf, [tf.vector(_text(r)) for r in bank]


def retrieve(context, k=5):
    """The k most similar decisions, most similar first, each with its cosine score."""
    bank, tf, vecs = _index()
    q = tf.vector(context)
    ranked = sorted(range(len(bank)), key=lambda i: -cosine(q, vecs[i]))[:k]
    return [dict(bank[i], score=round(cosine(q, vecs[i]), 3)) for i in ranked]


def render(rows):
    out = ["Past research decisions by this researcher on similar problems (most similar first):"]
    for i, r in enumerate(rows, 1):
        alts = "; ".join(map(str, r["alternatives_named"])) or "none recorded"
        out.append(f'{i}. [{r["point"]}, {r["date"][:4]}] Problem: {r["problem"]}\n'
                   f'   He did: {r["did"]}\n   Alternatives not taken: {alts}\n'
                   f'   Reason: {r.get("stated_reason") or "not stated"}\n   Quote: "{r["quote"]}"')
    return "\n".join(out)


def build():
    import build as b  # the corpus and pre-T filters live with the profile build
    rows = [{f: r[f] for f in FIELDS} for r in b.decisions_pre_t() if r["quote_verified"]]
    with open(BANK, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "decisions in the bank, latest", max(r["date"] for r in rows))


if __name__ == "__main__":
    build()
