"""taste_ranker replication on claude-hillclimb's rewrites (PREREG.md, Replication).

    python3 experiments/taste_petri/taste_ranker/replicate.py
"""
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as T
from autoresearch.llm import Budget

HC = HERE.parent / "hillclimb"
ARMS = ["R0", "H1", "H2", "H3", "H4", "H5"]
RANKERS = ["M0", "BOW", "CAR"]
T.PB.HERE = HERE


def texts():
    out = {}
    for a in ARMS:
        for l in (HC / "seeds" / f"{a}_dev.jsonl").read_text().splitlines():
            r = json.loads(l)
            out.setdefault(r["base_seed_id"], {})[a] = r["text"]
    return out


def measured():
    out = {}
    for a in ARMS:
        rows = {}
        for l in (HC / "scores" / f"{a}_dev.jsonl").read_text().splitlines():
            s = json.loads(l)
            if s["error"] or s.get("pj_realism") is None or s["k"] > 2:
                continue
            rows.setdefault(s["base_seed_id"], []).append(s)
        for seed, rs in rows.items():
            m = lambda k: sum(r[k] for r in rs) / len(rs)
            out.setdefault(seed, {})[a] = {"realism": m("pj_realism"), "validity": m("validity")}
    return out


def boot(xs, n=10000):
    rng = random.Random(0)
    bs = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return [bs[int(.05 * n)], bs[int(.95 * n)]], [bs[int(.025 * n)], bs[int(.975 * n)]]


def main():
    tx, meas = texts(), measured()
    seeds = [s for s in tx if len(meas.get(s, {})) >= 5]
    llm = T.PB.DevinCached("claude-sonnet-5-5-medium", budget=Budget(max_calls=120, max_seconds=4 * 3600))
    jobs = [(r, s, sh) for r in RANKERS for s in seeds for sh in range(2)]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda j: (j, T.rank(llm, j[0], j[1], {a: tx[j[1]][a] for a in meas[j[1]]}, j[2])), jobs))
    ranks = [{"ranker": r, "seed": s, "shuffle": sh, "ranks": rk} for (r, s, sh), rk in res]
    (HERE / "replication_ranks.json").write_text(json.dumps(ranks, indent=1))
    avg = {}
    for o in ranks:
        if o["ranks"]:
            for a, rk in o["ranks"].items():
                avg.setdefault((o["ranker"], o["seed"]), {}).setdefault(a, []).append(rk)

    def rho(rk, target, drop=()):
        out = {}
        for (r, s), d in avg.items():
            if r == rk:
                arms = [a for a in sorted(d) if a not in drop]
                out[s] = T.spearman([-sum(d[a]) / len(d[a]) for a in arms], [meas[s][a][target] for a in arms])
        return out
    out = {"n_seeds": len(seeds), "unparseable": sum(o["ranks"] is None for o in ranks)}
    for target, drop, tag in (("validity", (), "validity"), ("realism", (), "realism"), ("validity", ("H1",), "validity_noH1")):
        for rk in RANKERS:
            v = list(rho(rk, target, drop).values())
            out[f"{rk}:{tag}"] = {"mean": sum(v) / len(v), "ci90": boot(v)[0]}
        for rk in ("BOW", "CAR"):
            a, b = rho(rk, target, drop), rho("M0", target, drop)
            d = [a[s] - b[s] for s in a if s in b]
            c90, c95 = boot(d)
            out[f"{rk}-M0:{tag}"] = {"mean": sum(d) / len(d), "ci90": c90, "ci95": c95, "n": len(d)}
    for rk in RANKERS:
        g = {"realism": [], "validity": []}
        for (r, s), d in avg.items():
            if r == rk:
                best = min(d, key=lambda a: sum(d[a]) / len(d[a]))
                for t in g:
                    g[t].append(meas[s][best][t] - sum(v[t] for v in meas[s].values()) / len(meas[s]))
        out[f"top_pick:{rk}"] = {t: sum(v) / len(v) for t, v in g.items()}
        out[f"mean_rank_H1:{rk}"] = sum(sum(d["H1"]) / len(d["H1"]) for (r, s), d in avg.items() if r == rk and "H1" in d) / \
            max(1, sum(1 for (r, s), d in avg.items() if r == rk and "H1" in d))
    (HERE / "replication_results.json").write_text(json.dumps(out, indent=1))
    with open(HERE / "calls.log", "a") as f:
        f.write(f"replication rank: cli_calls={llm.budget.calls} (devin-cli claude-sonnet-5-5-medium)\n")
    for k, v in out.items():
        print(k, json.dumps(v))


if __name__ == "__main__":
    main()
