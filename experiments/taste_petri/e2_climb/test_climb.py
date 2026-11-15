"""Offline checks of climb.py with a fake `claude -p` (no real calls).

    python3 -m unittest experiments/taste_petri/e2_climb/test_climb.py   (from the repo root)
"""
import importlib.util
import json
import os
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("e2_climb", os.path.join(HERE, "climb.py"))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)

MARK = "zeta"  # the fake predictor favours options with this word, more so the more often the profile says it


def fake_reply(prompt, drop_keys=(), limit=False):
    if limit:
        return {"is_error": True, "result": "You've hit your 5-hour limit · resets 2:20pm"}
    if prompt.startswith("Below is one line"):
        return {"result": json.dumps({"line": prompt.split("LINE:\n", 1)[1] + " " + MARK})}
    if prompt.startswith("Below is a card"):
        return {"result": json.dumps({"card": prompt.split("CARD:\n", 1)[1]})}
    payload = json.loads(prompt.split("INPUT_JSON:\n", 1)[1])
    k = payload.get("persona", "").count(MARK)

    def probs(opts):
        w = [1 + k if MARK in o else 1 for o in opts]
        return [x / sum(w) for x in w]

    if "items" in payload and "problem" in payload["items"][0]:
        return {"result": json.dumps({"items": [{"key": it["key"], "claim": f"When {it['problem']}, he acts."}
                                                for it in payload["items"]]})}
    if "items" in payload:
        return {"result": "Here you go:\n```json\n" + json.dumps(
            {"items": [{"key": it["key"], "probabilities": probs(it["options"])}
                       for it in payload["items"] if it["key"] not in drop_keys]}) + "\n```"}
    return {"result": json.dumps({"probabilities": probs(payload["options"]), "rationale": "x"})}


class FakeCLI:
    def __init__(self, **kw):
        self.prompts, self.models, self.kw = [], [], kw

    def __call__(self, cmd, input, **_):
        self.prompts.append(input)
        self.models.append(cmd[cmd.index("--model") + 1])
        data = dict({"is_error": False, "usage": {}, "total_cost_usd": 0.0}, **fake_reply(input, **self.kw))
        return types.SimpleNamespace(returncode=1 if data["is_error"] else 0, stdout=json.dumps(data), stderr="")


def pairs(n, prefix="p"):
    out = []
    for i in range(n):
        his = "a" if i % 2 else "b"
        a, b = (f"{MARK} option {i}", f"plain option {i}") if his == "a" else (f"plain option {i}", f"{MARK} option {i}")
        out.append({"pair_id": f"{prefix}{i}", "work": f"w{i % 3}", "context": f"CTX-{prefix}{i}",
                    "question": "Q?", "a_text": a, "b_text": b, "his_side": his})
    return out


class ClimbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for mod in (C, C.V2):
            patcher = mock.patch.object(mod, "HERE", self.tmp.name)
            patcher.start()
            self.addCleanup(patcher.stop)
        C.STOP.clear()

    def fake(self, **kw):
        cli = FakeCLI(**kw)
        patcher = mock.patch.object(C.V2.subprocess, "run", cli)
        patcher.start()
        self.addCleanup(patcher.stop)
        return cli

    def test_parse_batch_keeps_valid_items_and_normalises(self):
        batch = [{"pair_id": "x", "order": 0}, {"pair_id": "y", "order": 0}, {"pair_id": "z", "order": 1},
                 {"pair_id": "w", "order": 1}]
        reply = {"items": [{"key": "i1", "probabilities": [0.6, 0.6]}, {"key": "i2", "probabilities": ["0.5", "0.5"]},
                           {"key": "i3", "probabilities": [True, 0]}, "junk"]}
        self.assertEqual(C.parse_batch(reply, batch), {("x", 0): [0.5, 0.5]})
        self.assertEqual(C.parse_batch(None, batch), {})

    def test_batched_scores_both_orders_and_falls_back_on_dropped_items(self):
        cli = self.fake(drop_keys=("i3",))
        ps = pairs(60)
        probs, misses = C.batched_probs(f"{MARK}", ps, "batch:t")
        self.assertEqual(len(probs), 120)
        self.assertEqual(misses, 4)  # 120 items -> batches of 50, 10, 50, 10; i3 dropped from each
        ph, acc = C.summarise(probs, ps)
        self.assertAlmostEqual(ph, 2 / 3)
        self.assertEqual(acc, 1.0)
        self.assertEqual(set(cli.models), {"haiku"})  # PREREG budget amendment: climb-set scoring on haiku
        batched = [json.loads(x.split("INPUT_JSON:\n")[1]) for x in cli.prompts if '"items"' in x]
        for b in batched:  # no labels in the prompt, and one order per call
            self.assertTrue(all(set(it) == {"key", "context", "options"} for it in b["items"]))
            self.assertEqual(len({it["context"] for it in b["items"]}), len(b["items"]))

    def test_m0s_scores_half_and_cached_calls_are_not_repeated(self):
        cli = self.fake()
        ps = pairs(10)
        C.batched_probs("", ps, "batch:m0")
        n = len(cli.prompts)
        probs, _ = C.batched_probs("", ps, "batch:m0")
        self.assertEqual(len(cli.prompts), n)
        self.assertEqual(C.summarise(probs, ps), (0.5, 0.0))  # ties pick the first option, as in e2

    def test_usage_limit_stops_without_caching_or_more_calls(self):
        cli = self.fake(limit=True)
        with self.assertRaises(C.UsageLimit):
            C.batched_probs(MARK, pairs(120), "batch:lim")
        self.assertLessEqual(len(cli.prompts), C.WORKERS)
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "cache", "raw")) and
                         os.listdir(os.path.join(self.tmp.name, "cache", "raw")))

    def test_climb_accepts_gains_keeps_best_early_stop_and_operators_never_see_pairs(self):
        cli = self.fake()
        climb, early = pairs(20, "c"), pairs(10, "e")
        pool = [{"id": f"C{i}", "source": "t", "text": f"claim {i} {MARK if i % 2 else ''}".strip()} for i in range(30)]
        res = C.run_climb("T", climb, early, C.make_scorer("T"), pool, "line one\n\nline two", max_steps=12)
        tr = res["trace"]
        self.assertEqual(len(tr), 13)
        for row in tr[1:]:
            if row.get("accepted"):
                prev = [r for r in tr[:row["step"]] if r.get("accepted")][-1]
                self.assertGreater(row["climb_obj"] - prev["climb_obj"], C.MIN_GAIN)
                self.assertIsNotNone(row["early_obj"])
        self.assertTrue(any(r.get("accepted") for r in tr[1:]))
        best = max((r for r in tr if r.get("accepted")), key=lambda r: (r["early_obj"], -r["step"]))
        self.assertEqual(res["kept_step"], best["step"])
        ops = [x for x in cli.prompts if x.startswith("Below is")]
        self.assertTrue(ops)
        self.assertEqual({m for m, x in zip(cli.models, cli.prompts) if x.startswith("Below is")}, {"sonnet"})
        for x in ops:
            self.assertNotIn("CTX-", x)
            self.assertNotIn("option", x)

    def test_pool_reads_every_source_and_generalises_informal_decisions(self):
        self.fake()
        pool = C.build_pool()
        srcs = {c["source"] for c in pool}
        self.assertEqual(srcs, {"P4", "P1", "P0", "P2", "S_paper", "informal"})
        self.assertEqual(sum(c["source"] == "P4" for c in pool), 7)
        self.assertEqual(sum(c["source"] == "informal" for c in pool), len(C.informal_decisions()))
        self.assertTrue(all("**" not in c["text"] for c in pool))

    def test_confirm_uses_e2_unbatched_format_and_report_compares_to_cached_arms(self):
        cli = self.fake()
        with open(os.path.join(self.tmp.name, "H_A.md"), "w") as f:
            f.write("some card\n")
        C.confirm_cmd("A")
        singles = [json.loads(x.split("INPUT_JSON:\n")[1]) for x in cli.prompts]
        self.assertEqual(len(singles), 192)
        self.assertEqual(set(cli.models), {"sonnet"})
        self.assertTrue(all(s["persona"] == "some card" and len(s["options"]) == 2 for s in singles))
        with self.assertRaises(SystemExit):  # one confirmation run per climb
            C.confirm_cmd("A")
        C.report_cmd()
        with open(os.path.join(self.tmp.name, "results.json")) as f:
            res = json.load(f)
        self.assertEqual(res["n_pairs"], 96)
        self.assertEqual(set(res["acc_diff"]["H_A"]), {"M0s", "NAME", "P4", "P0", "MIS", "ANTI"})
        self.assertEqual(res["accuracy"]["P4"]["value"], 0.292)  # e2_v4's cached number
        self.assertEqual(res["calls"]["H_A"], 192)

    def test_category_cap_refuses_the_next_real_call(self):
        self.fake()
        with mock.patch.dict(C.CAPS, {"op": 1}):
            C.ask("op:t", "Below is one line x\nLINE:\nfirst", "sonnet")
            with self.assertRaisesRegex(RuntimeError, "call cap"):
                C.ask("op:t", "Below is one line x\nLINE:\nsecond", "sonnet")
            C.ask("op:t", "Below is one line x\nLINE:\nfirst", "sonnet")  # cached: no new call


if __name__ == "__main__":
    unittest.main()
