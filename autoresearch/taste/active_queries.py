"""Disagreement-driven questions (PLAN 10, past.dev item 2): ask the researcher about the
decisions the user model is least sure of first, and remember every time they disagree.

Three parts:

  Disagreements  Every labelled decision where the researcher's choice differs from the user
                 model's is stored as a DISAGREE fact (integrations/living.py's kind and fields,
                 plus by=researcher and label=<option text>), next to a LABEL fact with the same
                 key, so living.pending does not ask about it again. The loop's own overrides keep
                 coming from research/decisions.DecisionLog (by is absent there). Facts go to
                 past.dev when PAST_API_KEY is set, else the local JSONL store.
  Queue          Unlabelled D1-D6 records from runs' decisions.jsonl, ranked by the user model's
                 uncertainty with a diversity term (greedy maximal marginal relevance over TF-IDF
                 of context + options), written as JSONL whose `id`s are trackp's label item ids.
                 `python3 -m autoresearch.taste label --queue Q` asks them in queue order; one
                 item can also be answered with `trackp record --id <id> --decisions <file>`.
  Simulation     On already-labelled pairs, learning curves (held-out accuracy vs labels) for
                 uncertainty-ordered and random-ordered labelling over several seeds, offline,
                 with a stdlib Bradley-Terry learner. Written as JSON and markdown.

Uncertainty, in order of preference:
  committee     several user models (or bootstrap refits): entropy of the mean distribution plus
                the Jensen-Shannon disagreement between members, each divided by log(k)
  model         one model's predicted distribution: its normalised entropy
  logged        the record's own user_model_choice/confidence, the remaining mass spread evenly
                over the other options; the confidence is Platt-calibrated on the decisions the
                researcher already labelled when at least MIN_CALIBRATION of them (with both
                outcomes) exist
  none          no user model was consulted: maximal uncertainty (1.0)

    python3 -m autoresearch.taste.active_queries queue --researcher <slug> [--decisions runs/*/decisions.jsonl] --out queue.jsonl
    python3 -m autoresearch.taste label --researcher <slug> --queue queue.jsonl
    python3 -m autoresearch.taste.active_queries disagreements --researcher <slug>
    python3 -m autoresearch.taste.active_queries simulate --choices data/researchers/demo_realist/choices.jsonl --out results/taste/active_queries/demo_realist
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import sys
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..integrations import living
from ..integrations.shared_memory import format_fact, get_shared_memory
from ..research.decisions import code_version, validate_record
from . import trackp
from .researcher import DEFAULT_ROOT
from .textsim import TfIdf, cosine, normalise, tokens

QUEUE_VERSION = "active-queue-v1"
MIN_CALIBRATION = 8
DEFAULT_DIVERSITY = 0.3
LABELLER = "labeller"


# ---- uncertainty -----------------------------------------------------------------

def entropy(p: Sequence[float]) -> float:
    """Entropy divided by log(k), so 0 is certain and 1 is uniform for any number of options."""
    k = len(p)
    if k < 2:
        return 0.0
    return -sum(x * math.log(x) for x in p if x > 0) / math.log(k)


def committee_uncertainty(dists: Sequence[Sequence[float]]) -> Tuple[float, float]:
    """(entropy of the mean distribution, Jensen-Shannon disagreement), both normalised by log(k).
    The score used is their sum: a member-level split counts on top of shared indecision."""
    k = len(dists[0])
    mean = [sum(d[i] for d in dists) / len(dists) for i in range(k)]
    total = entropy(mean)
    return total, max(0.0, total - sum(entropy(d) for d in dists) / len(dists))


def logged_distribution(rec: dict, calibrate: Optional[Callable[[float], float]] = None) -> Optional[List[float]]:
    """The record's own user-model distribution: confidence on its pick, the rest spread evenly."""
    umc, conf, k = rec.get("user_model_choice"), rec.get("user_model_confidence"), len(rec["options"])
    if umc is None or conf is None:
        return None
    conf = calibrate(float(conf)) if calibrate else float(conf)
    conf = min(1.0, max(0.0, conf))
    rest = (1.0 - conf) / (k - 1) if k > 1 else 0.0
    return [conf if i == umc else rest for i in range(k)]


