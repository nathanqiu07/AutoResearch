"""Small, bounded algorithms shared by the paper-inspired preference methods."""
import math
import random
import re
from collections import Counter
from dataclasses import asdict

from ..usermodel import digest


def bounded_int(config, name, default, minimum=0, maximum=50):
    value = config.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError("%s must be an integer in [%s, %s]" % (name, minimum, maximum))
    return value


def bounded_float(config, name, default, minimum=0., maximum=1.):
    value = config.get(name, default)
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or not minimum <= value <= maximum):
        raise ValueError("%s must be finite and in [%s, %s]" % (name, minimum, maximum))
    return float(value)


def selected_history(model, history):
    limit = bounded_int(model.config, "max_history", 5, minimum=1)
    ordered = sorted(history, key=lambda row: row.identity)
    if len(ordered) > limit:
        ordered = sorted(random.Random(model.seed).sample(ordered, limit), key=lambda row: row.identity)
    return ordered


def example(row):
    return asdict(row)


def text_field(result, key, max_chars=2000):
    value = result.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > max_chars:
        raise ValueError("%s must be nonempty text with at most %s characters" % (key, max_chars))
    return value.strip()


def accuracy(rows, predictor):
    if not rows:
        raise ValueError("validation accuracy requires nonempty rows")
    return sum(predictor(row.context, [row.a_text, row.b_text]).choice == row.chosen
               for row in rows) / len(rows)


def forward_select(candidates, score, max_items):
    """Greedily add only strict gains; record every attempted candidate."""
    chosen, remaining, trace = [], list(enumerate(candidates)), []
    current = score(chosen)
    while remaining and len(chosen) < max_items:
        trials = []
        for index, candidate in remaining:
            after = score(chosen + [candidate])
            entry = {"round": len(chosen), "candidate_index": index, "before": current,
                     "after": after, "delta": after - current, "selected": False}
            trace.append(entry)
            trials.append((after, index, candidate, entry))
        best = max(trials, key=lambda item: item[0])
        if best[0] <= current:
            break
        current = best[0]
        chosen.append(best[2])
        best[3]["selected"] = True
        remaining = [(i, c) for i, c in remaining if i != best[1]]
    return chosen, trace


def remove_harmful(components, score):
    """Iterative leave-one-out; strictly harmful components go, ties stay."""
    kept, trace = list(enumerate(components)), []
    current = score([c for _, c in kept])
    round_number = 0
    while kept:
        trials = []
        for index, component in kept:
            after = score([c for i, c in kept if i != index])
            entry = {"round": round_number, "component_index": index, "before": current,
                     "without": after, "contribution": current - after, "removed": False}
            trace.append(entry)
            trials.append((after, index, entry))
        best = max(trials, key=lambda item: item[0])
        if best[0] <= current:
            break
        current = best[0]
        best[2]["removed"] = True
        kept = [(i, c) for i, c in kept if i != best[1]]
        round_number += 1
    return [c for _, c in kept], trace


def tokens(text):
    return re.findall(r"\w+", text.casefold())


def tfidf(texts):
    counts = [Counter(tokens(text)) for text in texts]
    document_frequency = Counter(token for count in counts for token in count)
    vectors = []
    for count in counts:
        vector = {token: (1 + math.log(freq)) *
                  (1 + math.log((len(counts) + 1) / (document_frequency[token] + 1)))
                  for token, freq in count.items()}
        norm = math.sqrt(sum(x * x for x in vector.values()))
        vectors.append({token: weight / norm for token, weight in vector.items()} if norm else {})
    return vectors


def cosine(left, right):
    norm = math.sqrt(sum(x * x for x in left.values()) * sum(x * x for x in right.values()))
    return sum(weight * right.get(token, 0.) for token, weight in left.items()) / norm if norm else 0.


def cluster_principles(texts, threshold=.75):
    """Complete-link lexical clusters, with a conservative negation guard.

    This cannot identify semantic equivalence or all contradictions. No claim of
    semantic deduplication is made. Original indices preserve proposal provenance.
    """
    if not 0 < threshold <= 1 or not math.isfinite(threshold):
        raise ValueError("cluster threshold must be in (0, 1]")
    vectors = tfidf(texts)
    polarity = [bool(set(tokens(t)) & {"not", "never", "no", "avoid", "without"}) for t in texts]
    groups = []
    for index in range(len(texts)):
        for group in groups:
            if all(polarity[index] == polarity[j] and cosine(vectors[index], vectors[j]) >= threshold
                   for j in group):
                group.append(index)
                break
        else:
            groups.append([index])
    result = []
    for group in groups:
        medoid = max(group, key=lambda i: sum(cosine(vectors[i], vectors[j]) for j in group))
        result.append({"representative": texts[medoid], "representative_index": medoid,
                       "members": group})
    return result


