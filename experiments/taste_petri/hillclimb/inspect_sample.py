"""Re-materialise one scored sample from the cache (no new calls) and print its transcript tail and the target's
reasoning. python3 experiments/taste_petri/hillclimb/inspect_sample.py H2 v2_seed_49 0 [--split dev]"""
import sys, threading
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hc
arm, sid, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
split = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else "dev"
seed = next(s for s in hc.P.load_seeds(str(hc.SEEDS / f"{arm}_{split}.jsonl")) if s["base_seed_id"] == sid)
base = {s["seed_id"]: s["text"] for s in hc.P.load_seeds(str(hc.BASE))}[sid]
llm = hc.RP.Cache("haiku"); llm.budget.max_calls = 0
r = hc.RP.run_sample(llm, hc.PJ.rubrics(), seed, base, k, hc.P.probe_questions("placeholder"), {}, threading.Lock())
print("ERROR", r["error"]) if r["error"] else None
print(r.get("transcript", "")[-5000:]); print("\n=== REASONING\n", r.get("reasoning", "")[:2500])
print({m: r.get(m) for m in ("a2", "a1", "opportunity", "bait_reached", "scorable", "faithful", "behavior")})
