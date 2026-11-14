"""Command line interface.

  python -m autoresearch researchers
  python -m autoresearch taste --researcher demo_realist
  python -m autoresearch run --task eval_awareness --researcher demo_realist
  python -m autoresearch benchmark --researcher demo_realist --seeds 0 1 2
  python -m autoresearch scrape --name "Jane Doe" --arxiv "Doe, Jane" --url https://...
  python -m autoresearch label --memory runs/memory --researcher my_slug
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .benchmark import CONDITIONS, format_table, run_benchmark
from .llm import Budget, get_llm
from .loop import LoopConfig, Researcher
from .memory import ResearchMemory
from .taste import TasteProfile, list_researchers, load_researcher, prediction_accuracy
from .tasks import TASKS, get_task


def _profile(args, llm):
    if not args.researcher:
        return None, None
    r = load_researcher(args.researcher)
    prof = r.cached_profile()
    if prof is None:
        prof, _ = r.build_profile(llm, holdout=0)
    hidden = os.path.join(r.root, "hidden_weights.json")
    judge = TasteProfile(r.slug, json.load(open(hidden))) if os.path.exists(hidden) else prof
    return prof, judge


def cmd_researchers(args):
    for s in list_researchers():
        print(s)


def cmd_taste(args):
    llm = get_llm(args.llm, args.model)
    r = load_researcher(args.researcher)
    report = r.ablation_report(llm)
    print("Taste-prediction accuracy on held-out choices by source:")
    for k, v in report.items():
        print(f"  {k:<13} {v}")
    prof, test = r.build_profile(llm, holdout=0)
    r.save_profile(prof)
    print("\nSaved profile:\n" + prof.to_json())


def cmd_run(args):
    budget = Budget(max_calls=args.max_calls, max_seconds=args.max_seconds)
    llm = get_llm(args.llm, args.model, budget)
    prof, judge = _profile(args, llm)
    memory = ResearchMemory(args.memory)
    cfg = LoopConfig(iterations=args.iterations, samples=args.samples, seed=args.seed,
                     use_taste=not args.no_taste, use_memory=not args.no_memory,
                     use_drift=not args.no_drift)
    from .integrations.exa import get_scout
    from .integrations.shared_memory import get_shared_memory
    scout = None if args.no_web else get_scout(llm, cache_dir=os.path.join(args.memory, "exa_cache"))
    shared = None if args.no_shared else get_shared_memory(args.shared_path, run_tag=args.worker)
    print(f"agents: web scout={'exa' if scout else 'off (set EXA_API_KEY)'} | shared memory="
          f"{shared.backend if shared else 'off'}")
    rep = Researcher(get_task(args.task), llm, memory, prof, cfg, log_dir=args.log_dir,
                     scout=scout, shared=shared, worker=args.worker).run()
    print(f"task={rep.task} run={rep.run_id} best_score={rep.best_score:.3f}")
    print("best_config:", json.dumps(rep.best_config))
    print("metrics:", json.dumps({k: round(v, 3) for k, v in rep.best_metrics.items()}))
    print("drift events:", len(rep.drift_events), "| compute:", rep.compute)
    for i in rep.insights:
        print(" *", i)
    if rep.shared_memory:
        print("shared memory:", json.dumps(rep.shared_memory))
    for o in rep.discovered_options:
        print(f" + discovered {o['knob']}={o['option']} from {o.get('source_url')}")
    if rep.sources:
        print(f"web sources used ({len(rep.sources)}):")
        for s in rep.sources[:25]:
            print(f"   [{s['used_for']}] {s['title'][:70]} <{s['url']}> {s['published'] or ''}")


def cmd_benchmark(args):
    llm = get_llm(args.llm, args.model)
    prof, judge = _profile(args, llm)
    res = run_benchmark(args.tasks, args.seeds, prof, judge, args.iterations, args.samples,
                        args.llm, args.model, args.conditions)
    print(format_table(res["summary"]))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        json.dump(res, open(args.out, "w"), indent=1)
        print("wrote", args.out)


def cmd_scrape(args):
    from .taste.scrape import import_x_archive, scrape_arxiv, scrape_url, slugify
    from .taste.researcher import DEFAULT_ROOT
    root = os.path.join(DEFAULT_ROOT, slugify(args.name))
    paths = []
    if args.arxiv:
        paths += scrape_arxiv(args.arxiv, root, args.max_results)
    for u in args.url or []:
        paths.append(scrape_url(u, root, "research"))
    for u in args.other_url or []:
        paths.append(scrape_url(u, root, "other"))
    if args.x_archive:
        paths += import_x_archive(args.x_archive, root)
    print(f"saved {len(paths)} documents under {root}")


def cmd_research(args):
    """Open-ended research loop (v2) with separate generator/target/judge."""
    from .llm import get_llm
    from .research.corpus import load_corpus
    from .research.ideas import Proposer
    from .research.loop import Calibration, OpenResearcher, ResearchConfig, write_report
    from .research.measure import Measurer, Models, OfflineWorld
    import random as _r
    budget = Budget(max_calls=args.max_calls, max_seconds=args.max_seconds)
    mk = lambda m: get_llm(args.llm, m, budget)  # noqa: E731
    models = Models(generator=mk(args.generator), target=mk(args.target), judge=mk(args.judge))
    prof, _ = _profile(args, models.judge)
    from .research.measure import SCENARIOS
    scenario = SCENARIOS[args.scenario]
    corpus = [] if args.no_discriminator else load_corpus(keywords=scenario.corpus_keywords)
    matched = bool(corpus) and len(corpus) < len(load_corpus())
    measurer = Measurer(models, scenario=scenario, real_corpus=corpus, workers=args.workers,
                        simulator=OfflineWorld())
    scout = shared = None
    if not args.no_web:
        from .integrations.exa import get_scout
        scout = get_scout(models.judge, cache_dir=os.path.join(args.memory, "exa_cache"))
    if not args.no_shared:
        from .integrations.shared_memory import get_shared_memory
        shared = get_shared_memory(os.path.join(args.memory, "shared.jsonl"))
    cfg = ResearchConfig(iterations=args.iterations, samples=args.samples, proposals=args.proposals,
                         evals_per_iter=args.evals_per_iter, use_taste=not args.no_taste,
                         use_memory=not args.no_memory, use_web=not args.no_web, seed=args.seed,
                         max_calls=args.max_calls, faithfulness_samples=args.faithfulness_samples)
    who = prof.researcher if prof else "none"
    cal = Calibration(os.path.join(args.memory, "taste_calibration.json"), who)
    print(f"models: generator={args.generator} target={args.target} judge={args.judge} ({args.llm}) | "
          f"scenario={scenario.name} | researcher={who} | real corpus={len(corpus)} msgs "
          f"({'topic-matched' if matched else 'NOT topic-matched'}) | web={'exa' if scout else 'off'} | "
          f"shared={getattr(shared, 'backend', 'off')}")
    r = OpenResearcher(measurer, Proposer(models.generator, prof, _r.Random(args.seed), gate_llm=models.judge),
                       ResearchMemory(args.memory), prof, cfg, scenario=scenario, scout=scout, shared=shared,
                       calibration=cal, budget=budget)
    rep = r.run()
    path = write_report(rep, args.out)
    b, f = rep["baseline"], rep["best"]
    print(f"baseline score {b['score']:.3f} (awareness {b['awareness']:.3f}) -> best {f['score']:.3f} "
          f"(awareness {f['awareness']:.3f}), P(better)={rep['p_best_beats_baseline']:.2f}")
    print(f"validated findings: {sum(x['status'] == 'validated' for x in rep['findings'])} / {len(rep['findings'])} tested")
    print(f"taste: alignment={rep['taste']['alignment']} rho={rep['taste']['reliability_rho']:+.2f} "
          f"weight={rep['taste']['effective_weight']:.2f} | compute {rep['compute']}")
    fa = rep.get("faithfulness") or {}
    for k in ("baseline", "best"):
        if k in fa:
            print(f"faithfulness {k}: {fa[k]['misbehavior']} rate as-is={fa[k]['rate_plain']} "
                  f"with eval notice={fa[k]['rate_eval_notice']} (n={fa[k]['n']})")
    print("report:", path)


def cmd_corpus(args):
    from .research.corpus import fetch_hf_rows, wildchat_first_user
    path = fetch_hf_rows(args.dataset, args.config, args.split, args.n, wildchat_first_user, name=args.name)
    print("wrote", path)


def cmd_label(args):
    """Show the loop's past decisions and record what you would have chosen.
    Labels feed taste-alignment and become new structured choice data."""
    memory = ResearchMemory(args.memory)
    r = load_researcher(args.researcher)
    out = open(os.path.join(r.root, "choices.jsonl"), "a")
    pending = [d for d in memory.decisions if d.get("human_choice") is None and len(d["options"]) >= 2]
    for d in pending[: args.limit]:
        print(f"\n[{d['task']} iter {d['iter']}] which experiment next?")
        for i, o in enumerate(d["options"][:2]):
            print(f"  {'ab'[i]}) {o['change']}")
        ans = input("a/b/skip> ").strip().lower()
        if ans in ("a", "b"):
            a, b = d["options"][0], d["options"][1]
            out.write(json.dumps({"a": a["features"], "b": b["features"], "chosen": ans,
                                  "context": f"{d['task']}: {a['change']} vs {b['change']}"}) + "\n")
    out.close()


def main(argv=None):
    p = argparse.ArgumentParser(prog="autoresearch")
    p.add_argument("--llm", default="auto", choices=["auto", "offline", "anthropic", "claude-cli"])
    p.add_argument("--model", default="claude-sonnet-5-5")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("researchers").set_defaults(fn=cmd_researchers)
    t = sub.add_parser("taste"); t.add_argument("--researcher", required=True); t.set_defaults(fn=cmd_taste)
    r = sub.add_parser("run")
    r.add_argument("--task", default="eval_awareness", choices=sorted(TASKS))
    r.add_argument("--researcher")
    r.add_argument("--memory", default="runs/memory")
    r.add_argument("--log-dir", default="runs/logs")
    r.add_argument("--iterations", type=int, default=20)
    r.add_argument("--samples", type=int, default=8)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--max-calls", type=int, default=2000)
    r.add_argument("--max-seconds", type=float, default=3600)
    r.add_argument("--shared-path", default="runs/shared_memory.jsonl",
                   help="local shared-memory file (used when PAST_API_KEY is unset)")
    r.add_argument("--worker", default="local")
    for f in ("--no-taste", "--no-memory", "--no-drift", "--no-web", "--no-shared"):
        r.add_argument(f, action="store_true")
    r.set_defaults(fn=cmd_run)
    b = sub.add_parser("benchmark")
    b.add_argument("--tasks", nargs="+", default=sorted(TASKS))
    b.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    b.add_argument("--conditions", nargs="+", default=list(CONDITIONS), choices=list(CONDITIONS))
    b.add_argument("--researcher")
    b.add_argument("--iterations", type=int, default=8)
    b.add_argument("--samples", type=int, default=8)
    b.add_argument("--out", default="runs/benchmark.json")
    b.set_defaults(fn=cmd_benchmark)
    s = sub.add_parser("scrape")
    s.add_argument("--name", required=True)
    s.add_argument("--arxiv", help="arXiv author query, e.g. 'Doe, Jane'")
    s.add_argument("--url", nargs="*"); s.add_argument("--other-url", nargs="*")
    s.add_argument("--x-archive", help="path to tweets.js from an X data export")
    s.add_argument("--max-results", type=int, default=25)
    s.set_defaults(fn=cmd_scrape)
    rs = sub.add_parser("research", help="open-ended research loop (v2)")
    rs.add_argument("--researcher")
    rs.add_argument("--scenario", default="metric_inflation", choices=["metric_inflation", "sycophancy_code"])
    rs.add_argument("--faithfulness-samples", type=int, default=8)
    rs.add_argument("--generator", default="sonnet")
    rs.add_argument("--target", default="haiku", help="model under study; keep it different from the judge")
    rs.add_argument("--judge", default="sonnet")
    rs.add_argument("--iterations", type=int, default=6)
    rs.add_argument("--samples", type=int, default=6)
    rs.add_argument("--proposals", type=int, default=6)
    rs.add_argument("--evals-per-iter", type=int, default=2)
    rs.add_argument("--workers", type=int, default=4)
    rs.add_argument("--seed", type=int, default=0)
    rs.add_argument("--max-calls", type=int, default=600)
    rs.add_argument("--max-seconds", type=float, default=7200)
    rs.add_argument("--memory", default="runs/research_memory")
    rs.add_argument("--out", default="results/research")
    for f in ("--no-taste", "--no-memory", "--no-web", "--no-shared", "--no-discriminator"):
        rs.add_argument(f, action="store_true")
    rs.set_defaults(fn=cmd_research)
    co = sub.add_parser("corpus", help="fetch real user messages for the discriminator")
    co.add_argument("--dataset", default="allenai/WildChat-1M")
    co.add_argument("--config", default="default")
    co.add_argument("--split", default="train")
    co.add_argument("--n", type=int, default=200)
    co.add_argument("--name", default="wildchat_sample")
    co.set_defaults(fn=cmd_corpus)
    l = sub.add_parser("label")
    l.add_argument("--memory", default="runs/memory"); l.add_argument("--researcher", required=True)
    l.add_argument("--limit", type=int, default=20); l.set_defaults(fn=cmd_label)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
