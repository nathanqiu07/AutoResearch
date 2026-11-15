"""Grill the person about the current task and patch their user model with the answers.

Like the "grill me" skill: the system interviews the person one question at a time about the
decisions the research loop will face on the task at hand (decision points D1-D6), and gives
its recommended answer, which is the user model's own guess, with each question. It asks first
where the model is least sure, and after a disagreement or a stated reason it follows that
branch with follow-up questions before moving on. The answers become a task-scoped patch on
`data/researchers/<slug>/usermodel.json`, the file the loop loads (research/advisor.load_user_model).

Questions come from three sources, most grounded first:
  decisions   records the loop logged on this task (runs/<run>/decisions.jsonl), asked as they were
  bank        trade-off items (data/trackp/tradeoffs.jsonl) ranked by lexical similarity to the task
  llm         task-specific questions and follow-ups written by an LLM (`--backend`, paid unless offline)

Everything for one task lives in data/researchers/<slug>/grill/<task>/:
  meta.json        the task and its text
  questions.jsonl  every question asked or queued, with the user model's guess and confidence
  answers.jsonl    the person's answers, skips and stated principles

How a patch acts on the model:
  * each answer with a reason, and each stated principle, becomes a principle scoped to the task
    ("While working on <task>: ...", the person's own words, never paraphrased);
  * each answer becomes an exemplar choice. Methods that retrieve exemplars (m5-m7) get it in the
    retrieval pool, so it is used when a decision resembles it; the others (m1-m3) show it always.
  * m0 and m4 read neither principles nor exemplars, so they refuse a patch: refit instead.
  * m7's Platt calibration was fitted on the unpatched model; the patched file says so.

`apply` keeps the unpatched model in usermodel.base.json and always rebuilds usermodel.json from
it plus every task's answers, so applying twice is the same as once and `revert` restores the
base. A refit (trackp fit) writes an unpatched usermodel.json, which `apply` takes as the new base.

Grill answers stay out of every split that trackp builds (history/val/test). They are task-specific
corrections, not held-out evidence, and a model patched with them is not the fitted model that E2
evaluated. The prompt arm (advisor.history_text) does not read them either, so an R1 run with a
patched model and its R1-prompt control differ by more than the user model method.

    python3 -m autoresearch.taste.grill run    --researcher <slug> --task eval_awareness [--decisions runs/x/decisions.jsonl] [--backend anthropic --model ...]
    python3 -m autoresearch.taste.grill start  --researcher <slug> --task-text "..." [--n 6]   # JSON, for an agent in chat
    python3 -m autoresearch.taste.grill next | status --researcher <slug> --task ...
    python3 -m autoresearch.taste.grill record --id <qid> --choice <n> [--reason "..."] --researcher <slug> --task ...
    python3 -m autoresearch.taste.grill skip --id <qid> | principle --text "..." | follow-up --id <qid>
    python3 -m autoresearch.taste.grill apply | revert --researcher <slug>
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict
from typing import Callable, Dict, List, Optional, Sequence

from ..research.decisions import POINTS, validate_record
from . import tradeoffs
from .methods.common import cosine, tfidf
from .researcher import DEFAULT_ROOT
from .usermodel import Choice, digest

GRILL_DIR, META, QUESTIONS, ANSWERS = "grill", "meta.json", "questions.jsonl", "answers.jsonl"
USERMODEL, BASE = "usermodel.json", "usermodel.base.json"
TRACKS_FILE = "tracks.json"
NO_PATCH_METHODS = {"m0": "m0 judges a typical user and reads no personal evidence",
                    "m4": "m4 predicts from feature weights only"}
MAX_OPTIONS, MAX_CONTEXT, MAX_OPTION_CHARS = 4, 2000, 500


# ---- small file helpers ---------------------------------------------------------------------

def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _read(path: str) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _append(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: str, body: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(json.dumps(body, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    os.replace(tmp, path)


def _sha(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---- the task -------------------------------------------------------------------------------

def resolve_task(task: Optional[str] = None, task_text: Optional[str] = None) -> Dict[str, str]:
    """{"task": slug, "text": what the questions are about}. A registered task name
    (autoresearch/tasks) supplies its goal and probe; free text gets a slug from its words."""
    from ..tasks import TASKS
    if task and task in TASKS:
        t = TASKS[task]
        text = t.goal + (f" The environment's probe: {t.probe_description}." if getattr(t, "probe_description", "") else "")
        return {"task": task, "text": (text + (" " + task_text if task_text else "")).strip()}
    if task_text:
        words = re.findall(r"[a-z0-9]+", task_text.lower())[:6]
        return {"task": task or ("-".join(words)[:48] + "-" + digest(task_text)[:6]), "text": task_text.strip()}
    if task:
        raise ValueError(f"{task!r} is not a registered task ({sorted(TASKS)}); describe it with --task-text")
    raise ValueError("name the current task with --task or describe it with --task-text")


# ---- question sources -----------------------------------------------------------------------

def _question(task: str, point: str, context: str, options: Sequence[str], source: str,
              why: str = "", parent: str = "", depth: int = 0, evidence: Optional[dict] = None) -> dict:
    options = [str(o).strip() for o in options]
    return {"id": "q" + digest([task, point, context, options])[:12], "task": task, "point": point,
            "context": context.strip(), "options": options, "why": why.strip(), "source": source,
            "parent": parent, "depth": depth, "evidence": evidence or {}}


def bank_questions(task: Dict[str, str], n: int, bank_path: str = tradeoffs.BANK_PATH) -> List[dict]:
    """The `n` trade-off items closest to the task text, framed as decisions on this task."""
    bank = tradeoffs.load_bank(bank_path)
    texts = [task["text"]] + [" ".join(str(r.get(k, "")) for k in
                                       ("axis", "question", "pole_1", "pole_2", "scenario_question",
                                        "scenario_1", "scenario_2")) for r in bank]
    vectors = tfidf(texts)
    ranked = sorted(range(len(bank)), key=lambda i: (-cosine(vectors[0], vectors[i + 1]), bank[i]["axis"]))
    out = []
    for i in ranked[:n]:
        row = bank[i]
        if tradeoffs.has_scenario(row):
            question, options = row["scenario_question"], [row["scenario_1"], row["scenario_2"]]
        else:
            question, options = row["question"], [row["pole_1"], row["pole_2"]]
        out.append(_question(task["task"], row["decision_point"], f"Current task: {task['text']}\n\n{question}",
                             options, "bank", why=f"trade-off axis: {row['axis']}"))
    return out


def decision_questions(task: Dict[str, str], paths: Sequence[str], warn: Callable = print) -> List[dict]:
    """The loop's logged decisions on this task, asked as they were (context, options, evidence)."""
    out = []
    for path in paths:
        for k, rec in enumerate(_read(path)):
            errs = validate_record(rec)
            if errs:
                warn(f"skipping {path}:{k + 1}: {'; '.join(errs)}")
                continue
            if len(rec["options"]) < 2:
                continue
            out.append(_question(task["task"], rec["point"], rec["context"], [str(o) for o in rec["options"][:MAX_OPTIONS]],
                                 "decisions", why=f"logged at {rec['run_id']} iter {rec['iter']}",
                                 evidence=rec.get("evidence") or {}))
    return out