class Platt:
    """P(the user model's pick is the researcher's) = sigmoid(a * logit(conf) + b), fitted by
    gradient descent on labelled decisions. Identity until it has enough data of both outcomes."""

    def __init__(self, pairs: Sequence[Tuple[float, bool]] = (), l2: float = 0.01, epochs: int = 500):
        self.a, self.b, self.fitted = 1.0, 0.0, False
        ys = {y for _, y in pairs}
        if len(pairs) >= MIN_CALIBRATION and len(ys) == 2:
            xs = [(self._logit(c), 1.0 if y else 0.0) for c, y in pairs]
            for _ in range(epochs):
                ga = l2 * (self.a - 1.0)
                gb = 0.0
                for x, y in xs:
                    err = self._sig(self.a * x + self.b) - y
                    ga += err * x / len(xs)
                    gb += err / len(xs)
                self.a -= 0.5 * ga
                self.b -= 0.5 * gb
            self.fitted = True

    @staticmethod
    def _logit(c: float) -> float:
        c = min(1 - 1e-4, max(1e-4, c))
        return math.log(c / (1 - c))

    @staticmethod
    def _sig(z: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))

    def __call__(self, conf: float) -> float:
        return self._sig(self.a * self._logit(conf) + self.b) if self.fitted else conf


def score_record(rec: dict, models: Sequence = (), calibrate: Optional[Callable] = None) -> dict:
    """{"uncertainty", "source", "disagreement"?} for one decision record."""
    if models:
        dists = [list(m.predict(rec["context"], rec["options"]).probabilities) for m in models]
        if len(dists) > 1:
            total, js = committee_uncertainty(dists)
            return {"uncertainty": total + js, "disagreement": js, "source": "committee"}
        return {"uncertainty": entropy(dists[0]), "source": "model"}
    dist = logged_distribution(rec, calibrate)
    if dist is None:
        return {"uncertainty": 1.0, "source": "none"}
    return {"uncertainty": entropy(dist), "source": "logged_calibrated" if getattr(calibrate, "fitted", False)
            else "logged"}


# ---- diversity -------------------------------------------------------------------

def mmr_order(scores: Sequence[float], vectors: Sequence[dict], diversity: float = DEFAULT_DIVERSITY,
              limit: Optional[int] = None) -> List[Tuple[int, float]]:
    """Greedy maximal marginal relevance: [(index, max similarity to the items already picked)].
    Each step picks argmax (1 - diversity) * score - diversity * max_sim; scores are rescaled to
    [0, 1] first so the two terms share a scale."""
    n = len(scores)
    lo, hi = (min(scores), max(scores)) if n else (0.0, 0.0)
    norm = [(s - lo) / (hi - lo) if hi > lo else 1.0 for s in scores]
    left, out = set(range(n)), []
    best_sim = [0.0] * n
    while left and (limit is None or len(out) < limit):
        i = max(left, key=lambda j: ((1 - diversity) * norm[j] - diversity * best_sim[j], -j))
        out.append((i, best_sim[i]))
        left.discard(i)
        for j in left:
            best_sim[j] = max(best_sim[j], cosine(vectors[i], vectors[j]))
    return out


# ---- decisions, labels and facts ----------------------------------------------------

def decision_index(paths: Sequence[str]) -> Dict[str, Tuple[str, dict]]:
    """{trackp label key "<run_id>:<line>": (path, record)} for every valid record."""
    out = {}
    for path in paths:
        for i, rec in enumerate(trackp._read(path)):
            if not validate_record(rec):   # first file wins for a repeated key, as in trackp
                out.setdefault(f"{rec.get('run_id')}:{i}", (path, rec))
    return out


def fact_key(rec: dict) -> str:
    """The key living.write_disagree gives this decision, so LABEL, DISAGREE and the loop's own
    DISAGREE fact for one decision share it."""
    return living._key(rec["run_id"], str(rec["iter"]), rec["point"], rec["context"])


