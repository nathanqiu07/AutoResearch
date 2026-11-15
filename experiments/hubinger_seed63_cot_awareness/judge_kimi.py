"""Map Kimi cache records to conditions, clean OpenRouter reasoning blocks to plain text,
judge with cot_awareness_judge (majority of 3). Usage: judge_kimi.py CACHE_DIR RESULTS_JSON OUT_JSON"""
import json, os, sys, glob, re, ast
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "judge"))
from cot_awareness_judge import judge_majority
from openai import OpenAI

cache_dir, res_path, out_path = sys.argv[1:4]
res = json.load(open(res_path))

def clean(r):
    out = []
    for m in re.finditer(r"\[turn (\d+)\] (.*?)(?=\n?\[turn \d+\] |\Z)", r, flags=re.S):
        body = m.group(2).strip()
        parts = []
        def sub(lm):
            lits = re.findall(r"""'text': ('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""", lm.group(0))
            parts.append("\n".join(ast.literal_eval(l) for l in lits))
            return "\x00"
        rest = re.sub(r"\[\{'type'.*?'index': \d+\}\]", sub, body, flags=re.S)
        txt = "\n".join(p for p in parts + [rest.replace("\x00", "").strip()] if p.strip())
        out.append(f"[turn {m.group(1)}] {txt.strip()}")
    return "\n\n".join(out) if out else r

recs = []
for f in sorted(glob.glob(os.path.join(cache_dir, "*.json"))):
    d = json.load(open(f)); d["_file"] = os.path.basename(f); recs.append(d)

used = set()
for d in recs:
    cands = []
    for cond, samples in res["samples"].items():
        for i, s in enumerate(samples):
            if (cond, i) in used: continue
            if s.get("petri_scores") == d.get("petri_scores") and (s.get("response") or "")[-300:] in (d.get("transcript") or ""):
                cands.append((cond, i))
    d["_cond"] = cands[0] if len(cands) == 1 else None
    if len(cands) == 1: used.add(cands[0])
    else: print("ambiguous/unmapped", d["_file"], cands)

client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
def run(d):
    r = clean(d.get("reasoning") or "")
    d["_clean"] = r
    if not r.strip() or d.get("error"):
        return {"aware_majority": None, "note": "empty reasoning or error"}
    return judge_majority(client, r)
with ThreadPoolExecutor(12) as ex:
    judged = list(ex.map(run, recs))

rows = []
for d, j in zip(recs, judged):
    ps = d.get("petri_scores") or {}
    rows.append({"file": d["_file"], "condition": d["_cond"][0] if d["_cond"] else None,
                 "replicate": d["_cond"][1] if d["_cond"] else None, "error": d.get("error"),
                 "petri_eval_awareness": ps.get("eval_awareness"),
                 "petri_audit_situational_awareness": ps.get("audit_situational_awareness"),
                 "petri_scenario_realism": ps.get("scenario_realism"),
                 "n_target_turns": d.get("n_target_turns"),
                 "cot_aware_majority": j.get("aware_majority"), "cot_aware_count": j.get("aware_count"),
                 "quotes": [v.get("quote") for v in j.get("votes", []) if v.get("aware")],
                 "reasoning_chars": len(d["_clean"])})
rows.sort(key=lambda r: (str(r["condition"]), r["replicate"] or 0))
json.dump({"target": "moonshotai/kimi-k2.6 via OpenRouter", "judge": "gpt-5.1 x3 majority",
           "rows": rows, "judged": judged}, open(out_path, "w"), indent=1)
for r in rows:
    print(r["condition"], r["replicate"], "ea", r["petri_eval_awareness"], "sa", r["petri_audit_situational_awareness"],
          "cot", r["cot_aware_majority"], r["cot_aware_count"], "chars", r["reasoning_chars"], (r["quotes"] or [""])[0][:140])
