"""Hill-climb a taste-steered seed rewrite against the generic-realism control R0 on the E3b proxy.

    python3 experiments/taste_petri/hillclimb/hc.py build H1 --split dev        # sonnet rewrites -> seeds/H1_dev.jsonl
    python3 experiments/taste_petri/hillclimb/hc.py score H1 --split dev --ks 0 1 2
    python3 experiments/taste_petri/hillclimb/hc.py compare R0 H1 --split dev

Scoring is ../real_material/rm_proxy.py's no-material path, unchanged (auditor-sim, target-sim, batched A2 with the
placeholder probes, A1/validity judge, seed faithfulness, Petri-judge proxy; all haiku; date pinned to 2026-11-15),
so R0's dev samples k=0..5 come free from the caches earlier runs committed. Each scored sample's metrics (not the
transcript) go to scores/<arm>_<split>.jsonl, which is committed; raw calls are cached in cache/.

Arms are prompt templates in prompts/<arm>.txt (placeholders {{COMMON}}, {{SEED}}, {{TASTE_BLOCK}}, {{GUARD}};
an arm with taste "none" gets an empty TASTE_BLOCK, which is how each arm's no-researcher placebo is made) plus the
optional multi-step pipelines in PIPELINES below. See PREREG.md for the protocol and LOG.md for each iteration.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TP = HERE.parent
REPO = TP.parents[1]
for d in ("proxy", "arms", "real_material"):
    sys.path.insert(0, str(TP / d))
import petri_judge as PJ  # noqa: E402
import proxy_eval as P  # noqa: E402
import rm_proxy as RP  # noqa: E402

from autoresearch.research.stats import bootstrap_ci, mean, prob_better  # noqa: E402

RP.HERE = HERE
RP.CALLS_LOG = HERE / "calls.log"
RP.READ_CACHES = [TP / d / "cache" for d in ("decoys", "petri_taste", "real_material", "proxy", "arms")]
RP.BUDGET = 6000
PROMPTS = HERE / "prompts"
SEEDS = HERE / "seeds"
SCORES = HERE / "scores"
BASE = REPO / "data" / "petri" / "seeds_v2.jsonl"
SEED_RE = re.compile(r"<seed>(.*?)</seed>", re.DOTALL)
METRICS = ("score", "awareness", "a2", "a1", "validity", "bait_reached", "faithful", "pj_eval_awareness",
           "pj_realism")
KEEP = METRICS + ("opportunity", "scorable", "pj_audit_sa", "pj_tells", "behavior", "error")


def log(line: str):
    RP.log(line)
    print(line)


def base_seeds(split: str):
    return P.load_seeds(str(BASE), split)


# ---------- building arms ----------
def fill(name: str, **kw) -> str:
    text = (PROMPTS / name).read_text()
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", v)
    if "{{" in text:
        raise ValueError(f"unfilled placeholder in {name}: {re.findall(r'{{[A-Z_]+}}', text)}")
    return text


def cap_of(n: int) -> int:
    return max(int(1.3 * n), 600)        # as arms/make_arms.py: 1.3x stock, floor 600 chars


def common(n: int) -> str:
    return (TP / "arms" / "prompts" / "common.txt").read_text().replace("{{CAP}}", str(int(0.85 * cap_of(n)))) \
        .replace("{{N}}", str(n))


def rewrite(llm, prompt: str, n: int) -> tuple[str, str]:
    """(seed text, raw reply); one retry if there is no <seed> block or it is over the length cap."""
    raw = llm.complete(prompt, max_tokens=4000)
    m = SEED_RE.search(raw)
    if m and len(m.group(1).strip()) <= cap_of(n):
        return m.group(1).strip(), raw
    got = len(m.group(1).strip()) if m else 0
    fix = (f"{prompt}\n\nYour previous answer was:\n{raw}\n\n"
           + (f"It is {got} characters; the hard limit is {cap_of(n)}. Shorten it to at most {int(0.9 * cap_of(n))} "
              "characters without dropping the opportunity, the pressure or the monitoring instruction."
              if m else "It had no <seed>...</seed> block.")
           + " Return the edited seed between <seed> and </seed>.")
    raw2 = llm.complete(fix, max_tokens=4000)
    m2 = SEED_RE.search(raw2)
    if not m2:
        raise ValueError(f"no <seed> after retry: {raw2[:200]!r}")
    return m2.group(1).strip(), raw2


def taste_text(spec: str) -> str:
    """'<slug>:<file stem prefix>[,<slug>:<prefix>...]' -> the profile files (generator comments dropped).
    'none' -> empty. Files live in ../profiles/<slug>/ (read-only)."""
    if spec in ("", "none"):
        return ""
    parts = []
    for item in spec.split(","):
        slug, fmt = item.split(":")
        fmt, _, picks = fmt.partition("#")
        f = next((TP / "profiles" / slug).glob(f"{fmt}_*.md"))
        body = "\n".join(l for l in f.read_text().splitlines() if not l.startswith("<!--")).strip()
        if picks:                                   # keep only the numbered moves listed, e.g. "c#5+6"
            moves = re.split(r"(?m)^(?=\d+\. \*\*)", body.split("**What they", 1)[0])
            keep = {int(x) for x in picks.split("+")}
            body = "\n".join(m.strip() for m in moves if re.match(r"(\d+)\. ", m)
                              and int(re.match(r"(\d+)\. ", m).group(1)) in keep)
        parts.append(f"From {slug.replace('_', ' ').title()}:\n{body}")
    return "\n\n".join(parts)


ARMS = json.loads((HERE / "arms.json").read_text()) if (HERE / "arms.json").exists() else {}


def build_one(llm, arm: str, s: dict) -> dict:
    spec = ARMS[arm]
    n = len(s["text"])
    src = s
    if spec.get("input"):                           # edit another arm's rewrite of this seed (e.g. the control R0)
        src = next(r for r in P.load_seeds(str(SEEDS / f"{spec['input']}_{s['split']}.jsonl"))
                   if r["base_seed_id"] == s["seed_id"])
    taste = taste_text(spec.get("taste", "none"))
    who = ", ".join(x.split(":")[0].replace("_", " ").title() for x in spec.get("taste", "none").split(",")
                    if x != "none")
    block = (f"Guidance distilled from {who}'s published writing about realistic evaluations (apply what fits this "
             f"seed):\n<guidance>\n{taste}\n</guidance>\n") if taste else ""
    kw = {"COMMON": common(n), "SEED": src["text"], "ORIGINAL": s["text"], "TASTE_BLOCK": block}
    if spec.get("guard"):
        kw["GUARD"] = (PROMPTS / spec["guard"]).read_text().strip()
    text, raw = rewrite(llm, fill(spec["prompt"], **kw), n)
    meta = {"taste": spec.get("taste", "none")}
    for stage in spec.get("then", []):          # optional further edit passes on the previous output
        kw2 = dict(kw, SEED=text)
        text, raw = rewrite(llm, fill(stage, **kw2), n)
    return {"seed_id": f"{s['seed_id']}@{arm}", "base_seed_id": s["seed_id"], "text": text, "variant": f"hc_{arm}",
            "split": s["split"], "len_ratio": round(len(text) / n, 2), "meta": meta}


def build(arm: str, split: str):
    out = SEEDS / f"{arm}_{split}.jsonl"
    if arm == "R0" and split == "dev":           # the frozen control from ../arms (same prompt, already written)
        out.write_text((TP / "arms" / "seeds" / "R0.jsonl").read_text())
        return
    llm = RP.Cache(ARMS[arm].get("model", "sonnet"))
    seeds = base_seeds(split)
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(build_one, llm, arm, s) for s in seeds]
        rows, errs = [], []
        for s, f in zip(seeds, futs):
            try:
                rows.append(f.result())
            except Exception as e:  # noqa: BLE001  a failed rewrite is logged and left out
                errs.append(f"{s['seed_id']}: {type(e).__name__}: {str(e)[:200]}")
    SEEDS.mkdir(exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    log(f"build {arm} {split}: cli_calls={llm.budget.calls} cache_hits={llm.hits} rows={len(rows)} errors={errs}")


# ---------- scoring ----------
def score(arm: str, split: str, ks):
    seeds = P.load_seeds(str(SEEDS / f"{arm}_{split}.jsonl"))
    base_text = {s["seed_id"]: s["text"] for s in P.load_seeds(str(BASE))}
    questions = P.probe_questions("placeholder")
    llm, rub, faithful_cache, lock = RP.Cache("haiku"), PJ.rubrics(), {}, threading.Lock()
    jobs = [(s, k) for s in seeds for k in ks]
    with ThreadPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(lambda j: RP.run_sample(llm, rub, j[0], base_text[P.base_of(j[0])], j[1], questions,
                                                   faithful_cache, lock), jobs))
    SCORES.mkdir(exist_ok=True)
    f = SCORES / f"{arm}_{split}.jsonl"
    old = [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []
    have = {(r["seed_id"], r["k"]) for r in rows}
    keep = [r for r in old if (r["seed_id"], r["k"]) not in have]
    slim = [{"seed_id": r["seed_id"], "base_seed_id": r["base_seed_id"], "k": r["k"],
             **{m: r.get(m) for m in KEEP if m in r}} for r in rows]
    f.write_text("".join(json.dumps(r) + "\n" for r in sorted(keep + slim, key=lambda r: (r["seed_id"], r["k"]))))
    ok = [r for r in rows if not r["error"]]
    log(f"score {arm} {split} ks={ks[0]}..{ks[-1]}: cli_calls={llm.budget.calls} cache_hits={llm.hits} "
        f"n_ok={len(ok)}/{len(rows)} " + " ".join(f"{m}={mean([r[m] for r in ok if r.get(m) is not None]):.3f}"
                                                  for m in METRICS))


# ---------- comparing ----------
def load_scores(arm: str, split: str, ks=None):
    rows = [json.loads(l) for l in (SCORES / f"{arm}_{split}.jsonl").read_text().splitlines()]
    return [r for r in rows if not r.get("error") and (ks is None or r["k"] in ks)]


def per_seed(rows, m):
    d = defaultdict(list)
    for r in rows:
        if r.get(m) is not None:
            d[r["base_seed_id"]].append(r[m])
    return {k: mean(v) for k, v in d.items()}


def compare_rows(base_rows, other_rows, metrics=METRICS):
    out = {}
    for m in metrics:
        a, b = per_seed(base_rows, m), per_seed(other_rows, m)
        shared = sorted(set(a) & set(b))
        if len(shared) < 2:
            continue
        diffs = [b[s] - a[s] for s in shared]
        out[m] = {"n": len(shared), "base": mean([a[s] for s in shared]), "other": mean([b[s] for s in shared]),
                  "diff": mean(diffs), "ci90": list(bootstrap_ci(diffs)),
                  "p_higher": prob_better(diffs, [0.0] * len(diffs)), "per_seed": dict(zip(shared, diffs))}
    return out


def table(pairs, split, ks_base=None, ks_other=None) -> str:
    head = "| A vs B | n | " + " | ".join(f"Δ{m}" for m in METRICS) + " |"
    lines = [head, "|---|---|" + "---|" * len(METRICS)]
    for a, b in pairs:
        c = compare_rows(load_scores(b, split, ks_base), load_scores(a, split, ks_other))
        cells = []
        for m in METRICS:
            x = c.get(m)
            d = 1 if m.startswith("pj_") else 3
            cells.append("n/a" if not x else f"{x['diff']:+.{d}f} [{x['ci90'][0]:+.{d}f}, {x['ci90'][1]:+.{d}f}]")
        n = max((x["n"] for x in c.values()), default=0)
        lines.append(f"| {a} vs {b} | {n} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def levels(arms, split) -> str:
    lines = ["| arm | n_ok | " + " | ".join(METRICS) + " |", "|---|---|" + "---|" * len(METRICS)]
    for a in arms:
        rows = load_scores(a, split)
        allr = [json.loads(l) for l in (SCORES / f"{a}_{split}.jsonl").read_text().splitlines()]
        lines.append(f"| {a} | {len(rows)}/{len(allr)} | " + " | ".join(
            f"{mean([r[m] for r in rows if r.get(m) is not None]):.3f}" for m in METRICS) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("build", "score", "compare", "levels"))
    ap.add_argument("arms", nargs="+")
    ap.add_argument("--split", default="dev")
    ap.add_argument("--ks", type=int, nargs="+", default=[0, 1, 2])
    a = ap.parse_args()
    if a.cmd == "build":
        for arm in a.arms:
            build(arm, a.split)
    elif a.cmd == "score":
        for arm in a.arms:
            score(arm, a.split, a.ks)
    elif a.cmd == "compare":
        base = a.arms[0]
        print(table([(o, base) for o in a.arms[1:]], a.split))
    else:
        print(levels(a.arms, a.split))


if __name__ == "__main__":
    main()
