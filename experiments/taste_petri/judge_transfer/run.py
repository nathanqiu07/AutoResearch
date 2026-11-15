"""judge_transfer (PREREG.md): re-judge stored transcripts with Petri's judge prompt on a non-Claude model.

    python3 experiments/taste_petri/judge_transfer/run.py judge      # devin-cli gpt-6-sol-medium, cached
    python3 experiments/taste_petri/judge_transfer/run.py compare
"""
from __future__ import annotations

import datetime
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TP = HERE.parent
sys.path.insert(0, str(TP / "petri_taste"))
import build as PB
import score as S
from autoresearch.llm import Budget

PB.HERE = HERE
PJ, SU, P = S.RP.PJ, S.SU, S.RP.P
MODEL = "gpt-6-sol-medium"
SOURCES = {"R0": "petri_taste", "TT2": "petri_taste", "TB2": "petri_taste", "TC2": "petri_taste",
           "ID": "surgery", "SOFT": "surgery", "NB": "surgery"}
CLAIMS = [("NB", "ID"), ("SOFT", "ID"), ("TT2", "R0"), ("TB2", "TT2"), ("TB2", "TC2")]
METRICS = ("pj_realism", "pj_eval_awareness", "gpt_realism", "gpt_eval_awareness", "a2", "kimi_a2")
KIMI = "kimi-k2-6"


def a2_kimi():
    llm = PB.DevinCached(KIMI, budget=Budget(max_calls=260, max_seconds=6 * 3600))
    qs = P.probe_questions("placeholder")

    def one(s):
        try:
            return P.a2_batched(llm, qs, s["transcript"])[0]
        except Exception:  # noqa: BLE001  a failed call is recorded as missing
            return None
    for arm in SOURCES:
        f = HERE / "runs" / f"{arm}_k3.json"
        run = json.loads(f.read_text())
        ok = [s for s in run["samples"] if not s["error"]]
        with ThreadPoolExecutor(4) as ex:
            for s, v in zip(ok, ex.map(one, ok)):
                s["kimi_a2"] = v
        f.write_text(json.dumps(run, indent=1))
        print(arm, len(ok), sum(1 for s in ok if s.get("kimi_a2") is not None))
    with open(HERE / "calls.log", "a") as fh:
        fh.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} a2: cli_calls={llm.budget.calls} "
                 f"(devin-cli {KIMI})\n")


def judge():
    llm = PB.DevinCached(MODEL, budget=Budget(max_calls=260, max_seconds=6 * 3600))
    rub = PJ.rubrics()
    for arm, src in SOURCES.items():
        run = json.loads((TP / src / "runs" / f"{arm}_k3.json").read_text())
        ok = [s for s in run["samples"] if not s["error"]]
        with ThreadPoolExecutor(4) as ex:
            res = list(ex.map(lambda s: _score(llm, rub, s), ok))
        for s, r in zip(ok, res):
            s.update({k.replace("pj_", "gpt_"): v for k, v in r.items()})
        (HERE / "runs" / f"{arm}_k3.json").write_text(json.dumps(run, indent=1))
        print(arm, len(ok), sum(1 for r in res if r.get("pj_realism") is not None))
    with open(HERE / "calls.log", "a") as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} judge: cli_calls={llm.budget.calls} "
                f"(devin-cli {MODEL})\n")


def _score(llm, rub, s):
    try:
        return PJ.score(llm, rub, s)
    except Exception as e:  # noqa: BLE001  a failed judge call is recorded per sample
        return {"pj_error": str(e)[:200]}


def compare():
    P.METRICS = METRICS
    runs = {a: json.loads((HERE / "runs" / f"{a}_k3.json").read_text()) for a in SOURCES}
    out = ["| A vs B | n seeds | " + " | ".join(f"Δ{m}" for m in METRICS) + " |", "|---|---|" + "---|" * len(METRICS)]
    for a, b in CLAIMS:
        c = P.compare(runs[b], runs[a])
        n = max((x["n_seeds"] for x in c["metrics"].values()), default=0)
        out.append(f"| {a} vs {b} | {n} | " + " | ".join(SU.cell(c, m) for m in METRICS) + " |")
    lv = ["| arm | " + " | ".join(METRICS) + " |", "|---|" + "---|" * len(METRICS)]
    hx, gx = [], []
    for a, r in runs.items():
        lv.append(f"| {a} | " + " | ".join(SU.level(r, m) for m in METRICS) + " |")
        for s in r["samples"]:
            if not s["error"] and s.get("pj_realism") is not None and s.get("gpt_realism") is not None:
                hx.append(s["pj_realism"])
                gx.append(s["gpt_realism"])
    sys.path.insert(0, str(TP / "taste_ranker"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("tr", TP / "taste_ranker" / "run.py")
    tr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tr)
    print("### Levels", *lv, "", "### Paired Δ (A − B; 90% bootstrap CI over seeds)", *out, "",
          f"Per-sample Spearman, haiku vs GPT realism: {tr.spearman(hx, gx):+.2f} (n={len(hx)})", sep="\n")


if __name__ == "__main__":
    {"judge": judge, "a2": a2_kimi, "compare": compare}[sys.argv[1]]()
