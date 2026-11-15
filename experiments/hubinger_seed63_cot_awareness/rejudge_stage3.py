"""Judge the saved stage-3 samples (the first pass's retry wrapper recursed; samples were unaffected)."""
import json
from concurrent.futures import ThreadPoolExecutor
import replay_frozen as R
import replay_multi as M
s3 = json.load(open("multi_stage3.json")); s1 = json.load(open("multi_stage1.json"))
orig = R.judge
def go(r):
    if "judge_error" not in r["judge"]:
        return r
    err = None
    for _ in range(4):
        try:
            j = orig(r["reasoning"]); break
        except Exception as e:
            err = str(e); j = {"aware_majority": None, "judge_error": err}
    r["judge"] = j; r["literal"] = j.get("aware_majority"); r["strict"] = bool(M.strict(j)); return r
with ThreadPoolExecutor(25) as ex:
    s3 = list(ex.map(go, s3))
json.dump(s3, open("multi_stage3.json", "w"), indent=1)
seeds = {r["file"]: r["seed_id"] for r in s1}; C = ["stock"] + R.PROFILES
for k in sorted({r["case"] for r in s3}):
    print(seeds[k], k.split("/")[-1][:8], *[f"{c}={sum(r['strict'] for r in s3 if r['case']==k and r['condition']==c)}/{M.N}" for c in C])
for c in C:
    rs = [r for r in s3 if r["condition"] == c]
    print(c, "strict", sum(r["strict"] for r in rs), "literal", sum(bool(r["literal"]) for r in rs), "of", len(rs),
          "judge_err", sum("judge_error" in r["judge"] for r in rs))