def write_label_facts(shared, slug: str, rec: dict, label: int) -> Optional[str]:
    """A LABEL fact for one answered decision and, when the user model picked otherwise, a DISAGREE
    fact (by=researcher). Returns the key when a DISAGREE was written."""
    key = fact_key(rec)
    opts = rec["options"]
    umc = rec.get("user_model_choice")
    other = umc if umc is not None and umc != label else next(j for j in range(len(opts)) if j != label)
    # The stored pair's a/b order is set by the key, so the chosen text isn't always a.
    a, b, chosen = (label, other, "a") if int(key, 16) % 2 == 0 else (other, label, "b")
    living.write_label(shared, slug, rec["context"], opts[a], opts[b], chosen, point=rec["point"],
                       run=rec["run_id"], source="active_query", key=key)
    if umc is None or umc == label:
        return None
    conf = rec.get("user_model_confidence")
    shared.write(LABELLER, format_fact(
        "DISAGREE", key=key, run=rec["run_id"], arm=rec.get("arm") or "none", iter=rec["iter"], point=rec["point"],
        confidence=round(conf, 3) if conf is not None else "none", context=living._clean(rec["context"]),
        action=living._clean(opts[label]), taste=living._clean(opts[umc]), by="researcher",
        label=living._clean(opts[label])))
    return key


def researcher_disagreements(shared) -> set:
    return {f.get("key") for f in shared.facts("living", "DISAGREE by=researcher", "DISAGREE",
                                               limit=living.RECALL_LIMIT) if f.get("by") == "researcher"}


def sync_disagreements(shared, root: str, slug: str, decision_paths: Sequence[str]) -> dict:
    """Write the LABEL fact, and the DISAGREE fact when the user model picked otherwise, for every
    answer in labels.jsonl that shared memory lacks (answers from trackp's own `label`/`record`
    included). Safe to rerun: facts already present are not written again."""
    index = decision_index(decision_paths)
    have_dis = researcher_disagreements(shared)
    have_label = {f.get("key") for f in living.labels(shared, slug)}
    report = {"labels": 0, "disagreements": 0, "written": 0, "missing_record": 0}
    for row in trackp._read(os.path.join(root, slug, trackp.LABELS)):
        report["labels"] += 1
        hit = index.get(row["key"])
        if hit is None:
            report["missing_record"] += 1
            continue
        rec, key = hit[1], fact_key(hit[1])
        umc = rec.get("user_model_choice")
        disagrees = umc is not None and umc != row["label"]
        report["disagreements"] += disagrees
        if key not in have_label or (disagrees and key not in have_dis):
            write_label_facts(shared, slug, rec, row["label"])
            have_label.add(key)
            have_dis |= {key} if disagrees else set()
            report["written"] += 1
    return report


def calibrator(root: str, slug: str, index: Dict[str, Tuple[str, dict]]) -> Platt:
    """Platt scaling of logged confidences on the decisions this researcher already labelled."""
    pairs = []
    for row in trackp._read(os.path.join(root, slug, trackp.LABELS)):
        hit = index.get(row["key"])
        if hit and hit[1].get("user_model_choice") is not None and hit[1].get("user_model_confidence") is not None:
            pairs.append((float(hit[1]["user_model_confidence"]), hit[1]["user_model_choice"] == row["label"]))
    return Platt(pairs)


def _text(rec: dict) -> str:
    return rec["context"] + " " + " ".join(rec["options"])