GENERATE = """You help a researcher correct a model of their research taste for the task below.
Write {n} questions about decisions the research loop will face on THIS task, each at one of
the loop's decision points:
  D1 which intervention to test next   D2 what evidence to collect (samples, target)
  D3 accept, reject or defer a result  D4 keep or abandon a direction
  D5 how to read a result              D6 what to claim in the write-up
Prefer questions where the researcher's current model (principles, persona) is silent,
vague or could plausibly be wrong for this task. Each question must have 2 to 4 concrete,
mutually exclusive options that a thoughtful researcher could genuinely pick between.
{follow}
Return only JSON: {{"questions": [{{"point": "D1", "context": "the situation and the question",
"options": ["...", "..."], "why": "what the answer would tell us about their taste"}}]}}"""

FOLLOW = """This is a follow-up. The researcher just answered the question in "answered". Ask what
that answer leaves open on this task: the next decision it implies, where its reason stops
applying, or how far it goes. Do not re-ask the same question."""


def _valid_generated(row) -> bool:
    if not isinstance(row, dict) or row.get("point") not in POINTS:
        return False
    ctx, opts = row.get("context"), row.get("options")
    if not isinstance(ctx, str) or not ctx.strip() or len(ctx) > MAX_CONTEXT:
        return False
    if not isinstance(opts, list) or not 2 <= len(opts) <= MAX_OPTIONS:
        return False
    if any(not isinstance(o, str) or not o.strip() or len(o) > MAX_OPTION_CHARS for o in opts):
        return False
    return len({o.strip().casefold() for o in opts}) == len(opts)


