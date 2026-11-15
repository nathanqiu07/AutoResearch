"""WS B personal track: the trade-off bank, stance/scenario pair builders, LLM-written
scenarios and the balance check that gates them.

Every axis is asked as a stance item. Axes at decision points where the loop lets taste act
(D1, D3 when inconclusive, D4, D5) also carry a scenario, asked once per person in one
environment, rotated so no question text repeats.

A pair row is {pair_id, form, axis, decision_point, origin, item, context, question, a_text,
b_text, a_pole, b_pole}. The poles record which bank option sits on each side after
shuffling; the person never sees them."""
import datetime
import json
import random
from typing import List

from ..llm import extract_json
from .usermodel import digest

BANK_PATH = "data/trackp/tradeoffs.jsonl"
BALANCE = "balance.jsonl"
REQUIRED = ("axis", "decision_point", "question", "pole_1", "pole_2")
SCENARIO_FIELDS = ("scenario_question", "scenario_1", "scenario_2")
STANCE_CONTEXT = "A question about how you design evals in general."
REVISING = ("You are revising this environment so it looks less like a test. A 'change' is one such "
            "revision; a 'direction' is a family of similar revisions.")


def load_bank(path: str = BANK_PATH) -> List[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            for field in REQUIRED:
                if not row.get(field):
                    raise ValueError(f"bank row for axis {row.get('axis', '?')!r} is missing {field!r}")
            if not isinstance(row.get("sources"), list):
                raise ValueError(f"bank row for axis {row['axis']!r} needs a 'sources' list (may be empty)")
            present = [bool(row.get(f)) for f in SCENARIO_FIELDS]
            if any(present) and not all(present):
                raise ValueError(f"bank row for axis {row['axis']!r} has a partial scenario")
            rows.append(row)
    return rows


def has_scenario(row: dict) -> bool:
    return bool(row.get("scenario_question"))


def scenario_context(sc) -> str:
    lines = [f"Item: {sc.name}", f"Research goal: {sc.goal}", f"Setting: {sc.setting}",
             f"The environment must keep this opportunity: {sc.probe}"]
    if sc.original:
        lines += ["Original system prompt: " + sc.original.get("system", ""),
                  "Original user message: " + sc.original.get("user", "")]
    return "\n".join(lines + [REVISING])


def full_context(pair: dict) -> str:
    """What a model sees: the shared context and the question, as one text."""
    return pair["context"] + "\n\n" + pair["question"]


def _pair(form: str, row: dict, item, context: str, question: str, text_1: str, text_2: str,
          origin: str, rng: random.Random) -> dict:
    flip = rng.random() < 0.5
    (a_text, b_text), (a_pole, b_pole) = ((text_2, text_1), (2, 1)) if flip else ((text_1, text_2), (1, 2))
    name = item.name if item else None
    return {"pair_id": digest([form, row["axis"], name or "", question, a_text, b_text])[:12], "form": form,
            "axis": row["axis"], "decision_point": row["decision_point"], "origin": origin,
            "item": name, "context": context, "question": question, "a_text": a_text, "b_text": b_text,
            "a_pole": a_pole, "b_pole": b_pole}


def stance_pairs(bank: List[dict], seed: int = 0) -> List[dict]:
    rng = random.Random(seed)
    return [_pair("stance", r, None, STANCE_CONTEXT, r["question"], r["pole_1"], r["pole_2"], "bank", rng)
            for r in bank]


def scenario_pairs(bank: List[dict], items: list, seed: int = 0) -> List[dict]:
    """One scenario per scenario axis, each in a different environment where there are enough:
    axis i goes to items[(i + offset) % len(items)], the offset drawn from the seed."""
    rng = random.Random(seed)
    offset = rng.randrange(len(items))
    rows = [r for r in bank if has_scenario(r)]
    return [_pair("scenario", r, items[(i + offset) % len(items)], scenario_context(items[(i + offset) % len(items)]),
                  r["scenario_question"], r["scenario_1"], r["scenario_2"], "bank", rng)
            for i, r in enumerate(rows)]


def build_seed_pairs(bank: List[dict], items: list, seed: int = 0) -> List[dict]:
    return stance_pairs(bank, seed) + scenario_pairs(bank, items, seed)


def llm_scenario_pairs(bank: List[dict], items: list, llm, k: int, seed: int = 0,
                       warn=print) -> List[dict]:
    """For each item, k scenario axes taken round-robin; the LLM writes one option per pole,
    made specific to that environment."""
    rng = random.Random(seed)
    rows = [r for r in bank if has_scenario(r)]
    order = list(range(len(rows)))
    rng.shuffle(order)
    out = []
    for i, sc in enumerate(items):
        for j in range(k):
            row = rows[order[(i * k + j) % len(rows)]]
            prompt = (
                "Write two answer options for a researcher choosing how to design an eval "
                "environment.\n\n" + scenario_context(sc) + "\n\n"
                f"Trade-off axis: {row['axis']}\nPole 1: {row['pole_1']}\nPole 2: {row['pole_2']}\n"
                f"Question: {row['scenario_question']}\n\n"
                "Option 1 must take pole 1 and option 2 pole 2, each made concrete for this environment. "
                "Both must be defensible, of similar length and specificity, and use no evaluative "
                'words such as "better", "rigorous" or "sloppy". Return JSON: '
                '{"option_1": str, "option_2": str}.')
            reply = extract_json(llm.complete(prompt, temperature=0.9, max_tokens=500))
            o1 = str(reply.get("option_1", "")).strip() if isinstance(reply, dict) else ""
            o2 = str(reply.get("option_2", "")).strip() if isinstance(reply, dict) else ""
            if not o1 or not o2 or o1 == o2:
                warn(f"skipped LLM scenario for item {sc.name!r}, axis {row['axis']!r}: "
                     "reply was not JSON with two different options")
                continue
            out.append(_pair("scenario", row, sc, scenario_context(sc), row["scenario_question"],
                             o1, o2, "llm", rng))
    return out


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def balance_check(pairs: List[dict], judge, threshold: float = 0.75) -> List[dict]:
    """One check row per pair, from the public track's blind judge (track_eval.BlindJudge): a
    model with no history about the person answers in both option orders, as in
    track_eval.paired_correct. `picks` is its choice each time, as the public track scores it;
    a forced choice picks the same pole on almost any lean, so the gate uses its probabilities.
    One-sided when it gives the same pole >= threshold in both orders; a taste item should
    leave it roughly undecided."""
    rows = []
    for p in pairs:
        text = {p["a_pole"]: p["a_text"], p["b_pole"]: p["b_text"]}
        first = judge.predict(full_context(p), [text[1], text[2]])
        second = judge.predict(full_context(p), [text[2], text[1]])
        p_pole1 = [first.probabilities[0], second.probabilities[1]]
        rows.append({"type": "check", "pair_id": p["pair_id"],
                     "picks": [1 if first.choice == "a" else 2, 2 if second.choice == "a" else 1],
                     "p_pole1": p_pole1,
                     "one_sided": min(p_pole1) >= threshold or max(p_pole1) <= 1 - threshold,
                     "method": judge.method_id, "timestamp": _now()})
    return rows


def shown(pair: dict, balance_rows: List[dict]) -> bool:
    mine = [r for r in balance_rows if r.get("pair_id") == pair["pair_id"]]
    reviews = [r["decision"] for r in mine if r["type"] == "review"]
    if "drop" in reviews:
        return False
    if "approve" in reviews:
        return True
    checks = [r for r in mine if r["type"] == "check"]
    if checks:
        return not checks[-1]["one_sided"]
    return pair["origin"] == "bank"
