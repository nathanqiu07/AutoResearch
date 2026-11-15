"""Stage 3 of replay_multi.py, resumable: reuses multi_stage1/2 and multi_rewrites.json; retries judge errors."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
import replay_frozen as R
import replay_multi as M

def judge_retry(reasoning):
    for _ in range(4):
        try:
            return R.judge(reasoning)
        except Exception as e:
            err = str(e)
    return {"aware_majority": None, "judge_error": err}
R.judge = judge_retry

s1 = json.load(open("multi_stage1.json")); s2 = json.load(open("multi_stage2.json")); rwj = json.load(open("multi_rewrites.json"))
turn = {r["file"]: r["aware_turn"] for r in s1 if r.get("aware_turn")}
kept = sorted({r["case"] for r in s2 if sum(x["strict"] for x in s2 if x["case"] == r["case"]) >= M.KEEP})
base = {k: R.prefix(json.load(open(k))["transcript"], turn[k]) for k in kept}
def apply(msgs, j):
    um = j.get("user_messages", {})
    return [{"role": "system", "content": j["system_prompt"]}] + [
        {"role": m["role"], "content": um.get(m["content"], m["content"]) if m["role"] == "user" else m["content"]} for m in msgs[1:]]
tasks = [(k, "stock", base[k], i) for k in kept for i in range(M.N)]
tasks += [(k, p, apply(base[k], rwj[f"{k}|{p}"]), i) for k in kept for p in R.PROFILES for i in range(M.N)]
with ThreadPoolExecutor(120) as ex:
    s3 = list(ex.map(M.run, tasks))
json.dump(s3, open("multi_stage3.json", "w"), indent=1)
seeds = {r["file"]: r["seed_id"] for r in s1}
C = ["stock"] + R.PROFILES
for k in kept:
    print(seeds[k], k.split("/")[-1][:8], *[f"{c}={sum(r['strict'] for r in s3 if r['case']==k and r['condition']==c)}/{M.N}" for c in C])
for c in C:
    rs = [r for r in s3 if r["condition"] == c]
    print(c, "strict", sum(r["strict"] for r in rs), "literal", sum(bool(r["literal"]) for r in rs), "of", len(rs),
          "empty", sum(not r["reasoning"].strip() for r in rs), "judge_err", sum("judge_error" in r["judge"] for r in rs))
