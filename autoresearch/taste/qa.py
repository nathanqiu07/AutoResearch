"""Free-text taste Q&A: each team member answers 24 eval-design questions in their own words.

The questions (data/taste_qa/questions.jsonl) follow the 8 recommendations in Bean et al.,
"Measuring what Matters: Construct Validity in LLM Benchmarks" (NeurIPS 2025, arXiv 2511.04703),
section 3; each row names its section and checklist item. They are not shown to the answerer.

Answers go to data/researchers/<slug>/qa.jsonl, one row per answer, in the person's words.
Split (fixed by hashing, the same for everyone): in each section, the question with the lowest
hash is held out and the rest form the primer, so 16 primer and 8 held-out questions.

    python3 -m autoresearch.taste.qa fill --name "<full name>"    # interactive, resumable
    python3 -m autoresearch.taste.qa status --name "<full name>"
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from typing import Callable, Dict, List

from .researcher import DEFAULT_ROOT
from .trackp import slugify

QUESTIONS_PATH = os.path.join("data", "taste_qa", "questions.jsonl")
ANSWERS = "qa.jsonl"
END = "."

INTRO = """These {n} questions ask how you would make decisions when you build tests of whether an
AI model can tell it's being tested ("eval awareness"). Each test is an environment: the
setup (prompts, files, tools) a model is run in, usually built to see whether the model will
do some bad behaviour. One run is one attempt by the model in one environment.

There are no right answers: say what you would actually do. Two to six sentences is plenty.
If your answer is "it depends", say what it depends on.

To answer, type as many lines as you like, then a line with only a period (.) to finish.
Type skip to skip a question, or quit to stop (Ctrl-D also stops). Your answers are saved as
you go; run this same command again later to pick up where you left off. All {n} take about
40 minutes.
"""


def _read(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def load_questions(path: str = QUESTIONS_PATH) -> List[dict]:
    return _read(path)


def held_out(questions: List[dict]) -> set:
    first: Dict[str, dict] = {}
    for q in questions:
        h = hashlib.sha256(q["id"].encode()).hexdigest()
        if q["section"] not in first or h < first[q["section"]]["h"]:
            first[q["section"]] = {"h": h, "id": q["id"]}
    return {v["id"] for v in first.values()}


def answers(root: str, slug: str) -> List[dict]:
    return _read(os.path.join(root, slug, ANSWERS))


def split(root: str, slug: str, questions_path: str = QUESTIONS_PATH) -> Dict[str, List[dict]]:
    out = held_out(load_questions(questions_path))
    rows = answers(root, slug)
    return {"primer": [r for r in rows if r["qid"] not in out],
            "heldout": [r for r in rows if r["qid"] in out]}


def fill(root: str, name: str, questions_path: str = QUESTIONS_PATH,
         ask: Callable = input, say: Callable = print) -> int:
    slug = slugify(name)
    questions = load_questions(questions_path)
    path = os.path.join(root, slug, ANSWERS)
    done = {r["qid"] for r in _read(path)}
    todo = [q for q in questions if q["id"] not in done]
    if not todo:
        say(f"All {len(questions)} questions answered. Thank you!")
        return 0
    say(INTRO.format(n=len(questions)))
    if done:
        say(f"Welcome back: {len(done)} answered, {len(todo)} to go.\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for q in todo:
        say(f"\n[{questions.index(q) + 1}/{len(questions)}] {q['text']}\n")
        lines = []
        while True:
            try:
                line = ask("> ")
            except EOFError:
                line = "quit" if not lines else END
            if not lines and line.strip().lower() in ("skip", "quit"):
                break
            if line.strip() == END:
                break
            lines.append(line)
        cmd = line.strip().lower() if not lines else ""
        if cmd == "quit":
            say("Stopped. Run the same command to continue.")
            return 0
        text = "\n".join(lines).strip()
        if cmd == "skip" or not text:
            continue
        with open(path, "a") as f:
            f.write(json.dumps({"qid": q["id"], "question": q["text"], "answer": text, "name": name,
                                "answered_at": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
    left = len(questions) - len({r["qid"] for r in _read(path)})
    say(f"\nDone for now. {left} question(s) left unanswered." if left else "\nAll done. Thank you!")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m autoresearch.taste.qa")
    p.add_argument("--root", default=DEFAULT_ROOT)
    sub = p.add_subparsers(dest="cmd", required=True)
    for c in ("fill", "status"):
        sub.add_parser(c).add_argument("--name", required=True, help="your full name")
    a = p.parse_args(argv)
    if a.cmd == "fill":
        return fill(a.root, a.name)
    s = split(a.root, slugify(a.name))
    print(json.dumps({"slug": slugify(a.name), "primer": len(s["primer"]), "heldout": len(s["heldout"]),
                      "unanswered": len(load_questions()) - len(s["primer"]) - len(s["heldout"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
