"""Taste-Bench: does a decider pick the next step that the rest of a real run proved better?

Taste-Bench (Pan et al. 2026, arXiv 2609.25804; github.com/wbopan/tastebench; code MIT,
data CC BY 4.0, gated on Hugging Face as wenbopan/taste-bench@v1.0) shows the task, an
agent's transcript up to a decision fork and two candidate next steps; the rest of the
transcript labels the better one. PLAN uses its research subset (112 forks from METR's
RE-Bench and HCAST runs) to score R0's decider against the taste tracks.

Deciders, all on the same questions:
  * `BaseDecider(llm)`: R0, with the benchmark's own prompt.
  * `BaseDecider(llm, history)`: the prompt arm (R1-X-prompt). The researcher's raw history
    (research/advisor.history_text) is added to the same prompt.
  * `AdvisorDecider(advisor, base_records)`: R1-X, the loop's TasteAdvisor policy. A confident
    user-model choice is taken; otherwise R0's answer stands. Each record also keeps the user
    model's own pick (`um_pred`), so the same run scores the user model alone.

Scoring follows the benchmark's protocol paired_order_v1. Each question is asked in the
published option order and in its exact reverse, with letters recomputed; the reply must end
in `ANSWER: X`; a question counts only if both orders are right, so guessing scores 0.25 and
always picking one position scores 0. Errors and unparsed replies count as wrong, and
rerunning with the same records file retries them.

Differences from paired_order_v1, named in every record's `protocol` field:
  * the 65,536-token input cap is checked as characters / 3 because this package has no
    tokenizer, so long transcripts are cut a little earlier than in the reference runner;
  * every model runs at temperature 0 with at most 1,024 output tokens.

The data lives in data/tastebench/ (gitignored; see its README.md).

    python3 -m autoresearch.taste.tastebench run --decider base --llm anthropic --model <id> --out runs/tastebench/base.jsonl
    python3 -m autoresearch.taste.tastebench run --decider advisor --researcher <slug> --base runs/tastebench/base.jsonl ...
    python3 -m autoresearch.taste.tastebench score runs/tastebench/r1.jsonl --vs runs/tastebench/base.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from typing import Dict, List, Tuple

from ..llm import BudgetExceeded, get_llm
from ..research.advisor import TasteAdvisor, history_text, load_user_model
from ..research.decisions import code_version
from ..research.stats import bootstrap_ci, mean

LETTERS = "AB"
ORDERS = (("seeded", False), ("reversed", True))   # the benchmark's names for the two presentations
MAX_INPUT_TOKENS = 65536
OMISSION_MARKER = "...[middle transcript lines omitted to satisfy the 64K-token input cap]..."
PROTOCOL = "paired_order_v1, input cap counted as characters/3, temperature 0, 1024 output tokens"
SYSTEM = ("You are evaluating an autonomous agent at a technical decision point. The task, the agent's "
          "progress, and two candidate next steps are provided. Exactly one candidate is the better "
          "technical decision.")
USER = ("# Task given to the agent\n{query}\n\n"
        "# Agent's progress so far (transcript up to the decision point)\n{prefix}\n\n"
        "# Decision point\n{options}\n\n"
        "Which option is the better technical decision?\nReturn exactly one line: ANSWER: X")
HISTORY = "# Past choices and documents of the researcher advising this agent\n{history}\n\n"
CONTEXT = ("# Task given to the agent\n{query}\n\n"
           "# Agent's progress so far (transcript up to the decision point)\n{prefix}\n\n"
           "Which candidate next step is the better technical decision?")
ANSWER_LINE = re.compile(r"(?:^|\n)\s*ANSWER:\s*([AB])\s*$", re.I)


# ---------- questions ----------

def check_question(q: dict) -> List[str]:
    """Problems with one released row (empty when it is valid)."""
    problems = [f"empty {key}" for key in ("id", "query", "prefix_text") if not str(q.get(key, "")).strip()]
    choices = q.get("choices") or []
    if len(choices) != 2 or any(not str(c).strip() for c in choices):
        problems.append("needs two nonempty choices")
    if q.get("answer") not in LETTERS or q.get("answer_index") not in (0, 1) or \
            LETTERS[q["answer_index"]] != q["answer"]:
        problems.append(f"answer {q.get('answer')!r} disagrees with answer_index {q.get('answer_index')!r}")
    if q.get("cell") != f"{q.get('method')}_{q.get('domain')}":
        problems.append("cell does not match method and domain")
    return problems


def load_questions(path: str) -> List[dict]:
    with open(path) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    problems = [f"{q.get('id', '?')}: {p}" for q in rows for p in check_question(q)]
    if problems:
        raise ValueError(f"{len(problems)} invalid questions in {path}; first: " + "; ".join(problems[:5]))
    return rows


def presentation(q: dict, reverse: bool) -> Tuple[List[str], str]:
    """The two options in the order shown, and the letter of the better one in that order."""
    order = [1, 0] if reverse else [0, 1]
    return [q["choices"][i].strip() for i in order], LETTERS[order.index(q["answer_index"])]


def option_blocks(options: List[str]) -> str:
    return "\n\n".join(f"Option {LETTERS[i]}:\n{o}" for i, o in enumerate(options))


def _tokens(text: str) -> int:
    return -(-len(text) // 3)


def fit_prefix(prefix: str, render) -> Tuple[str, bool]:
    """The published prefix if the rendered prompt fits the cap; otherwise its first 25 lines,
    the omission marker and the longest tail that fits (the protocol's overflow rule).
    Returns (prefix, truncated)."""
    if _tokens(render(prefix)) <= MAX_INPUT_TOKENS:
        return prefix, False
    lines = prefix.splitlines()
    head, rest = lines[:25] + [OMISSION_MARKER], lines[25:]
    low, high, best = 0, len(rest), None
    while low <= high:
        keep = (low + high) // 2
        candidate = "\n".join(head + (rest[-keep:] if keep else []))
        if _tokens(render(candidate)) <= MAX_INPUT_TOKENS:
            best, low = candidate, keep + 1
        else:
            high = keep - 1
    if best is None:
        raise ValueError("the task and the first 25 transcript lines alone exceed the input cap")
    return best, True


def parse_answer(text: str):
    stripped = text.strip()
    if stripped.upper() in ("A", "B"):
        return stripped.upper()
    m = ANSWER_LINE.search(stripped)
    return m.group(1).upper() if m else None


# ---------- deciders: (question, options in shown order, order name) -> record fields ----------

class BaseDecider:
    """R0 with the benchmark's prompt; given `history`, the prompt arm."""

    def __init__(self, llm, history: str = ""):
        self.llm, self.history = llm, history
        self.name = "prompt" if history else "base"

    def _prompt(self, q, prefix, options):
        head = HISTORY.format(history=self.history) if self.history else ""
        return head + USER.format(query=q["query"].strip(), prefix=prefix.strip(), options=option_blocks(options))

    def __call__(self, q, options, order):
        prefix, truncated = fit_prefix(q["prefix_text"], lambda p: SYSTEM + self._prompt(q, p, options))
        text = self.llm.complete(self._prompt(q, prefix, options), system=SYSTEM, max_tokens=1024, temperature=0.0)
        return {"pred": parse_answer(text), "text": text, "truncated": truncated}


class AdvisorDecider:
    """R1: TasteAdvisor.decide over R0's answer to the same presentation."""
    name = "advisor"

    def __init__(self, advisor: TasteAdvisor, base_records: List[dict]):
        self.advisor = advisor
        self.base = {(r["item_id"], r["order"]): r for r in base_records}

    def __call__(self, q, options, order):
        base = self.base.get((q["id"], order))
        if base is None or base.get("error"):
            raise ValueError(f"no R0 answer for {q['id']} ({order}); run the base decider on these questions first")

        def render(prefix):
            return CONTEXT.format(query=q["query"].strip(), prefix=prefix.strip()) + "".join(options)
        prefix, truncated = fit_prefix(q["prefix_text"], render)
        context = CONTEXT.format(query=q["query"].strip(), prefix=prefix.strip())
        # -1 stands for "R0 gave no parseable answer": R1 then answers only if taste decides.
        default = LETTERS.index(base["pred"]) if base.get("pred") else -1
        n_errors = len(self.advisor.errors)
        index, advice = self.advisor.decide(context, options, default, decisive=False)
        if len(self.advisor.errors) > n_errors:
            # The loop falls back to R0 when the user model fails; a benchmark retries it instead.
            raise RuntimeError(self.advisor.errors[-1])
        return {"pred": LETTERS[index] if index >= 0 else None,
                "um_pred": LETTERS[advice.choice] if advice.choice is not None else None,
                "um_confidence": advice.confidence, "taste_used": advice.usable and advice.choice is not None,
                "um_rationale": advice.rationale, "truncated": truncated}


# ---------- running and scoring ----------

def read_records(path: str) -> List[dict]:
    """The latest record per (question, order), so a retry supersedes a failed attempt."""
    if not os.path.exists(path):
        return []
    latest: Dict[tuple, dict] = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                latest[(r["item_id"], r["order"])] = r
    return list(latest.values())


def run(questions: List[dict], decider, path: str, meta: dict = None) -> List[dict]:
    """Ask `decider` every question in both orders, appending one record per answer to
    `path`. Presentations already answered without error are skipped."""
    done = {(r["item_id"], r["order"]) for r in read_records(path) if not r.get("error")}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a") as f:
        for q in questions:
            for order, reverse in ORDERS:
                if (q["id"], order) in done:
                    continue
                options, correct = presentation(q, reverse)
                rec = {"item_id": q["id"], "cell": q["cell"], "order": order, "correct": correct,
                       "decider": decider.name, "protocol": PROTOCOL, **(meta or {})}
                try:
                    rec.update(decider(q, options, order))
                except BudgetExceeded:
                    raise
                except Exception as e:   # counts as wrong in this run's score; the next run retries it
                    rec.update(pred=None, error=str(e)[:500])
                f.write(json.dumps(rec) + "\n")
                f.flush()
    return read_records(path)


def _pairs(records: List[dict], questions: List[dict], field: str) -> List[Tuple[str, List[dict]]]:
    """Per question: "CC", "CW", "WC" or "WW" (seeded order first), and its two records."""
    by_key = {(r["item_id"], r["order"]): r for r in records}
    out = []
    for q in questions:
        pair, recs = "", []
        for order, reverse in ORDERS:
            r = by_key.get((q["id"], order), {})
            pair += "C" if r.get(field) is not None and r[field] == presentation(q, reverse)[1] else "W"
            recs.append(r)
        out.append((pair, recs))
    return out


def _block(pairs, field):
    n = len(pairs)
    outcomes = Counter(pair for pair, _ in pairs)
    positions, missing, errors, unparsed = Counter(), 0, 0, 0
    for _, recs in pairs:
        for (order, _), r in zip(ORDERS, recs):
            if r.get(field):
                positions[f"{order}_{r[field]}"] += 1
            elif not r:
                missing += 1
            elif r.get("error"):
                errors += 1
            else:
                unparsed += 1
    rate = lambda k: round(k / n, 6) if n else None
    return {"n": n,
            "both_correct_rate": rate(outcomes["CC"]),
            "seeded_accuracy": rate(outcomes["CC"] + outcomes["CW"]),
            "reversed_accuracy": rate(outcomes["CC"] + outcomes["WC"]),
            "two_order_mean_accuracy": round((2 * outcomes["CC"] + outcomes["CW"] + outcomes["WC"]) / (2 * n), 6)
            if n else None,
            "paired_outcomes": {k: outcomes[k] for k in ("CC", "CW", "WC", "WW")},
            "position_choices": dict(sorted(positions.items())),
            "missing": missing, "errors": errors, "unparsed": unparsed}


def summarize(records: List[dict], questions: List[dict], field: str = "pred") -> dict:
    """Paired-order scores over `questions`; a question with no record counts as wrong.
    `average` weights the domains 1:1, as the benchmark's leaderboard does."""
    pairs = _pairs(records, questions, field)
    group = lambda key: {v: _block([p for p, q in zip(pairs, questions) if q[key] == v], field)
                         for v in sorted({q[key] for q in questions})}
    per_domain = group("domain")
    return {"field": field, "overall": _block(pairs, field), "per_cell": group("cell"),
            "per_domain": per_domain,
            "average": round(mean([b["both_correct_rate"] for b in per_domain.values()]), 6) if per_domain else None}


def compare(records: List[dict], base_records: List[dict], questions: List[dict], field: str = "pred") -> dict:
    """`records` minus R0 in the share of questions right in both orders, paired by question,
    with a 90% bootstrap interval over questions."""
    both = lambda recs, fld: [pair == "CC" for pair, _ in _pairs(recs, questions, fld)]
    diffs = [int(a) - int(b) for a, b in zip(both(records, field), both(base_records, "pred"))]
    lo, hi = bootstrap_ci(diffs)
    return {"diff": round(mean(diffs), 6), "ci90": [round(lo, 6), round(hi, 6)], "n": len(diffs)}


# ---------- CLI ----------

def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m autoresearch.taste.tastebench",
                                description="Taste-Bench (paired_order_v1) for R0, the prompt arm and R1.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="ask one decider every question in both option orders")
    r.add_argument("--decider", choices=["base", "prompt", "advisor"], required=True)
    r.add_argument("--questions", default="data/tastebench/research.jsonl")
    r.add_argument("--limit", type=int, default=0, help="first N questions only (smoke tests)")
    r.add_argument("--out", required=True, help="records JSONL; rerunning with the same file resumes it")
    r.add_argument("--llm", default="offline", help="offline, anthropic, openai-compat or claude-cli")
    r.add_argument("--model", default="claude-sonnet-5-5")
    r.add_argument("--researcher", help="slug under --root; needed by the prompt and advisor deciders")
    r.add_argument("--root", default="data/researchers")
    r.add_argument("--um-llm", help="backend the user model was fitted on (default: --llm)")
    r.add_argument("--um-model", help="model the user model was fitted on (default: --model)")
    r.add_argument("--base", help="the base decider's records on the same questions (advisor only)")
    r.add_argument("--dry-run", action="store_true", help="print the request count and a token estimate, then stop")
    s = sub.add_parser("score", help="paired-order scores of one or more records files")
    s.add_argument("records", nargs="+")
    s.add_argument("--questions", default="data/tastebench/research.jsonl")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--vs", help="base records to compare against, paired by question")
    a = p.parse_args(argv)
    questions = load_questions(a.questions)[: a.limit or None]

    if a.cmd == "score":
        base = read_records(a.vs) if a.vs else None
        out = {}
        for path in a.records:
            recs = read_records(path)
            for field in ["pred"] + (["um_pred"] if any("um_pred" in x for x in recs) else []):
                entry = summarize(recs, questions, field)
                if base is not None:
                    entry["vs_base"] = compare(recs, base, questions, field)
                out[f"{path}:{field}"] = entry
        print(json.dumps(out, indent=2))
        return

    if a.decider != "base" and not a.researcher:
        p.error(f"--decider {a.decider} needs --researcher")
    if a.decider == "advisor" and not a.base:
        p.error("--decider advisor needs --base")
    if a.dry_run:
        chars = sum(len(q["query"]) + min(len(q["prefix_text"]), 3 * MAX_INPUT_TOKENS) + len("".join(q["choices"]))
                    for q in questions)
        print(f"{2 * len(questions)} requests, about {2 * chars // 4:,} input tokens (characters / 4)"
              + (", plus the user model's own prompt" if a.decider == "advisor" else ""))
        return
    llm = get_llm(a.llm, a.model)
    meta = {"llm": llm.label, "researcher": a.researcher or "", "code_version": code_version()}
    if a.decider == "base":
        decider = BaseDecider(llm)
    elif a.decider == "prompt":
        decider = BaseDecider(llm, history_text(os.path.join(a.root, a.researcher)))
    else:
        um_llm = get_llm(a.um_llm or a.llm, a.um_model or a.model)
        model, source = load_user_model(os.path.join(a.root, a.researcher), None, um_llm)
        if model is None:
            sys.exit(f"no usermodel.json for {a.researcher}; restore it with "
                     f"python3 -m autoresearch.taste.usermodel_store pull --researcher {a.researcher}")
        decider = AdvisorDecider(TasteAdvisor(model, source=source), read_records(a.base))
        meta["user_model"] = source
    records = run(questions, decider, a.out, meta)
    print(json.dumps(summarize(records, questions)["overall"], indent=2))


if __name__ == "__main__":
    main()
