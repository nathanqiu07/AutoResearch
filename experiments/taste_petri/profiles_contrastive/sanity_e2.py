"""Optional sanity check: the contrastive arms on the OLD e2_owain held-out pairs where the blind judge
was not 4/4 for his option (7 pairs, 5 works), with e2_owain's M0 and E_pre predictions on the same
pairs for comparison. Same predictor as e2_owain's E_pre arm (UserModel persona slot, haiku, JsonReply).
n is tiny; this checks the arms work end to end in a predictor, it cannot rank them."""
import json
import os

import common
from common import p, read_jsonl
from autoresearch.llm import LLM
from autoresearch.taste import track_eval
from autoresearch.taste.usermodel import Choice, UserModel

import arms

E2 = p("..", "e2_owain")
ARMS = ("P0", "P1", "P2", "P4", "P1+P3")


class Haiku(LLM):
    name, model = "claude-cli", "haiku"

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        return common.call("haiku", prompt, system or "You are a helpful assistant.", tag="sanity_e2")


class Persona(UserModel):
    method_id = "persona"

    def __init__(self, llm_, persona, **kw):
        super().__init__(llm_, **kw)
        self.persona = persona

    def predict(self, context, options):
        return self._predict_with(context, options, persona=self.persona)


def main():
    votes = {r["pair_id"]: [v for o in r["votes"] for v in o] for r in read_jsonl(os.path.join(E2, "gate_votes.jsonl"))}
    hard = {k for k, v in votes.items() if sum(map(bool, v)) < len(v)}
    pairs = [r for r in read_jsonl(os.path.join(E2, "pairs.jsonl")) if r["pair_id"] in hard]
    old = {(r["arm"], r["pair_id"]): r for r in read_jsonl(os.path.join(E2, "predictions.jsonl"))}
    rows = []
    for r in pairs:
        c = Choice(user_id="anon", context=r["context"], a_text=r["a_text"], b_text=r["b_text"], chosen=r["chosen"],
                   decision_point=r["decision_point"], reason="", timestamp=r["date"], source="timesplit",
                   example_id=r["pair_id"], group_id=r["work"])
        row = {"pair_id": r["pair_id"], "work": r["work"]}
        for arm in ("M0", "E_pre"):
            o = old[(arm, r["pair_id"])]
            row[arm] = {"correct": o["correct"], "p_his": round(sum(o["p_his"]) / 2, 3)}
        for arm in ARMS:
            m = Persona(track_eval.JsonReply(Haiku()), arms.get_profile_text(arm, r["context"]),
                        cache_dir=p("cache", "usermodel"))
            ok = track_eval.paired_correct(m, c)
            p1 = m.predict(c.context, [c.a_text, c.b_text]).probabilities
            p2 = m.predict(c.context, [c.b_text, c.a_text]).probabilities
            his = (p1[0 if c.chosen == "a" else 1] + p2[1 if c.chosen == "a" else 0]) / 2
            row[arm] = {"correct": ok, "p_his": round(his, 3)}
        rows.append(row)
        print(json.dumps(row))
    summary = {arm: {"acc": sum(bool(r[arm]["correct"]) for r in rows) / len(rows),
                     "mean_p_his": round(sum(r[arm]["p_his"] for r in rows) / len(rows), 3)}
               for arm in ("M0", "E_pre", *ARMS)}
    json.dump({"n_pairs": len(rows), "n_works": len({r["work"] for r in rows}), "summary": summary, "rows": rows},
              open(p("sanity_e2.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