def build_queue(root: str, slug: str, decision_paths: Sequence[str], models: Sequence = (),
                diversity: float = DEFAULT_DIVERSITY, limit: Optional[int] = None, warn: Callable = print) -> List[dict]:
    """Ranked label queue rows for the unlabelled records (trackp.pending_items decides which)."""
    items = trackp.pending_items(root, slug, ("label",), list(decision_paths), warn=warn)
    index = decision_index(decision_paths)
    cal = None if models else calibrator(root, slug, index)
    recs = [it["_src"] for it in items]
    scored = [score_record(r, models, cal) for r in recs]
    tfidf = TfIdf(_text(r) for r in recs)
    order = mmr_order([s["uncertainty"] for s in scored], [tfidf.vector(_text(r)) for r in recs], diversity, limit)
    out = []
    for rank, (i, sim) in enumerate(order, 1):
        r, s = recs[i], scored[i]
        out.append({"id": items[i]["id"], "rank": rank, "uncertainty": round(s["uncertainty"], 4),
                    "uncertainty_source": s["source"], "disagreement": round(s.get("disagreement", 0.0), 4),
                    "max_similarity_to_earlier": round(sim, 4), "point": r["point"], "run_id": r["run_id"],
                    "iter": r["iter"], "decisions": index[r["key"]][0], "fact_key": fact_key(r),
                    "diversity": diversity, "calibrated": bool(cal and cal.fitted), "queue_version": QUEUE_VERSION})
    return out


def read_queue(path: str) -> List[dict]:
    rows = trackp._read(path)
    bad = [r.get("id") for r in rows if not str(r.get("id", "")).startswith("label:") or "decisions" not in r]
    if bad:
        raise ValueError(f"{path} is not an active_queries queue (bad rows: {bad[:3]})")
    return sorted(rows, key=lambda r: r["rank"])


def label_from_queue(root: str, slug: str, queue_path: str, shared=None, ask: Optional[Callable] = None,
                     say: Optional[Callable] = None, limit: Optional[int] = None) -> dict:
    """Ask the queue's still-pending items in queue order (trackp's terminal loop and labels.jsonl),
    then write LABEL/DISAGREE facts for the new answers. ask/say default to input/print."""
    ask, say = ask or input, say or print
    queue = read_queue(queue_path)
    paths = sorted({r["decisions"] for r in queue})
    pending = {it["id"]: it for it in trackp.pending_items(root, slug, ("label",), paths, warn=say)}
    items = [pending[r["id"]] for r in queue if r["id"] in pending]
    n = trackp.ask_items(root, slug, items, ask=ask, say=say, limit=limit)
    report = {"answered": n, "queued": len(queue), "still_pending": len(items) - n}
    if shared is not None:
        report["facts"] = sync_disagreements(shared, root, slug, paths)
        report["memory"] = shared.backend
    return report


# ---- simulation: uncertainty vs random labelling ------------------------------------

def _features(row: dict) -> Tuple[dict, dict, str]:
    """(features of a, of b, text) for a feature-dict choice ({"a": {...}, "b": {...}}) or a text
    Choice row ({"a_text", "b_text"}: unit-normalised token counts)."""
    if isinstance(row.get("a"), dict):
        fa, fb = {k: float(v) for k, v in row["a"].items()}, {k: float(v) for k, v in row["b"].items()}
        return fa, fb, " ".join(f"{k}" for k, v in sorted(fa.items()) if v) + " vs " + " ".join(
            f"{k}" for k, v in sorted(fb.items()) if v)

    def bag(text):
        v = {}
        for t in tokens(text):
            v[t] = v.get(t, 0.0) + 1.0
        return normalise(v)
    return bag(row["a_text"]), bag(row["b_text"]), f"{row.get('context', '')} {row['a_text']} {row['b_text']}"


def load_pool(path: str) -> List[dict]:
    """Labelled pairs as {x: a-minus-b features, y: 1 if a chosen, group, text}."""
    out = []
    for i, row in enumerate(trackp._read(path)):
        fa, fb, text = _features(row)
        x = {k: v for k in set(fa) | set(fb) for v in [fa.get(k, 0.0) - fb.get(k, 0.0)] if v}
        # Diversity space: for feature rows the trade-off itself (signed a-minus-b direction), for
        # text rows TF-IDF of the text (simulate_seed fits it on the training pool).
        out.append({"x": x, "y": 1.0 if row["chosen"] == "a" else 0.0,
                    "group": row.get("group_id") or row.get("example_id") or str(i), "text": text,
                    "vec": normalise(x) if isinstance(row.get("a"), dict) else None})
    return out


