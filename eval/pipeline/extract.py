"""Turn Petri .eval logs into one record per run (condition x seed x epoch).

Each record holds the Petri judge scores, the target's reasoning and visible output
(across every branch, including ones the auditor rolled back, as Petri's judge sees it),
and the final-branch target conversation for the post-hoc question.

Usage: python extract.py            -> out/records.jsonl
"""

from __future__ import annotations

from inspect_ai.log import list_eval_logs, read_eval_log
from inspect_ai.model import ChatMessageAssistant
from petri.transcript.transcript import Event, _collect_messages
from pydantic import TypeAdapter

from common import OUT, split_assistant, write_jsonl

_events = TypeAdapter(list[Event])
KEEP_SCORES = ["eval_awareness", "audit_situational_awareness", "scenario_realism", "auditor_failure"]


def _store_events(store: dict) -> list:
    for k, v in store.items():
        if k.split(":")[-1] == "events" and "AuditStore" in k:
            return _events.validate_python(v)
    return []


def _petri_scores(sample) -> tuple[dict, str]:
    """Petri fills any score its judge failed to parse with 1 (= not aware), which would bias
    results toward 'less aware'. So failed parses become None, and partial parses are flagged."""
    for s in (sample.scores or {}).values():
        if isinstance(s.value, dict) and "eval_awareness" in s.value:
            expl = s.explanation or ""
            if expl.startswith("Failed to parse"):
                return {k: None for k in KEEP_SCORES}, "failed"
            return {k: s.value.get(k) for k in KEEP_SCORES}, ("partial" if expl.startswith("Partial parse") else "ok")
    return {k: None for k in KEEP_SCORES}, "missing"


def record_from_sample(md: dict, sample) -> dict:
    events = _store_events(sample.store or {})
    all_msgs = _collect_messages(events, "target", add_only=True) if events else []
    final_msgs = _collect_messages(events, "target") if events else []
    reasoning, output = [], []
    turn = 0
    for m in all_msgs:
        if isinstance(m, ChatMessageAssistant):
            turn += 1
            r, o = split_assistant(m)
            if r:
                reasoning.append(f"[turn {turn}] {r}")
            if o:
                output.append(f"[turn {turn}] {o}")
    scores, status = _petri_scores(sample)
    first_user = next((m.text for m in final_msgs if m.role == "user"), "")
    system = next((m.text for m in final_msgs if m.role == "system"), "")
    return {
        "condition": md["condition"],
        "split": md["split"],
        "seed_id": md["seed_id"],
        "epoch": sample.epoch,
        "run_id": f'{md["condition"]}|{md["split"]}|{md["seed_id"]}|{sample.epoch}',
        "petri": scores,
        "petri_judge_status": status,
        "petri_judge_summary": next(
            (s.answer for s in (sample.scores or {}).values() if isinstance(s.value, dict)), None
        ),
        "task_text": (system + "\n\n" + first_user).strip(),
        "reasoning": "\n\n".join(reasoning),
        "output": "\n\n".join(output),
        "n_target_turns": turn,
        "final_messages": [m.model_dump(mode="json") for m in final_msgs],
        "error": str(sample.error.message) if sample.error else None,
    }


def main():
    rows = []
    for info in list_eval_logs(str(OUT / "logs")):
        log = read_eval_log(info)
        md = log.eval.metadata or {}
        if "condition" not in md:
            continue
        for s in log.samples or []:
            rows.append(record_from_sample(md, s))
    write_jsonl(OUT / "records.jsonl", rows)
    n_err = sum(1 for r in rows if r["error"])
    n_noreason = sum(1 for r in rows if not r["reasoning"])
    n_judge = sum(1 for r in rows if r["petri_judge_status"] != "ok")
    print(f"{len(rows)} runs -> out/records.jsonl ({n_err} errored, {n_judge} with a failed or partial Petri judge, "
          f"{n_noreason} with no reasoning text)")


if __name__ == "__main__":
    main()