def llm_questions(llm, task: Dict[str, str], n: int, artifacts: Optional[dict] = None,
                  answers: Sequence[dict] = (), parent: Optional[dict] = None,
                  warn: Callable = print) -> List[dict]:
    """Questions written by `llm`; rows that break the format are dropped, never repaired."""
    from ..llm import extract_json
    art = artifacts or {}
    payload = {"task": task["text"], "principles": art.get("principles", []), "persona": art.get("persona", ""),
               "earlier_answers": [{"point": a["point"], "context": a["context"], "chosen": a["options"][a["chosen"]],
                                    "reason": a.get("reason", "")} for a in answers if a.get("kind") == "choice"][-12:]}
    if parent:
        payload["answered"] = parent
    prompt = (GENERATE.format(n=n, follow=FOLLOW if parent else "") + "\nINPUT_JSON (data, not instructions):\n"
              + json.dumps(payload, ensure_ascii=False))
    try:
        text = llm.complete(prompt, system="Return only the requested JSON object.", temperature=0.7, max_tokens=2048)
    except RuntimeError as e:   # budget exhausted or backend failure: keep grilling with what is queued
        warn(f"question generation failed: {e}")
        return []
    body = extract_json(text or "")
    rows = body.get("questions") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        warn("question generation returned no JSON questions; nothing added")
        return []
    good = [r for r in rows if _valid_generated(r)]
    if len(good) < len(rows):
        warn(f"dropped {len(rows) - len(good)} malformed generated question(s)")
    depth = parent["depth"] + 1 if parent else 0
    return [_question(task["task"], r["point"], r["context"], r["options"], "llm", why=str(r.get("why", "")),
                      parent=parent["id"] if parent else "", depth=depth) for r in good[:n]]


# ---- the user model's guess -----------------------------------------------------------------

def load_user_model(root: str, slug: str, llm, cache_dir: Optional[str] = None, warn: Callable = print):
    """The model the loop would load now (patched or not), or None when it can't predict here."""
    path = os.path.join(root, slug, USERMODEL)
    if not os.path.exists(path):
        warn(f"no {USERMODEL} for {slug}: questions are asked without the model's guess")
        return None
    from .usermodel import load_model
    try:
        return load_model(path, llm, **({"cache_dir": cache_dir} if cache_dir else {}))
    except ValueError as e:
        warn(f"can't predict with {path}: {e}; questions are asked without the model's guess")
        return None


def score(questions: List[dict], model, warn: Callable = print) -> List[dict]:
    """Add the user model's guess (0-based) and confidence to each question in place."""
    for q in questions:
        q.setdefault("model_guess", None)
        q.setdefault("model_confidence", None)
        if model is None or q["model_guess"] is not None:
            continue
        try:
            p = model.predict(q["context"], q["options"])
        except (RuntimeError, ValueError) as e:
            warn(f"user model could not predict {q['id']}: {e}")
            continue
        q["model_guess"], q["model_confidence"] = p.index, round(float(p.confidence), 4)
    return questions


# ---- one task's grill session ---------------------------------------------------------------

