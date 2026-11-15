"""Real-material arms v2 on the haiku proxy. Reuses ../real_material/{rm_proxy,make_seeds,summarize}.py unchanged,
pointed at this directory and at the v2 material (material_v2.install()).

    python3 experiments/taste_petri/real_material_v2/run_v2.py docs              # modernise docs (sonnet, cached)
    python3 experiments/taste_petri/real_material_v2/run_v2.py seeds             # RM3b, RM23 (no model calls)
    python3 experiments/taste_petri/real_material_v2/run_v2.py run RM3b --samples 2
    python3 experiments/taste_petri/real_material_v2/run_v2.py summary k2

Arms (both built on R0's text, like v1):
  RM3b  v1's RM3 with docs v2: scaffold where one fits, plus the present-day documents; India docs for 28, DRC for 70.
  RM23  RM3b plus v1's real trajectory prefixes (48, 63, 21, 73, 17): the RM2 material and the docs together.
One change to the proxy (recorded per sample in flags.docs_forced): v1's auditor skipped the <<DOC:id>> placeholder on
the non-scaffold seeds (66, 70), which made the arm equal to R0 there. If no placeholder was used, the documents are
put at the top of the first tool result.
"""
from __future__ import annotations

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


def modernise():
    llm = RP.Cache("sonnet")
    ids = sorted({d for f in V.FIT.values() for d in f["docs"]})

    def one(did):
        fiction = (V.NEW_NAMES.format(extra=V.NEW_FICTION[did]) if did in V.NEW_DOCS else V.KEEP_NAMES)
        raw = llm.complete(V.MODERNISE.format(today=V.TODAY, lo=V.WINDOW[0], hi=V.WINDOW[1], fiction=fiction,
                                              text=V.source_text(did)), max_tokens=4000)
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
    RP.log(f"modernise docs: cli_calls={llm.budget.calls} (sonnet)")
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
        modernise()
    elif cmd == "seeds":
        seeds()
    elif cmd == "run":
        k = int(rest[rest.index("--samples") + 1]) if "--samples" in rest else 1
        for arm in [a for a in rest if not a.startswith("--") and not a.isdigit()]:
            (HERE / "runs").mkdir(exist_ok=True)
            RP.run(arm, k)
    elif cmd == "summary":
        print(SU.table(rest[0] if rest else "k1"))
    else:
        sys.exit(__doc__)
