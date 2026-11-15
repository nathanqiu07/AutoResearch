"""One taste arm per user model, without the measurement loop (deadline version, WS C2).

For each researcher: load (or build) their taste profile, let the taste-steered proposer write
candidate realism interventions for the agentic Petri setting, rank them by the profile and keep the
top K as the design, then apply that design to the screened seeds exactly as the loop's export does
(--petri-rewrite both: seed rewrite + one auditor guidance for all seeds). The result is the taste
system's ONE-SHOT pick (taste at D1 only, no audits to validate it). Label it that way: it is not
the loop's validated best design (that's evan_hubinger's taste_real from scripts/c2_loop_evan.sh).

    python3 scripts/c2_taste_oneshot.py --researchers marius_hobbhahn ethan_cai samuel_bowman \
        --seeds data/petri/seeds_screened.jsonl --outdir runs/petri/taste_oneshot
Writes <outdir>/<slug>.jsonl (AuditSeeds, condition taste_<slug>) and <outdir>/<slug>_auditor_prompt.txt.
"""
import argparse
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch.llm import Budget, OfflineLLM, get_llm  # noqa: E402
from autoresearch.research.ideas import Proposer  # noqa: E402
from autoresearch.research.measure import Models  # noqa: E402
from autoresearch.research.models_config import load_models_config  # noqa: E402
from autoresearch.research.petri_measure import (PETRI_SCENARIO, PetriMeasurer, load_audit_seeds,  # noqa: E402
                                                 stock_auditor_prompt, with_guidance)
from autoresearch.taste.researcher import load_researcher  # noqa: E402


def one(slug, seeds, gen, k, outdir, offline):
    r = load_researcher(slug)
    prof = r.cached_profile()
    if prof is None:
        prof, _ = r.build_profile(gen, holdout=0)
    prop = Proposer(gen, prof, random.Random(0), setting_kind="agentic")
    cands = prop.propose(PETRI_SCENARIO.goal, PETRI_SCENARIO.probe, [], set(), [], [], k=8,
                         setting=PETRI_SCENARIO.setting)
    ranked = sorted(cands, key=lambda i: -prof.score(i.features))
    design = [i.text for i in ranked[:k]]
    off = OfflineLLM()
    pm = PetriMeasurer(Models(generator=gen, target=off, judge=off), seeds)
    guidance = "(offline guidance)" if offline else pm.auditor_guidance(design)
    prompt = with_guidance(stock_auditor_prompt(), guidance or "")
    rows = []

    def rw(i_s):
        i, s = i_s
        text = ("(offline) " + s["text"]) if offline else pm.rewrite_seed(s, design, random.Random(i))
        return dict(s, text=text or s["text"], variant="ours", condition=f"taste_{slug}", design=design,
                    taste="one-shot (D1 ranking, no measurement loop)", rewrite_ok=bool(text))
    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = list(ex.map(rw, enumerate(seeds)))
    (outdir / f"{slug}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
    (outdir / f"{slug}_auditor_prompt.txt").write_text(prompt)
    return slug, design, sum(x["rewrite_ok"] for x in rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--researchers", nargs="+", required=True)
    ap.add_argument("--seeds", default="data/petri/seeds_screened.jsonl")
    ap.add_argument("--outdir", default="runs/petri/taste_oneshot")
    ap.add_argument("--k", type=int, default=3, help="interventions in the design")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    budget = Budget(max_cost_usd=5.0)
    gen = OfflineLLM(budget) if a.offline else get_llm("auto", load_models_config()["roles"]["generator"], budget)
    seeds = load_audit_seeds(a.seeds)
    with ThreadPoolExecutor(max_workers=len(a.researchers)) as ex:
        res = list(ex.map(lambda s: one(s, seeds, gen, a.k, out, a.offline), a.researchers))
    for slug, design, ok in res:
        print(f"{slug}: {ok}/{len(seeds)} seeds rewritten; design = {design}")
    print("compute:", budget.summary())


if __name__ == "__main__":
    main()