def retrieve(context, options, pool, count):
    if not pool or count <= 0:
        return []
    texts = [context + " " + " ".join(options)] + [
        row["context"] + " " + row["a_text"] + " " + row["b_text"] for row in pool]
    vectors = tfidf(texts)
    ranked = sorted(range(len(pool)), key=lambda i: (-cosine(vectors[0], vectors[i + 1]),
                                                    pool[i].get("example_id", ""), i))
    return [pool[i] for i in ranked[:count]]


def fit_child(parent, cls, history, val):
    child = cls(parent.llm, seed=parent.seed, cache_dir=parent.cache_dir,
                max_calls=max(0, parent.max_calls - parent.cost["calls"]), **parent.config)
    try:
        child.fit(history, val)
    finally:
        for key in ("calls", "cache_hits", "input_tokens", "output_tokens", "cost_usd"):
            parent.cost[key] += child.cost[key]
        parent.cost["cost_available"] = parent.cost["cost_available"] or child.cost["cost_available"]
    return child.artifacts()


def partition_calibration(rows, seed=0, fraction=.5):
    """Label-independent partition of whole conversations; one group stays tuning-only."""
    if not 0 < fraction < 1:
        raise ValueError("calibration fraction must be between zero and one")
    groups = {}
    for row in rows:
        key = row.group_id or digest([row.user_id, row.context])
        groups.setdefault(key, []).append(row)
    keys = sorted(groups)
    if len(keys) < 2:
        return list(rows), []
    random.Random(seed).shuffle(keys)
    count = min(len(keys) - 1, max(1, round(len(keys) * fraction)))
    calibration = set(keys[:count])
    tune = [row for key in sorted(groups) if key not in calibration for row in groups[key]]
    cal = [row for key in sorted(groups) if key in calibration for row in groups[key]]
    return tune, cal


def logit(p):
    p = max(1e-6, min(1 - 1e-6, p))
    return math.log(p) - math.log1p(-p)


def sigmoid(x):
    if x >= 0:
        return 1. / (1. + math.exp(-x))
    e = math.exp(x)
    return e / (1. + e)


def fit_platt(probabilities, labels, min_samples=8, regularization=.01, max_iterations=200):
    """Regularized binary logistic calibration of P(a), using bounded Newton steps."""
    if len(probabilities) != len(labels):
        raise ValueError("calibration probabilities/labels length mismatch")
    if (any(isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or
            not 0 <= p <= 1 for p in probabilities) or any(y not in (0, 1) for y in labels)):
        raise ValueError("invalid calibration data")
    if not math.isfinite(regularization) or regularization <= 0 or max_iterations < 1:
        raise ValueError("calibration regularization and iterations must be positive")
    state = {"fitted": False, "n": len(labels), "a": 1., "b": 0.,
             "regularization": regularization, "target": "probability_of_a"}
    if len(labels) < min_samples:
        return dict(state, reason="too_few_calibration_rows")
    if len(set(labels)) < 2:
        return dict(state, reason="single_calibration_class")
    xs, n = [logit(p) for p in probabilities], len(labels)
    a, b = 1., 0.

    def objective(aa, bb):
        zs = [aa * x + bb for x in xs]
        return (sum(max(z, 0) + math.log1p(math.exp(-abs(z))) - y * z
                    for z, y in zip(zs, labels)) / n + regularization * (aa * aa + bb * bb) / 2)

    initial = objective(a, b)
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        ps = [sigmoid(a * x + b) for x in xs]
        da = sum((p - y) * x for p, y, x in zip(ps, labels, xs)) / n + regularization * a
        db = sum(p - y for p, y in zip(ps, labels)) / n + regularization * b
        if max(abs(da), abs(db)) < 1e-8:
            break
        haa = sum(p * (1 - p) * x * x for p, x in zip(ps, xs)) / n + regularization
        hab = sum(p * (1 - p) * x for p, x in zip(ps, xs)) / n
        hbb = sum(p * (1 - p) for p in ps) / n + regularization
        determinant = haa * hbb - hab * hab
        step_a, step_b = (hbb * da - hab * db) / determinant, (haa * db - hab * da) / determinant
        before, scale = objective(a, b), 1.
        for _ in range(24):
            candidate_a, candidate_b = a - scale * step_a, b - scale * step_b
            if objective(candidate_a, candidate_b) < before:
                a, b = candidate_a, candidate_b
                break
            scale *= .5
        else:
            break
    return dict(state, fitted=True, reason="fitted_on_reserved_validation", a=a, b=b,
                iterations=iterations, initial_objective=initial, final_objective=objective(a, b))


def apply_platt(probability, state):
    if not state.get("fitted"):
        return probability
    return sigmoid(state["a"] * logit(probability) + state["b"])