class BradleyTerry:
    """Logistic regression on a-minus-b features with an L2 penalty (taste/choices.py's model, over
    any sparse feature set). p(a) = sigmoid(w . x)."""

    def __init__(self, l2: float = 0.5, lr: float = 0.5, epochs: int = 200):
        self.l2, self.lr, self.epochs, self.w = l2, lr, epochs, {}

    def fit(self, rows: Sequence[dict]) -> "BradleyTerry":
        w: Dict[str, float] = {}
        n = max(1, len(rows))
        for _ in range(self.epochs):
            grad = {k: self.l2 * v / n for k, v in w.items()}
            for r in rows:
                err = self._p(w, r["x"]) - r["y"]
                for k, v in r["x"].items():
                    grad[k] = grad.get(k, 0.0) + err * v / n
            for k, g in grad.items():
                w[k] = w.get(k, 0.0) - self.lr * g
        self.w = w
        return self

    @staticmethod
    def _p(w, x) -> float:
        z = sum(w.get(k, 0.0) * v for k, v in x.items())
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))

    def prob(self, x: dict) -> float:
        return self._p(self.w, x)


def accuracy(model: BradleyTerry, rows: Sequence[dict]) -> float:
    # A tie (p = 0.5, e.g. no labels yet) counts as half right: chance, not a free win for a.
    return sum(0.5 if model.prob(r["x"]) == 0.5 else float((model.prob(r["x"]) > 0.5) == (r["y"] == 1.0))
               for r in rows) / len(rows)


def _split(pool: List[dict], test_frac: float, rng: random.Random) -> Tuple[List[dict], List[dict]]:
    """(train pool, test) with every group on one side."""
    groups = sorted({r["group"] for r in pool})
    rng.shuffle(groups)
    test_groups = set(groups[:max(1, int(round(test_frac * len(groups))))])
    return [r for r in pool if r["group"] not in test_groups], [r for r in pool if r["group"] in test_groups]


def _committee(rows, n, rng, l2):
    """Bootstrap refits: the committee whose disagreement ranks the next labels."""
    return [BradleyTerry(l2=l2).fit([rng.choice(rows) for _ in rows]) for _ in range(n)]


def simulate_seed(pool: List[dict], seed: int, init: int = 4, batch: int = 4, max_labels: Optional[int] = None,
                  test_frac: float = 0.3, committee: int = 5, diversity: float = DEFAULT_DIVERSITY,
                  l2: float = 0.5) -> dict:
    """One seed: the same split and the same `init` random labels for both strategies."""
    rng = random.Random(seed)
    train, test = _split(pool, test_frac, rng)
    budget = min(len(train), max_labels or len(train))
    start = rng.sample(range(len(train)), min(init, budget))
    if all(r.get("vec") is not None for r in train):
        vecs = [r["vec"] for r in train]
    else:
        tfidf = TfIdf(r["text"] for r in train)
        vecs = [tfidf.vector(r["text"]) for r in train]
    curves = {}
    for strategy in ("random", "uncertainty"):
        srng = random.Random(f"{seed}:{strategy}")
        labelled = list(start)
        points, disagreements, asked = [], 0, 0
        while True:
            model = BradleyTerry(l2=l2).fit([train[i] for i in labelled])
            points.append([len(labelled), accuracy(model, test)])
            if len(labelled) >= budget:
                break
            done = set(labelled)
            left = [i for i in range(len(train)) if i not in done]
            k = min(batch, budget - len(labelled))
            if strategy == "random":
                picks = srng.sample(left, k)
            else:
                members = _committee([train[i] for i in labelled], committee, srng, l2)
                scores = []
                for i in left:
                    ps = [m.prob(train[i]["x"]) for m in members]
                    total, js = committee_uncertainty([[p, 1 - p] for p in ps])
                    scores.append(total + js)
                picks = [left[j] for j, _ in mmr_order(scores, [vecs[i] for i in left], diversity, k)]
            for i in picks:   # a disagreement: the current model would have picked the other option
                p = model.prob(train[i]["x"])
                disagreements += p != 0.5 and (p > 0.5) != (train[i]["y"] == 1.0)
                asked += 1
            labelled += picks
        curves[strategy] = {"points": points, "alc": sum(a for _, a in points) / len(points),
                            "disagreement_rate": disagreements / asked if asked else None}
    full = accuracy(BradleyTerry(l2=l2).fit(train), test)
    return {"seed": seed, "n_train": len(train), "n_test": len(test), "full_pool_accuracy": full, "curves": curves}