class Session:
    def __init__(self, root: str, slug: str, task: Dict[str, str]):
        self.root, self.slug, self.task = root, slug, task
        self.dir = os.path.join(root, slug, GRILL_DIR, task["task"])
        meta = os.path.join(self.dir, META)
        if not os.path.exists(meta):
            os.makedirs(self.dir, exist_ok=True)
            _write_json(meta, {"task": task["task"], "text": task["text"], "researcher": slug, "created": _now()})

    @classmethod
    def open(cls, root: str, slug: str, task_name: str) -> "Session":
        """An existing session by its task slug (for record/skip/apply in agent mode)."""
        meta = os.path.join(root, slug, GRILL_DIR, task_name, META)
        if not os.path.exists(meta):
            raise ValueError(f"no grill session for task {task_name!r}; run 'start' first")
        with open(meta) as f:
            m = json.load(f)
        return cls(root, slug, {"task": m["task"], "text": m["text"]})

    def questions(self) -> List[dict]:
        return _read(os.path.join(self.dir, QUESTIONS))

    def answers(self) -> List[dict]:
        return _read(os.path.join(self.dir, ANSWERS))

    def add(self, questions: List[dict]) -> List[dict]:
        """Queue new questions (dedup by id). Returns the ones actually added."""
        seen = {q["id"] for q in self.questions()}
        added = []
        for q in questions:
            if q["id"] not in seen:
                seen.add(q["id"])
                q = dict(q, queued=_now())
                _append(os.path.join(self.dir, QUESTIONS), q)
                added.append(q)
        return added

    def pending(self) -> List[dict]:
        """Unanswered questions, depth-first (follow-ups of the latest branch first), then the
        ones the user model is least sure about; questions with no guess keep queue order last."""
        done = {a["question_id"] for a in self.answers() if a.get("question_id")}
        rows = [(i, q) for i, q in enumerate(self.questions()) if q["id"] not in done]
        key = lambda iq: (-iq[1]["depth"], -iq[0] if iq[1]["depth"] else 0,
                          iq[1]["model_confidence"] if iq[1].get("model_confidence") is not None else 2.0, iq[0])
        return [q for _, q in sorted(rows, key=key)]

    def get(self, qid: str) -> dict:
        for q in self.questions():
            if q["id"] == qid:
                return q
        raise ValueError(f"no question {qid!r} in this session")

    def record(self, qid: str, shown: int, reason: str = "") -> dict:
        """Store the answer: `shown` is the 1-based option number as displayed."""
        q = self.get(qid)
        if any(a.get("question_id") == qid for a in self.answers()):
            raise ValueError(f"{qid} is already answered")
        if not 1 <= shown <= len(q["options"]):
            raise ValueError(f"choice must be 1..{len(q['options'])}, got {shown}")
        idx, guess = shown - 1, q.get("model_guess")
        row = {"kind": "choice", "question_id": qid, "task": self.task["task"], "point": q["point"],
               "context": q["context"], "options": q["options"], "chosen": idx, "reason": reason.strip(),
               "model_guess": guess, "model_confidence": q.get("model_confidence"),
               "agreed": None if guess is None else guess == idx, "source": q["source"], "timestamp": _now()}
        _append(os.path.join(self.dir, ANSWERS), row)
        return row

    def skip(self, qid: str) -> None:
        self.get(qid)
        _append(os.path.join(self.dir, ANSWERS), {"kind": "skip", "question_id": qid, "timestamp": _now()})

    def principle(self, text: str) -> dict:
        if not text.strip():
            raise ValueError("a principle needs text")
        row = {"kind": "principle", "task": self.task["task"], "text": text.strip(), "timestamp": _now()}
        _append(os.path.join(self.dir, ANSWERS), row)
        return row

    def status(self) -> dict:
        ans = self.answers()
        choices = [a for a in ans if a["kind"] == "choice"]
        judged = [a for a in choices if a["agreed"] is not None]
        return {"task": self.task["task"], "text": self.task["text"], "queued": len(self.questions()),
                "pending": len(self.pending()), "answered": len(choices),
                "skipped": sum(a["kind"] == "skip" for a in ans),
                "principles": sum(a["kind"] == "principle" for a in ans),
                "model_agreed": sum(a["agreed"] for a in judged), "model_judged": len(judged)}


