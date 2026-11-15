"""WS B personal track: the trade-off bank, stance/scenario pair builders, LLM-written
scenarios and the balance check that gates them.

A pair row is {pair_id, form, axis, decision_point, origin, item, context, a_text, b_text,
a_pole, b_pole}. The poles record which bank option sits on each side after shuffling; the
person never sees them."""
import datetime
import json
import random
from typing import List

from ..llm import extract_json
from .usermodel import digest

BANK_PATH = "data/trackp/tradeoffs.jsonl"
BALANCE = "balance.jsonl"
REQUIRED = ("axis", "decision_point", "sources", "question", "pole_1", "pole_2",
            "scenario_question", "scenario_1", "scenario_2")
STANCE_CONTEXT = "A question about how you design evals in general."


def load_bank(path: str = BANK_PATH) -> List[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            for field in REQUIRED:
                if field not in row or row[field] in ("", None, []):
                    raise ValueError(f"bank row for axis {row.get('axis', '?')!r} is missing {field!r}")
            rows.append(row)
    return rows


def scenario_context(sc) -> str:
    lines = [f"Item: {sc.name}", f"Research goal: {sc.goal}", f"Setting: {sc.setting}",
             f"The environment must keep this opportunity: {sc.probe}"]
    if sc.original:
        lines += ["Original system prompt: " + sc.original.get("system", ""),
                  "Original user message: " + sc.original.get("user", "")]
    return "\n".join(lines)


def _pair(form: str, row: dict, item, context: str, text_1: str, text_2: str,
          origin: str, rng: random.Random) -> dict:
    flip = rng.random() < 0.5
    (a_text, b_text), (a_pole, b_pole) = ((text_2, text_1), (2, 1)) if flip else ((text_1, text_2), (1, 2))
    name = item.name if item else None
    return {"pair_id": digest([form, row["axis"], name or "", a_text, b_text])[:12], "form": form,
            "axis": row["axis"], "decision_point": row["decision_point"], "origin": origin,
            "item": name, "context": context, "a_text": a_text, "b_text": b_text,
            "a_pole": a_pole, "b_pole": b_pole}


def stance_pairs(bank: List[dict], seed: int = 0) -> List[dict]:
    rng = random.Random(seed)
    return [_pair("stance", r, None, STANCE_CONTEXT + "\n\n" + r["question"],
                  r["pole_1"], r["pole_2"], "bank", rng) for r in bank]


def _scenario_row(row: dict, sc, text_1: str, text_2: str, origin: str, rng: random.Random) -> dict:
    return _pair("scenario", row, sc, scenario_context(sc) + "\n\n" + row["scenario_question"],
                 text_1, text_2, origin, rng)


def scenario_pairs(bank: List[dict], items: list, n: int, seed: int = 0) -> List[dict]:
    """n distinct (axis, item) pairs, shuffled, then taken round-robin over items."""
    rng = random.Random(seed)
    combos = [(sc, r) for sc in items for r in bank]
    if len(combos) < n:
        raise ValueError(f"only {len(combos)} distinct scenario pairs available for {n} requested")
    rng.shuffle(combos)
    queues = [[c for c in combos if c[0] is sc] for sc in items]
    picked = []
    while len(picked) < n:
        for q in queues:
            if q and len(picked) < n:
                picked.append(q.pop(0))
    return [_scenario_row(r, sc, r["scenario_1"], r["scenario_2"], "bank", rng) for sc, r in picked]


def build_seed_pairs(bank: List[dict], items: list, n: int, seed: int = 0) -> List[dict]:
    stance = stance_pairs(bank, seed)[:n]
    return stance + scenario_pairs(bank, items, n - len(stance), seed) if n > len(stance) else stance


def llm_scenario_pairs(bank: List[dict], items: list, llm, k: int, seed: int = 0,
                       warn=print) -> List[dict]:
    """For each item, k axes taken round-robin; the LLM writes one option per pole."""
    rng = random.Random(seed)
    order = list(range(len(bank)))
    rng.shuffle(order)
    out = []
    for i, sc in enumerate(items):
        for j in range(k):
            row = bank[order[(i * k + j) % len(bank)]]
            prompt = (
                "Write two answer options for a researcher choosing how to design an eval "
                "environment.\n\n" + scenario_context(sc) + "\n\n"
                f"Trade-off axis: {row['axis']}\nPole 1: {row['pole_1']}\nPole 2: {row['pole_2']}\n"
                f"Question: {row['scenario_question']}\n\n"
                "Option 1 must take pole 1 and option 2 pole 2, each made concrete for this item. "
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
            out.append(_scenario_row(row, sc, o1, o2, "llm", rng))
    return out


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def balance_check(pairs: List[dict], model, threshold: float = 0.8) -> List[dict]:
    """One check row per pair. One-sided only when the same pole gets >= threshold in both
    orders; a model that always favours the first slot is position bias, not pole bias."""
    rows = []
    for p in pairs:
        text = {p["a_pole"]: p["a_text"], p["b_pole"]: p["b_text"]}
        p_12 = model.predict(p["context"], [text[1], text[2]]).probabilities[0]
        p_21 = model.predict(p["context"], [text[2], text[1]]).probabilities[1]
        rows.append({"type": "check", "pair_id": p["pair_id"], "p_pole1": [p_12, p_21],
                     "one_sided": min(p_12, p_21) >= threshold or max(p_12, p_21) <= 1 - threshold,
                     "method": model.method_id, "timestamp": _now()})
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