def _labels_to_reach(points, target):
    return next((n for n, a in points if a >= target), None)


def simulate(pool: List[dict], seeds: Sequence[int] = (0, 1, 2, 3, 4), **kw) -> dict:
    """Learning curves averaged over seeds, the per-seed area-under-curve gain of uncertainty over
    random, and the labels each needs to reach 95% of the full-pool accuracy."""
    from ..research.stats import bootstrap_ci
    runs = [simulate_seed(pool, s, **kw) for s in seeds]
    out = {"n_pool": len(pool), "seeds": list(seeds), "config": {k: v for k, v in kw.items()}, "per_seed": runs}
    summary = {}
    for strategy in ("random", "uncertainty"):
        by_n: Dict[int, List[float]] = {}
        for r in runs:
            for n, a in r["curves"][strategy]["points"]:
                by_n.setdefault(n, []).append(a)
        summary[strategy] = {
            "curve": [[n, sum(v) / len(v), len(v)] for n, v in sorted(by_n.items())],
            "alc": sum(r["curves"][strategy]["alc"] for r in runs) / len(runs),
            "labels_to_95pct_full": [_labels_to_reach(r["curves"][strategy]["points"], 0.95 * r["full_pool_accuracy"])
                                     for r in runs],
            "disagreement_rate": _mean([r["curves"][strategy]["disagreement_rate"] for r in runs])}
    gains = [r["curves"]["uncertainty"]["alc"] - r["curves"]["random"]["alc"] for r in runs]
    lo, hi = bootstrap_ci(gains) if len(gains) > 1 else (gains[0], gains[0])
    out.update(summary=summary, alc_gain={"mean": sum(gains) / len(gains), "ci90": [lo, hi], "per_seed": gains},
               full_pool_accuracy=_mean([r["full_pool_accuracy"] for r in runs]))
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def markdown(report: dict, title: str) -> str:
    s, g = report["summary"], report["alc_gain"]
    lines = [f"# Active labelling simulation: {title}", "",
             f"Source: `{report.get('source', 'n/a')}`. {report['n_pool']} labelled pairs; seeds {report['seeds']}; "
             f"config {json.dumps(report['config'], sort_keys=True)}. Offline: a stdlib Bradley-Terry learner, "
             "no model calls. Code version " + str(report.get("code_version")) + ".", "",
             "| labels | random | uncertainty |", "|---:|---:|---:|"]
    rnd = {n: a for n, a, _ in s["random"]["curve"]}
    for n, a, _ in s["uncertainty"]["curve"]:
        lines.append(f"| {n} | {rnd.get(n, float('nan')):.3f} | {a:.3f} |")

    def reach(xs):
        return ", ".join("never" if x is None else str(x) for x in xs)
    lines += ["", f"Full-pool accuracy (all training labels): {report['full_pool_accuracy']:.3f}.", "",
              f"Area under the learning curve: random {s['random']['alc']:.3f}, uncertainty {s['uncertainty']['alc']:.3f}; "
              f"gain {g['mean']:+.3f} (90% bootstrap CI over seeds {g['ci90'][0]:+.3f} to {g['ci90'][1]:+.3f}).", "",
              f"Labels to reach 95% of full-pool accuracy, per seed: random [{reach(s['random']['labels_to_95pct_full'])}], "
              f"uncertainty [{reach(s['uncertainty']['labels_to_95pct_full'])}].", "",
              "Share of queried labels where the current model disagreed with the label: random "
              f"{_fmt(s['random']['disagreement_rate'])}, uncertainty {_fmt(s['uncertainty']['disagreement_rate'])}.", ""]
    return "\n".join(lines)