def public(q: dict) -> dict:
    """What an agent shows the person: the question, its options and the model's guess (1-based)."""
    out = {k: q[k] for k in ("id", "point", "context", "options", "why", "source", "depth", "evidence") if q.get(k)}
    out["depth"] = q.get("depth", 0)
    if q.get("model_guess") is not None:
        out["recommended"] = q["model_guess"] + 1
        out["model_confidence"] = q["model_confidence"]
    return out


# ---- the patch ------------------------------------------------------------------------------

def _task_label(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def answer_choices(slug: str, answer: dict) -> List[Choice]:
    """An answer as pairwise choices: the chosen option against each other option."""
    picked, out = answer["options"][answer["chosen"]], []
    for j, other in enumerate(answer["options"]):
        if j == answer["chosen"]:
            continue
        chosen_first = int(digest([answer["question_id"], j])[0], 16) % 2 == 0
        a, b = (picked, other) if chosen_first else (other, picked)
        out.append(Choice(user_id=slug, context=answer["context"], a_text=a, b_text=b,
                          chosen="a" if chosen_first else "b", decision_point=answer["point"],
                          reason=answer.get("reason", ""), timestamp=answer["timestamp"], source="grill",
                          example_id=f"grill:{answer['question_id']}:{j}", group_id=f"grill:{answer['question_id']}"))
    return out


def build_patch(session: Session) -> dict:
    label = _task_label(session.task["text"])
    principles, exemplars, n = [], [], 0
    for a in session.answers():
        if a["kind"] == "principle":
            principles.append(f"While working on {label}: {a['text']}")
        elif a["kind"] == "choice":
            n += 1
            exemplars += [asdict(c) for c in answer_choices(session.slug, a)]
            if a.get("reason"):
                others = "; ".join(f'"{o}"' for j, o in enumerate(a["options"]) if j != a["chosen"])
                principles.append(f"While working on {label}: at {a['point']} prefers "
                                  f"\"{a['options'][a['chosen']]}\" over {others}, because {a['reason']}")
    answers_path = os.path.join(session.dir, ANSWERS)
    return {"task": session.task["task"], "task_text": session.task["text"], "answers": n,
            "principles": principles, "exemplars": exemplars,
            "answers_sha": _sha(answers_path) if os.path.exists(answers_path) else ""}


def sessions(root: str, slug: str) -> List[Session]:
    return [Session.open(root, slug, os.path.basename(os.path.dirname(m)))
            for m in sorted(glob.glob(os.path.join(root, slug, GRILL_DIR, "*", META)))]


def _base(root: str, slug: str) -> dict:
    """The unpatched model, updating usermodel.base.json when usermodel.json is a newer fit."""
    cur_path, base_path = os.path.join(root, slug, USERMODEL), os.path.join(root, slug, BASE)
    if not os.path.exists(cur_path):
        raise ValueError(f"no {USERMODEL} for {slug}: fit one first (trackp fit), then apply the grill patch")
    with open(cur_path) as f:
        cur = json.load(f)
    grill = cur.get("artifacts", {}).get("metadata", {}).get("grill")
    if grill is None:                        # an unpatched fit: it is the base now
        _write_json(base_path, cur)
        return cur
    if not os.path.exists(base_path) or _sha(base_path) != grill["base_sha"]:
        raise ValueError(f"{USERMODEL} is patched but {BASE} is missing or not the model it was patched from; "
                         "refit the model, or restore the base file from git")
    with open(base_path) as f:
        return json.load(f)


def apply(root: str, slug: str, tasks: Optional[Sequence[str]] = None) -> dict:
    """Rebuild usermodel.json as the base model plus the grill patches of `tasks` (default: all)."""
    base = _base(root, slug)
    base_sha = _sha(os.path.join(root, slug, BASE))
    method = base.get("method")
    if method in NO_PATCH_METHODS:
        raise ValueError(f"{NO_PATCH_METHODS[method]}, so a grill patch cannot change its predictions; "
                         "refit with a method that reads principles or exemplars (m1-m3, m5-m7)")
    chosen = [s for s in sessions(root, slug) if tasks is None or s.task["task"] in tasks]
    missing = set(tasks or ()) - {s.task["task"] for s in chosen}
    if missing:
        raise ValueError(f"no grill session for {sorted(missing)}")
    patches = [p for p in (build_patch(s) for s in chosen) if p["principles"] or p["exemplars"]]
    body = json.loads(json.dumps(base))
    art = body["artifacts"]
    meta = art.setdefault("metadata", {})
    retrieves = "retrieval_pool" in meta     # m5-m7 retrieve; m1-m3 show every exemplar
    for p in patches:
        art["principles"] = list(art.get("principles", [])) + p["principles"]
        if retrieves:
            meta["retrieval_pool"] = list(meta["retrieval_pool"]) + p["exemplars"]
        else:
            art["exemplars"] = list(art.get("exemplars", [])) + p["exemplars"]
    notes = []
    if meta.get("calibration", {}).get("fitted"):
        notes.append("Platt calibration was fitted on the unpatched model; confidences on patched "
                     "decisions are not recalibrated")
    meta["grill"] = {"base_sha": base_sha, "applied": _now(), "exemplars_in": "retrieval_pool" if retrieves else "exemplars",
                     "patches": [{k: p[k] for k in ("task", "task_text", "answers", "answers_sha")} |
                                 {"principles": len(p["principles"]), "exemplars": len(p["exemplars"])} for p in patches],
                     "notes": notes}
    _write_json(os.path.join(root, slug, USERMODEL), body)
    return meta["grill"]


def revert(root: str, slug: str) -> bool:
    """Restore the unpatched model. False when usermodel.json carries no patch."""
    cur_path = os.path.join(root, slug, USERMODEL)
    if not os.path.exists(cur_path):
        return False
    with open(cur_path) as f:
        if "grill" not in json.load(f).get("artifacts", {}).get("metadata", {}):
            return False
    _write_json(cur_path, _base(root, slug))
    return True


# ---- the interview --------------------------------------------------------------------------

def show(q: dict, say: Callable = print, k: Optional[int] = None, task_text: str = "") -> None:
    """Print one question. The task, already shown once, is not repeated before each question."""
    head = f"[{q['point']}]" + (f" (follow-up, depth {q['depth']})" if q.get("depth") else "")
    context = q["context"]
    prefix = f"Current task: {task_text}\n\n"
    if task_text and context.startswith(prefix):
        context = context[len(prefix):]
    say(f"\n{('#' + str(k) + ' ') if k else ''}{head} {context}")
    if q.get("evidence"):
        say("evidence: " + json.dumps(q["evidence"], sort_keys=True))
    for shown, text in enumerate(q["options"], 1):
        say(f"  {shown}) {text}")
    if q.get("model_guess") is not None:
        say(f"recommended (your user model's guess): {q['model_guess'] + 1}  "
            f"[confidence {q['model_confidence']:.0%}]")
    if q.get("why"):
        say(f"why this matters: {q['why']}")


def interview(session: Session, ask: Callable = input, say: Callable = print, model=None, llm=None,
              max_questions: int = 10, follow_ups: int = 2, refill: int = 4) -> int:
    """Ask pending questions one at a time until `max_questions`, quit or nothing is left.
    Answer with a number (then an optional reason), `s` to skip, `p <text>` to state a principle,
    `q` to stop. A disagreement with the model, or a reason, opens follow-ups when `llm` is set."""
    asked, refilled = 0, False
    while asked < max_questions:
        pending = session.pending()
        if not pending and llm is not None and not refilled:
            refilled = True
            new = session.add(score(llm_questions(llm, session.task, refill, _artifacts(model),
                                                  session.answers(), warn=say), model, warn=say))
            pending = session.pending() if new else []
        if not pending:
            say("\nNo more questions for this task.")
            break
        q = pending[0]
        show(q, say, asked + 1, session.task["text"])
        valid = [str(i) for i in range(1, len(q["options"]) + 1)]
        while True:
            ans = ask(f"{'/'.join(valid)} | s skip | p <principle> | q quit> ").strip()
            if ans.lower().startswith("p "):
                session.principle(ans[2:])
                say("noted.")
                continue
            if ans in valid or ans.lower() in ("s", "skip", "q", "quit"):
                break
        if ans.lower() in ("q", "quit"):
            break
        asked += 1
        if ans not in valid:
            session.skip(q["id"])
            continue
        reason = ask("why? (one line, enter to skip)> ").strip()
        row = session.record(q["id"], int(ans), reason)
        if row["agreed"] is not None:
            say("matches the model's guess." if row["agreed"] else "the model guessed differently; noted.")
        if llm is not None and follow_ups > 0 and (row["agreed"] is False or reason):
            parent = {"id": q["id"], "depth": q.get("depth", 0), "point": q["point"], "context": q["context"],
                      "options": q["options"], "chosen": q["options"][row["chosen"]], "reason": reason}
            session.add(score(llm_questions(llm, session.task, follow_ups, _artifacts(model), session.answers(),
                                            parent=parent, warn=say), model, warn=say))
    return asked


def _artifacts(model) -> Optional[dict]:
    return asdict(model.artifacts()) if model is not None else None


# ---- CLI ------------------------------------------------------------------------------------

def _researcher(root: str, slug: Optional[str]) -> str:
    if slug:
        return slug
    path = os.path.join(root, TRACKS_FILE)
    if os.path.exists(path):
        with open(path) as f:
            p = json.load(f).get("P")
        if p:
            return p
    raise SystemExit("pass --researcher (no personal-track person in tracks.json)")


def _llms(args):
    """(question writer, user-model predictor); None when not requested."""
    from ..llm import Budget, get_llm
    budget = Budget(max_calls=args.max_calls)
    writer = get_llm(args.backend, args.model, budget) if args.backend else None
    um_backend = args.um_backend or args.backend
    predictor = get_llm(um_backend, args.um_model or args.model, budget) if um_backend else None
    return writer, predictor


def _cache_dir(slug: str) -> str:
    return os.path.join("runs", "grill_cache", slug)   # runs/ is scratch (gitignored)


def _seed(session: Session, args, writer, model, say) -> List[dict]:
    qs = decision_questions(session.task, args.decisions or [], warn=say)
    if args.bank:
        qs += bank_questions(session.task, args.bank, args.bank_path)
    if writer is not None and args.n:
        qs += llm_questions(writer, session.task, args.n, _artifacts(model), session.answers(), warn=say)
    return session.add(score(qs, model, warn=say))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.taste.grill", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, task=True):
        p.add_argument("--root", default=DEFAULT_ROOT)
        p.add_argument("--researcher")
        if task:
            p.add_argument("--task", help="registered task name (autoresearch/tasks) or a session's task slug")
            p.add_argument("--task-text", help="free-text description of the current task")
        return p

    def models(p):
        p.add_argument("--backend", help="LLM that writes questions; omit to use only decisions and the bank")
        p.add_argument("--model", default="claude-haiku-5-5")
        p.add_argument("--um-backend", help="backend the user model predicts with (default: --backend); "
                                            "must match the one it was fitted on")
        p.add_argument("--um-model")
        p.add_argument("--max-calls", type=int, default=60)
        return p

    def seeds(p):
        p.add_argument("--decisions", nargs="*", help="decisions.jsonl files from runs on this task")
        p.add_argument("--bank", type=int, default=4, help="trade-off bank items closest to the task (0: none)")
        p.add_argument("--bank-path", default=tradeoffs.BANK_PATH)
        p.add_argument("--n", type=int, default=4, help="LLM-written questions to add")
        return p

    p = seeds(models(common(sub.add_parser("run", help="interactive grill in this terminal"))))
    p.add_argument("--max-questions", type=int, default=10)
    p.add_argument("--follow-ups", type=int, default=2)
    p.add_argument("--apply", action="store_true", help="apply the patch at the end without asking")
    seeds(models(common(sub.add_parser("start", help="create/extend a session; print pending questions as JSON"))))
    common(sub.add_parser("next", help="the next question as JSON"))
    common(sub.add_parser("status"))
    p = common(sub.add_parser("record"))
    p.add_argument("--id", required=True)
    p.add_argument("--choice", type=int, required=True, help="1-based option number as shown")
    p.add_argument("--reason", default="")
    p = common(sub.add_parser("skip"))
    p.add_argument("--id", required=True)
    p = common(sub.add_parser("principle"))
    p.add_argument("--text", required=True)
    p = models(common(sub.add_parser("follow-up", help="LLM follow-ups to an answered question")))
    p.add_argument("--id", required=True)
    p.add_argument("--n", type=int, default=2)
    p = common(sub.add_parser("apply", help="rebuild usermodel.json = base + grill patches"), task=False)
    p.add_argument("--tasks", nargs="*", help="task slugs to apply (default: all)")
    common(sub.add_parser("revert", help="restore the unpatched usermodel.json"), task=False)
    args = ap.parse_args(argv)

    root = args.root
    slug = _researcher(root, args.researcher)
    say = lambda *a: print(*a, file=sys.stderr) if args.cmd in ("start", "next", "follow-up") else print(*a)
    try:
        if args.cmd == "apply":
            print(json.dumps(apply(root, slug, args.tasks), indent=2))
            return 0
        if args.cmd == "revert":
            print("restored the unpatched user model" if revert(root, slug) else "usermodel.json carries no grill patch")
            return 0
        if args.cmd in ("run", "start"):
            session = Session(root, slug, resolve_task(args.task, args.task_text))
        else:
            if not args.task:
                raise ValueError("name the session with --task <task slug> (see grill/ under the researcher)")
            session = Session.open(root, slug, args.task)
        if args.cmd in ("run", "start", "follow-up"):
            writer, predictor = _llms(args)
            model = load_user_model(root, slug, predictor, _cache_dir(slug), warn=say) if predictor else None
        if args.cmd == "run":
            added = _seed(session, args, writer, model, say)
            say(f"task: {session.task['text']}\n{len(added)} new question(s); {len(session.pending())} pending.")
            interview(session, model=model, llm=writer, max_questions=args.max_questions, follow_ups=args.follow_ups)
            st = session.status()
            say(json.dumps(st, indent=2))
            if st["answered"] or st["principles"]:
                go = args.apply or input("apply this patch to usermodel.json now? [y/N]> ").strip().lower() == "y"
                if go:
                    try:
                        say(json.dumps(apply(root, slug), indent=2))
                    except ValueError as e:
                        say(f"not applied: {e}")
            return 0
        if args.cmd == "start":
            _seed(session, args, writer, model, say)
            print(json.dumps({"task": session.task, "pending": [public(q) for q in session.pending()]}, indent=2))
        elif args.cmd == "next":
            pending = session.pending()
            print(json.dumps(public(pending[0]) if pending else None, indent=2))
        elif args.cmd == "status":
            print(json.dumps(session.status(), indent=2))
        elif args.cmd == "record":
            row = session.record(args.id, args.choice, args.reason)
            print(json.dumps({"recorded": args.id, "agreed_with_model": row["agreed"]}))
        elif args.cmd == "skip":
            session.skip(args.id)
            print(json.dumps({"skipped": args.id}))
        elif args.cmd == "principle":
            session.principle(args.text)
            print(json.dumps({"principle": args.text}))
        elif args.cmd == "follow-up":
            if writer is None:
                raise ValueError("follow-up needs --backend for the question writer")
            ans = [a for a in session.answers() if a.get("question_id") == args.id and a["kind"] == "choice"]
            if not ans:
                raise ValueError(f"{args.id} has no recorded answer")
            q, a = session.get(args.id), ans[-1]
            parent = {"id": q["id"], "depth": q.get("depth", 0), "point": q["point"], "context": q["context"],
                      "options": q["options"], "chosen": q["options"][a["chosen"]], "reason": a.get("reason", "")}
            added = session.add(score(llm_questions(writer, session.task, args.n, _artifacts(model),
                                                    session.answers(), parent=parent, warn=say), model, warn=say))
            print(json.dumps([public(q) for q in added], indent=2))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
