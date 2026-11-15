"""Real-material arms v2 on the haiku proxy. Reuses ../real_material/{rm_proxy,make_seeds,summarize}.py unchanged,
pointed at this directory and at the v2 material (material_v2.install()).

    python3 experiments/taste_petri/real_material_v2/run_v2.py docs [--devin]    # modernise docs (sonnet, cached;
                                                                                 # --devin: through devin -p)
    python3 experiments/taste_petri/real_material_v2/run_v2.py seeds             # RM3b, RM23 (no model calls)
    python3 experiments/taste_petri/real_material_v2/run_v2.py run RM3b --samples 2
    python3 experiments/taste_petri/real_material_v2/run_v2.py summary k2

Arms (both built on R0's text, like v1):
  RM3b  v1's RM3 with docs v2: scaffold where one fits, plus the present-day documents; India docs for 28, DRC for 70.
  RM23  RM3b plus v1's real trajectory prefixes (48, 63, 21, 73, 17): the RM2 material and the docs together.
Two changes to the proxy, both for v1's misses on the non-scaffold seeds (28, 66, 70):
  - auditor_prompt: v1's document rule never reached the auditor on those seeds (a string replace that didn't match);
    v2 inserts it;
  - _expand: if the auditor still used no <<DOC:id>> placeholder, the documents go at the top of the first tool result
    (recorded per sample in flags.docs_forced).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TP = HERE.parent
sys.path.insert(0, str(HERE))
import material_v2 as V

V.install()
import make_seeds as MS
import rm_proxy as RP
import summarize as SU

M = V.M
RP.HERE = HERE
RP.CALLS_LOG = HERE / "calls.log"
RP.READ_CACHES = [TP / "real_material" / "cache", TP / "proxy" / "cache", TP / "arms" / "cache"]
RP.BUDGET = 350
SU.HERE = HERE
SU.ARMS = ["RM3b", "RM23"]
_expand_v1 = RP._expand


def _expand(turns, mat, sc, flags):
    turns = _expand_v1(turns, mat, sc, flags)
    docs = mat.get("docs") or []
    if docs and not flags["docs_used"]:
        tr = next((t for t in turns if t["role"] == "tool_result"), None)
        if tr is None:
            flags["docs_missing"] = True
        else:
            tr["content"] = "\n\n".join(M.doc(d) for d in docs) + "\n\n" + tr["content"]
            flags["docs_forced"] = list(docs)
    return turns


RP._expand = _expand
_auditor_prompt_v1 = RP.auditor_prompt


def auditor_prompt(seed, k, target_name):
    """v1 meant to add the document rule for seeds without a scaffold by replacing "\nReturn the JSON only.", but in
    proxy_eval.AUDITOR_FORMAT that sentence follows a space, so the rule never reached the auditor (seeds 28, 66, 70)."""
    p = _auditor_prompt_v1(seed, k, target_name)
    mat = seed.get("material") or {}
    if mat.get("docs") and not mat.get("scaffold") and "<<DOC:" not in p.split("# Output format")[-1]:
        rule = RP.PLAIN_EXTRA.replace("%RULES%", RP.DOC_RULE.format(ids=", ".join(mat["docs"])))
        head, sep, tail = p.rpartition(" Return the JSON only.")
        assert sep, "AUDITOR_FORMAT changed"
        p = head + rule + "\nReturn the JSON only." + tail
    return p


RP.auditor_prompt = auditor_prompt


def devin_llm():
    """Sonnet through `devin -p` (billed to Devin), with the same on-disk prompt cache as RP.Cache."""
    from autoresearch.llm import Budget, DevinCLILLM

    class Cached(DevinCLILLM):
        def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
            f = HERE / "cache" / (hashlib.sha256(json.dumps([self.model, system, prompt]).encode()).hexdigest()[:32] + ".json")
            if f.exists():
                return json.loads(f.read_text())["out"]
            out = super().complete(prompt, system=system, max_tokens=max_tokens)
            f.write_text(json.dumps({"model": self.model, "out": out}))
            return out
    return Cached("claude-sonnet-5-5-medium", budget=Budget(max_calls=40, max_seconds=3600))


def modernise(devin=False):
    llm = devin_llm() if devin else RP.Cache("sonnet")
    ids = sorted({d for f in V.FIT.values() for d in f["docs"]})

    def one(did):
        fiction = (V.NEW_NAMES.format(extra=V.NEW_FICTION[did]) if did in V.NEW_DOCS else V.KEEP_NAMES)
        raw = llm.complete(V.MODERNISE.format(today=V.TODAY, lo=V.WINDOW[0], hi=V.WINDOW[1], fiction=fiction,
                                              text=V.source_text(did)), max_tokens=4000)
        m = re.search(r"<doc>\n?(.*?)</doc>", raw, re.DOTALL)
        if m and did in V.CLEANUP:
            raw = llm.complete(V.CLEANUP_PROMPT.format(instruction=V.CLEANUP[did], text=m.group(1)), max_tokens=4000)
            m = re.search(r"<doc>\n?(.*?)</doc>", raw, re.DOTALL)
        if not m:
            raise ValueError(f"{did}: no <doc>")
        text, n_fixed = V.fix_weekdays(m.group(1).rstrip() + "\n")
        V.path(did).write_text(text)
        return did, {"chars_in": len(V.source_text(did)), "chars_out": len(text), "weekdays_fixed": n_fixed,
                     **V.check(text), "v1_check": V.check(V.source_text(did))}
    with ThreadPoolExecutor(4) as ex:
        checks = dict(ex.map(one, ids))
    (HERE / "material" / "checks.json").write_text(json.dumps(checks, indent=1))
    RP.log(f"modernise docs: cli_calls={llm.budget.calls} ({'devin-cli claude-sonnet-5-5-medium' if devin else 'sonnet'})")
    for did, c in checks.items():
        print(did, {k: c[k] for k in ("latest_date", "dates_after_today", "dates_before_2024", "export_headers",
                                      "old_tech", "weekdays_fixed")})


def build(arm, s):
    base = s["base_seed_id"]
    fit = V.FIT[base]
    sc, pid, docs = fit["scaffold"], fit["prefix"] if arm == "RM23" else None, fit["docs"]
    paras = ([MS.para_scaffold(sc)] if sc else []) + ([MS.para_prefix(M.prefix(pid, sc))] if pid else []) \
        + ([MS.para_docs(docs)] if docs else [])
    text = s["text"] + ("\n\n" + "\n\n".join(paras) if paras else "")
    return {"seed_id": f"{base}@{arm}", "base_seed_id": base, "text": text, "variant": f"arm_{arm}", "split": "dev",
            "material": {"scaffold": sc, "prefix": pid, "docs": docs}, "fit_note": fit.get("fit_note", ""),
            "changed_vs_R0": bool(paras), "len_ratio_vs_R0": round(len(text) / len(s["text"]), 2), "meta": {}}


def seeds():
    (HERE / "seeds").mkdir(exist_ok=True)
    for arm in SU.ARMS:
        rows = [build(arm, s) for s in MS.R0]
        (HERE / "seeds" / f"{arm}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(arm, "changed:", [r["base_seed_id"] for r in rows if r["changed_vs_R0"]])


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "docs":
        modernise("--devin" in rest)
    elif cmd == "seeds":
        seeds()
    elif cmd == "run":
        k = int(rest[rest.index("--samples") + 1]) if "--samples" in rest else 1
        for arm in [a for a in rest if not a.startswith("--") and not a.isdigit()]:
            (HERE / "runs").mkdir(exist_ok=True)
            RP.run(arm, k)
    elif cmd == "summary":
        tag = rest[0] if rest else "k1"
        print(SU.table(tag))
        # The doc fix in isolation: RM3b vs v1 RM3 (same seed text, only the documents differ), and RM23 vs v1 RM2.
        print("\n### Δ vs v1 (paired per base seed; 90% bootstrap CI; P↓ = P(v2 lower))")
        print("| v2 vs v1 | n seeds | " + " | ".join(f"Δ{m}" for m in SU.SHOWN) + " |\n|---|---|" + "---|" * len(SU.SHOWN))
        for v2, v1 in (("RM3b", "RM3"), ("RM23", "RM2")):
            a = SU.load(HERE / "runs" / f"{v2}_{tag}.json")
            b = SU.load(TP / "real_material" / "runs" / f"{v1}_{tag}.json") or SU.load(TP / "real_material" / "runs" / f"{v1}_k1.json")
            if a and b:
                c = SU.proxy_eval.compare(b, a)
                n = max((x["n_seeds"] for x in c["metrics"].values()), default=0)
                print(f"| {v2} vs {v1} k={b['samples_per_seed']} | {n} | " + " | ".join(SU.cell(c, m) for m in SU.SHOWN) + " |")
    else:
        sys.exit(__doc__)
