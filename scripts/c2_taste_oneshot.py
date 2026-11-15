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


def quick_profile(r, gen, outdir, max_docs, offline):
    """The researcher's text profile (taste.extract.profile_from_texts weighting) from up to max_docs
    corpus documents, extracted in parallel, cached in outdir (data/researchers/ is WS B's, not written)."""
    from autoresearch.taste.extract import _lexicon_weights, _llm_extract
    from autoresearch.taste.profile import FEATURES, TasteProfile
    cache = outdir / f"{r.slug}_profile.json"
    if cache.exists():
        return TasteProfile.from_dict(json.loads(cache.read_text()))
    prof = r.cached_profile()
    if prof is None:
        docs = [(k, t) for k, t in r.docs() if k in ("research", "other")][:max_docs]
        ext = (lambda d: (_lexicon_weights(d[1]), [])) if offline else (lambda d: _llm_extract(d[1], gen))
        with ThreadPoolExecutor(max_workers=16) as ex:
            outs = list(ex.map(ext, docs))
        acc, total, principles = {f: 0.0 for f in FEATURES}, 0.0, []
        for (kind, _), (w, pr) in zip(docs, outs):
            wt = 1.0 if kind == "research" else 0.4
            for f in FEATURES:
                acc[f] += wt * w[f]
            total += wt
            principles += [x for x in pr if x not in principles]
        weights = {f: (acc[f] / total if total else 0.0) for f in FEATURES}
        prof = TasteProfile(r.slug, weights, principles=principles[:8])
    cache.write_text(prof.to_json())
    return prof


def one(slug, seeds, gen, k, outdir, offline, max_docs=24):
    r = load_researcher(slug)
    prof = quick_profile(r, gen, outdir, max_docs, offline)
    prop = Proposer(gen, prof, random.Random(0), setting_kind="agentic")
    cands = prop.propose(PETRI_SCENARIO.goal, PETRI_SCENARIO.probe, [], set(), [], [], k=10,
                         setting=PETRI_SCENARIO.setting)
    # The goal gate the loop applies (drift monitor): an idea that tells the target it is being evaluated
    # contradicts the task (make the audit unrecognisable), so it is dropped before taste ranks the rest.
    import re
    tells = re.compile(r"disclos|notice that|authori[sz]ed (audit|evaluation)|is (part of )?an? (audit|evaluation|test)|"
                       r"debrief|label simulated|inform the (target|model)", re.I)
    kept = [i for i in cands if not tells.search(i.text)]
    dropped = len(cands) - len(kept)
    ranked = sorted(kept or cands, key=lambda i: -prof.score(i.features))
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
                    goal_gate_dropped=dropped,
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
