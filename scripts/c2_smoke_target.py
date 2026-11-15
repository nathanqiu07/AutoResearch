"""Smoke test for the Modal reasoning target (WS C2, PLAN 12.3 item 5).

Sends N single-turn samples from the metric_inflation scenario to the target
behind OPENAI_COMPAT_BASE_URL and checks that (1) raw reasoning comes back in
Sample.reasoning and (2) the A1 judge can read it. Writes
results/smoke/c2_target_<date>.json. Paid (Modal GPU time plus judge calls):
run only with the user's OK (AGENTS.md rule 5).

    python3 scripts/c2_smoke_target.py --n 5 --target openai-compat:Qwen/Qwen3-30B-A3B --judge anthropic:claude-haiku-4-5
    python3 scripts/c2_smoke_target.py --offline      # free plumbing check
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch.llm import Budget, OfflineLLM, get_llm  # noqa: E402
from autoresearch.research.measure import Measurer, Models, OfflineWorld  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--target", default="openai-compat:moonshotai/Kimi-K2.5")
    ap.add_argument("--generator", default="openai:gpt-6-luna")
    ap.add_argument("--judge", default="anthropic:claude-haiku-4-5")
    ap.add_argument("--max-cost", type=float, default=5.0)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    budget = Budget(max_cost_usd=a.max_cost)
    mk = (lambda s: OfflineLLM(budget)) if a.offline else (lambda s: get_llm("auto", s, budget))
    m = Models(generator=mk(a.generator), target=mk(a.target), judge=mk(a.judge))
    samples = Measurer(m, simulator=OfflineWorld(), workers=min(a.n, 5)).measure([], list(range(a.n)))
    ok = [s for s in samples if s.behavior != "error"]
    with_reasoning = [s for s in ok if s.reasoning.strip()]
    a1 = [s.verbalized for s in ok]
    passed = a.offline or (len(ok) == a.n and len(with_reasoning) == a.n)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    rec = {"date": datetime.date.today().isoformat(), "code_version": commit, "offline": a.offline,
           "target": a.target, "judge": a.judge, "n": a.n, "n_ok": len(ok), "n_with_reasoning": len(with_reasoning),
           "a1_verbalized": a1, "errors": [s.error for s in samples if s.error], "passed": passed,
           "compute": budget.summary() if hasattr(budget, "summary") else {},
           "examples": [{"reasoning": s.reasoning[:800], "response": s.response[:400]} for s in with_reasoning[:2]]}
    out = Path(a.out or f"results/smoke/c2_target_{rec['date']}{'_offline' if a.offline else ''}.json")
    if not a.offline:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("n", "n_ok", "n_with_reasoning", "passed")}),
          "" if a.offline else f"-> {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
