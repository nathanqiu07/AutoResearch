#!/usr/bin/env python3
"""E4b rating packets: blinded decision records for judging the research loop.

PLAN 9 (E4b) asks whether the loop's decisions are justified by the evidence.
Team members who are not the taste source rate each decision 1-5, and an LLM
rubric judge scores the same packets. Packets are blinded: arm names, run ids,
code versions and everything about the user model are removed, the D1 priority
table loses its taste column, and the order is shuffled. A separate key file
maps packet ids back to runs for unblinding.

  # 1. build packets from decision logs (files or directories, searched recursively)
  python3 scripts/make_rating_packets.py make --decisions runs/ results/e4/ --out results/e4b

  # 2. humans fill "rating" (1-5) in a copy of packets.jsonl; optionally an LLM judge rates too
  python3 scripts/make_rating_packets.py judge --packets results/e4b/packets.jsonl --llm anthropic \
      --model claude-sonnet-5-5 --out results/e4b/ratings_llm.jsonl

  # 3. unblind and summarise per arm and decision point
  python3 scripts/make_rating_packets.py summarize --key results/e4b/key.jsonl \
      --ratings results/e4b/ratings_alice.jsonl results/e4b/ratings_llm.jsonl --reports results/e4/

Only the judge step calls a model (paid unless --llm offline).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autoresearch.research.decisions import validate_record  # noqa: E402

POINT_QUESTIONS = {
    "D1": "Which candidate change to test next.",
    "D2": "How much evidence to collect (samples per candidate).",
    "D3": "Whether to accept (and confirm on fresh samples), reject, or defer a tested change.",
    "D4": "Whether to keep exploring or abandon a direction (a category of changes).",
    "D5": "How to read a result: which explanation is most plausible.",
    "D6": "Whether a claim goes into the write-up.",
}
RUBRIC = ("Rate how well the decision is justified by the evidence shown, 1-5: 5 = clearly the right call given "
          "the evidence; 4 = reasonable; 3 = defensible but a better option was available; 2 = poorly supported; "
          "1 = contradicts the evidence. Judge only from what is shown.")
# evidence keys that would reveal the arm or the taste source
BLIND_EVIDENCE = {"taste_weight"}
BLIND_PRIORITY = {"taste"}


def find_decision_files(paths: List[str]) -> List[str]:
    out = []
    for p in paths:
        if os.path.isfile(p):
            out.append(p)
            continue
        for dp, _, fs in os.walk(p):
            out += [os.path.join(dp, f) for f in fs if f == "decisions.jsonl" or f.endswith("_decisions.jsonl")]
    return sorted(set(out))


def load_records(files: List[str]) -> List[dict]:
    """All valid records, de-duplicated (a run's records appear both under
    runs/<run_id>/ and next to its report)."""
    seen, out = set(), []
    for path in files:
        with open(path) as f:
            for n, line in enumerate(f, 1):
                if not line.strip():
                    continue
                rec = json.loads(line)
                errs = validate_record(rec)
                if errs:
                    raise ValueError(f"{path}:{n}: invalid decision record: {errs}")
                key = (rec["run_id"], rec["iter"], rec["point"], rec["context"], tuple(rec["options"]), rec["chosen"])
                if key not in seen:
                    seen.add(key)
                    out.append(rec)
    return out


def _blind_evidence(ev: dict) -> dict:
    out = {k: v for k, v in ev.items() if k not in BLIND_EVIDENCE}
    if isinstance(out.get("priority"), list):
        out["priority"] = [{k: v for k, v in row.items() if k not in BLIND_PRIORITY} if isinstance(row, dict) else row
                           for row in out["priority"]]
    return out


def make_packets(records: List[dict], seed: int = 0, points: Optional[List[str]] = None) -> Tuple[List[dict], List[dict]]:
    rng = random.Random(seed)
    recs = [r for r in records if not points or r["point"] in points]
    order = list(range(len(recs)))
    rng.shuffle(order)
    packets, key = [], []
    used = set()
    for k in order:
        r = recs[k]
        pid = None
        while pid is None or pid in used:
            pid = "%08x" % rng.getrandbits(32)
        used.add(pid)
        packets.append({"packet_id": pid, "point": r["point"], "question": POINT_QUESTIONS[r["point"]],
                        "iteration": r["iter"], "context": r["context"], "options": r["options"],
                        "decision": r["options"][r["chosen"]], "evidence": _blind_evidence(r["evidence"]),
                        "rating": None, "rater": "", "notes": ""})
        key.append({"packet_id": pid, "run_id": r["run_id"], "arm": r["arm"], "iter": r["iter"], "point": r["point"],
                    "chosen": r["chosen"], "user_model_choice": r["user_model_choice"],
                    "user_model_confidence": r["user_model_confidence"], "overrode_taste": r["overrode_taste"],
                    "code_version": r["code_version"]})
    return packets, key


def judge_prompt(packet: dict) -> str:
    opts = "\n".join(f"  [{i}] {o}" for i, o in enumerate(packet["options"]))
    return (f"You audit decisions made by an automated research loop that designs evaluation environments.\n"
            f"Decision type: {packet['question']}\nSituation: {packet['context']}\nOptions:\n{opts}\n"
            f"Decision taken: {packet['decision']}\nEvidence available at the time:\n"
            f"{json.dumps(packet['evidence'], default=str)[:4000]}\n\n{RUBRIC}\n"
            "Return JSON {\"rating\": integer 1-5, \"why\": short reason}.")


def judge_packets(packets: List[dict], llm, rater: str) -> List[dict]:
    from autoresearch.llm import extract_json
    out = []
    for p in packets:
        try:
            res = extract_json(llm.complete(judge_prompt(p), temperature=0.0, max_tokens=300))
        except Exception as e:   # one failed call is recorded, not fatal
            res, err = None, str(e)[:200]
        else:
            err = ""
        rating = res.get("rating") if isinstance(res, dict) else None
        ok = isinstance(rating, int) and not isinstance(rating, bool) and 1 <= rating <= 5
        out.append({"packet_id": p["packet_id"], "rating": rating if ok else None, "rater": rater,
                    "notes": (res.get("why", "") if isinstance(res, dict) else "") if ok else
                    (err or "unparseable judge reply")})
    return out


def load_jsonl(path: str) -> List[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def summarize(key: List[dict], ratings: List[dict], reports: Optional[List[dict]] = None) -> dict:
    """Mean rating per arm and per (arm, point); for decisions where the loop
    departed from the user model, the share rated justified (>= 4); and the
    claim-check pass rate per arm from the run reports."""
    by_id = {k["packet_id"]: k for k in key}
    unknown = [r["packet_id"] for r in ratings if r["packet_id"] not in by_id]
    rows = [(by_id[r["packet_id"]], r) for r in ratings
            if r["packet_id"] in by_id and isinstance(r.get("rating"), int) and 1 <= r["rating"] <= 5]
    raters = sorted({r.get("rater", "") for _, r in rows})
    out = {"n_ratings": len(rows), "unrated": len(ratings) - len(rows) - len(unknown), "unknown_packets": len(unknown),
           "raters": raters, "by_arm": {}, "by_arm_point": {}, "by_rater_arm": {}}
    arms = sorted({k["arm"] for k, _ in rows})
    for arm in arms:
        rs = [r["rating"] for k, r in rows if k["arm"] == arm]
        over = [r["rating"] for k, r in rows if k["arm"] == arm and k["overrode_taste"]]
        out["by_arm"][arm] = {"n": len(rs), "mean_rating": _mean(rs),
                              "overrides_of_taste": len(over),
                              "overrides_rated_justified": (sum(x >= 4 for x in over) / len(over)) if over else None}
        for pt in sorted({k["point"] for k, _ in rows if k["arm"] == arm}):
            xs = [r["rating"] for k, r in rows if k["arm"] == arm and k["point"] == pt]
            out["by_arm_point"][f"{arm}/{pt}"] = {"n": len(xs), "mean_rating": _mean(xs)}
        for who in raters:
            xs = [r["rating"] for k, r in rows if k["arm"] == arm and r.get("rater", "") == who]
            if xs:
                out["by_rater_arm"][f"{who}/{arm}"] = {"n": len(xs), "mean_rating": _mean(xs)}
    if reports:
        cl: Dict[str, List[float]] = {}
        for rep in reports:
            pr = (rep.get("claims") or {}).get("pass_rate")
            if pr is not None:
                cl.setdefault(rep.get("arm", "?"), []).append(pr)
        out["claim_check_pass_rate"] = {a: {"runs": len(v), "mean": _mean(v)} for a, v in sorted(cl.items())}
    return out


def load_reports(paths: List[str]) -> List[dict]:
    out = []
    for p in paths:
        files = [p] if os.path.isfile(p) else [os.path.join(dp, f) for dp, _, fs in os.walk(p) for f in fs
                                                  if f.endswith(".json")]
        for f in sorted(files):
            try:
                with open(f) as fh:
                    rep = json.load(fh)
            except (ValueError, OSError):
                continue
            if isinstance(rep, dict) and "decisions" in rep and "run_id" in rep:
                out.append(rep)
    return out


def write_jsonl(path: str, rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="blinded packets + unblinding key from decision logs")
    m.add_argument("--decisions", nargs="+", required=True, help="decisions.jsonl files or directories")
    m.add_argument("--out", required=True)
    m.add_argument("--seed", type=int, default=0)
    m.add_argument("--points", nargs="*", choices=sorted(POINT_QUESTIONS), help="only these decision points")
    j = sub.add_parser("judge", help="LLM rubric judge over packets")
    j.add_argument("--packets", required=True)
    j.add_argument("--llm", default="offline", choices=["offline", "anthropic", "claude-cli", "openai-compat"])
    j.add_argument("--model", default="claude-sonnet-5-5")
    j.add_argument("--max-calls", type=int, default=2000)
    j.add_argument("--out", required=True)
    s = sub.add_parser("summarize", help="unblind ratings and summarise per arm")
    s.add_argument("--key", required=True)
    s.add_argument("--ratings", nargs="+", required=True)
    s.add_argument("--reports", nargs="*", default=[], help="run report JSONs or directories (claim-check pass rate)")
    s.add_argument("--out")
    a = p.parse_args(argv)
    if a.cmd == "make":
        recs = load_records(find_decision_files(a.decisions))
        if not recs:
            raise SystemExit("no decision records found")
        packets, key = make_packets(recs, a.seed, a.points)
        write_jsonl(os.path.join(a.out, "packets.jsonl"), packets)
        write_jsonl(os.path.join(a.out, "key.jsonl"), key)
        with open(os.path.join(a.out, "INSTRUCTIONS.md"), "w") as f:
            f.write("# E4b rating instructions\n\nCopy packets.jsonl, fill `rating` (1-5) and `rater` on every line, "
                    "and add `notes` where useful. Do not open key.jsonl until all ratings are in.\n\n"
                    f"{RUBRIC}\n\nDecision types:\n\n" +
                    "\n".join(f"- {k}: {v}" for k, v in POINT_QUESTIONS.items()) + "\n")
        print(f"wrote {len(packets)} packets from {len({k['run_id'] for k in key})} runs "
              f"({len({k['arm'] for k in key})} arms) to {a.out}")
    elif a.cmd == "judge":
        from autoresearch.llm import Budget, get_llm
        llm = get_llm(a.llm, a.model, Budget(max_calls=a.max_calls))
        rows = judge_packets(load_jsonl(a.packets), llm, rater=f"llm:{a.llm}:{a.model}")
        write_jsonl(a.out, rows)
        print(f"judged {sum(r['rating'] is not None for r in rows)}/{len(rows)} packets -> {a.out}")
    else:
        ratings = [r for path in a.ratings for r in load_jsonl(path)]
        res = summarize(load_jsonl(a.key), ratings, load_reports(a.reports) if a.reports else None)
        text = json.dumps(res, indent=1)
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w") as f:
                f.write(text + "\n")
        print(text)


if __name__ == "__main__":
    main()