def _fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


# ---- CLI --------------------------------------------------------------------------

def _load_models(paths, backend, model, max_calls):
    if not paths:
        return []
    from ..llm import Budget, get_llm
    from .usermodel import load_model
    llm = get_llm(backend, model, Budget(max_calls=max_calls))
    return [load_model(p, llm) for p in paths]


def main(argv=None):
    p = argparse.ArgumentParser(description="Disagreement-driven label queue and its offline simulation")
    p.add_argument("--root", default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queue", help="rank unlabelled decisions by user-model uncertainty, with diversity")
    q.add_argument("--researcher", required=True)
    q.add_argument("--decisions", nargs="*", help="decisions.jsonl files (default: runs/*/decisions.jsonl)")
    q.add_argument("--out", required=True)
    q.add_argument("--limit", type=int)
    q.add_argument("--diversity", type=float, default=DEFAULT_DIVERSITY, help="0 = uncertainty only, 1 = spread only")
    q.add_argument("--usermodel", nargs="*", default=[],
                   help="saved user models to score with (several: committee disagreement); calls their backend")
    q.add_argument("--backend", default="offline")
    q.add_argument("--model", default="claude-haiku-5-5")
    q.add_argument("--max-calls", type=int, default=500)
    d = sub.add_parser("disagreements", help="write DISAGREE/LABEL facts for labels not yet in shared memory")
    d.add_argument("--researcher", required=True)
    d.add_argument("--decisions", nargs="*")
    d.add_argument("--memory", default="runs/research_memory", help="local store dir when PAST_API_KEY is unset")
    s = sub.add_parser("simulate", help="learning curves: uncertainty vs random labelling (offline)")
    s.add_argument("--choices", required=True, help="labelled pairs: feature rows (choices.jsonl) or Choice rows")
    s.add_argument("--out", required=True, help="output stem; writes <out>.json and <out>.md")
    s.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    s.add_argument("--init", type=int, default=4)
    s.add_argument("--batch", type=int, default=4)
    s.add_argument("--max-labels", type=int, default=60)
    s.add_argument("--test-frac", type=float, default=0.3)
    s.add_argument("--committee", type=int, default=5)
    s.add_argument("--diversity", type=float, default=DEFAULT_DIVERSITY)
    s.add_argument("--l2", type=float, default=0.5)
    a = p.parse_args(argv)
    if a.command == "simulate":
        report = simulate(load_pool(a.choices), a.seeds, init=a.init, batch=a.batch, max_labels=a.max_labels,
                          test_frac=a.test_frac, committee=a.committee, diversity=a.diversity, l2=a.l2)
        report.update(source=a.choices, code_version=code_version(), backend="offline-bradley-terry")
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out + ".json", "w") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
        with open(a.out + ".md", "w") as f:
            f.write(markdown(report, os.path.basename(a.out)))
        print(json.dumps({"alc_gain": report["alc_gain"], "full_pool_accuracy": report["full_pool_accuracy"],
                          "wrote": [a.out + ".json", a.out + ".md"]}, indent=2))
        return
    decisions = a.decisions if a.decisions is not None else sorted(glob.glob(os.path.join("runs", "*", "decisions.jsonl")))
    if a.command == "queue":
        rows = build_queue(a.root, a.researcher, decisions,
                           _load_models(a.usermodel, a.backend, a.model, a.max_calls), a.diversity, a.limit,
                           warn=lambda m: print(m, file=sys.stderr))
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        sources = {}
        for r in rows:
            sources[r["uncertainty_source"]] = sources.get(r["uncertainty_source"], 0) + 1
        print(json.dumps({"queued": len(rows), "uncertainty_sources": sources, "out": a.out,
                          "next": f"python3 -m autoresearch.taste label --researcher {a.researcher} --queue {a.out}"}))
        return
    shared = get_shared_memory(os.path.join(a.memory, "shared.jsonl"))
    print(json.dumps(dict(sync_disagreements(shared, a.root, a.researcher, decisions), memory=shared.backend)))


if __name__ == "__main__":
    main()
