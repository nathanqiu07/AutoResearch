"""Deadline shortcut (user, 13:13: results by 13:30): SynthesizeMe-lite. Same history, same per-choice hypothesis
prompt as m2 (cached from the interrupted fits), but NO validation forward-selection: one persona call over all
unique hypotheses, then the persona is scored on the test pairs like any other arm.

    python3 lite.py paper|informal     # writes S_<x>_lite.json, then: python3 run.py arms S_paper_lite ...
"""
import json
import os
import sys

import common as C

F = C.synthme_fit()
m2 = F.m2
src = sys.argv[1]
arm = {"paper": "S_paper", "informal": "S_inf"}[src]
history, _ = F.history_and_val(src)
model = F.BatchedSynthesizeMe(F.llm("fit:" + arm), seed=0, cache_dir=os.path.join(C.HERE, "cache", "um_" + arm),
                              max_calls=2400, **F.CONFIG)
rows = m2.selected_history(model, history)
hyps = []
for row in rows:
    r = model._json('Explain why this user chose this reply. Return {"hypothesis": "one concise '
                    'preference hypothesis, at most 600 characters"}.', {"choice": m2.example(row)})
    try:
        h = C.text_field(r, "hypothesis", 600)
    except ValueError:
        continue
    if h not in hyps:
        hyps.append(h)
r = model._json('Write a short persona using only these hypotheses. Return {"persona": "persona text"}. '
                'Use at most 1600 characters.', {"hypotheses": hyps})
persona = C.text_field(r, "persona", 1600)
out = {"arm": arm + "_lite", "persona": persona, "n_history": len(rows), "n_hypotheses": len(hyps), "hypotheses": hyps,
       "shortcut": "no validation forward-selection (deadline)"}
json.dump(out, open(os.path.join(C.HERE, arm + "_lite.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("n_history", "n_hypotheses", "persona")}, indent=1, ensure_ascii=False))
