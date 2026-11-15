"""Disagreement-driven label queue: uncertainty ranking with diversity, DISAGREE facts, simulation."""
import contextlib
import io
import json
import math
import os
import random
import tempfile
import unittest
from unittest import mock

from autoresearch.integrations import living
from autoresearch.integrations.shared_memory import LocalSharedMemory
from autoresearch.taste import active_queries as aq
from autoresearch.taste import trackp
from autoresearch.taste.usermodel import Prediction


def record(run, it, context, options, chosen=0, umc=None, conf=None, point="D1"):
    return {"run_id": run, "iter": it, "point": point, "context": context, "options": options, "chosen": chosen,
            "user_model_choice": umc, "user_model_confidence": None if umc is None else conf, "evidence": {},
            "overrode_taste": umc is not None and umc != chosen, "arm": "R1", "code_version": "test"}


def write_decisions(path, recs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in recs)


class Setup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "researchers")
        os.makedirs(os.path.join(self.root, "pat"))
        self.path = os.path.join(self.tmp, "runs", "r1", "decisions.jsonl")
        self.recs = [
            record("r1", 1, "Which realism change to test on metric inflation", ["messy logs", "real names"], umc=0, conf=0.95),
            record("r1", 2, "Which realism change to test on metric inflation again", ["messy logs", "real names"], umc=0, conf=0.55),
            record("r1", 3, "Which realism change to test on metric inflation once more", ["messy logs", "real names"], umc=1, conf=0.52),
            record("r1", 4, "Accept the sycophancy result with a wide interval", ["accept", "defer"], umc=0, conf=0.6, point="D3"),
            record("r1", 5, "Claim strength for the fabrication finding", ["strong claim", "hedged claim"], point="D6"),
        ]
        write_decisions(self.path, self.recs)
        self.shared = LocalSharedMemory(os.path.join(self.tmp, "mem", "shared.jsonl"))


class UncertaintyTest(unittest.TestCase):
    def test_entropy_is_normalised(self):
        self.assertAlmostEqual(aq.entropy([0.5, 0.5]), 1.0)
        self.assertAlmostEqual(aq.entropy([0.25] * 4), 1.0)
        self.assertEqual(aq.entropy([1.0, 0.0]), 0.0)

    def test_committee_disagreement_is_zero_when_members_agree(self):
        total, js = aq.committee_uncertainty([[0.5, 0.5], [0.5, 0.5]])
        self.assertAlmostEqual(js, 0.0)
        total2, js2 = aq.committee_uncertainty([[0.99, 0.01], [0.01, 0.99]])
        self.assertGreater(js2, 0.8)
        self.assertAlmostEqual(total, total2, places=6)

    def test_logged_distribution_spreads_the_rest(self):
        rec = record("r", 1, "c", ["a", "b", "c"], umc=1, conf=0.6)
        self.assertEqual(aq.logged_distribution(rec), [0.2, 0.6, 0.2])
        self.assertEqual(aq.score_record(record("r", 1, "c", ["a", "b"]))["source"], "none")

    def test_models_are_used_when_given_and_disagreement_with_several(self):
        class M:
            def __init__(self, p):
                self.p = p

            def predict(self, context, options):
                return Prediction("a", max(self.p), probabilities=self.p)
        rec = record("r", 1, "c", ["a", "b"])
        self.assertEqual(aq.score_record(rec, [M([0.9, 0.1])])["source"], "model")
        s = aq.score_record(rec, [M([0.9, 0.1]), M([0.1, 0.9])])
        self.assertEqual(s["source"], "committee")
        self.assertGreater(s["disagreement"], 0.3)

    def test_platt_is_identity_without_enough_labels_and_learns_overconfidence(self):
        self.assertEqual(aq.Platt([(0.9, True)])(0.9), 0.9)
        # A model that says 0.9 but is right half the time.
        cal = aq.Platt([(0.9, i % 2 == 0) for i in range(20)])
        self.assertTrue(cal.fitted)
        self.assertLess(abs(cal(0.9) - 0.5), 0.1)

    def test_mmr_spreads_near_duplicates(self):
        vecs = [{"x": 1.0}, {"x": 1.0}, {"y": 1.0}]
        self.assertEqual([i for i, _ in aq.mmr_order([1.0, 0.99, 0.5], vecs, diversity=0.0)], [0, 1, 2])
        self.assertEqual([i for i, _ in aq.mmr_order([1.0, 0.99, 0.5], vecs, diversity=0.6)], [0, 2, 1])


class QueueTest(Setup):
    def test_queue_ids_are_trackp_label_ids_ranked_by_uncertainty(self):
        rows = aq.build_queue(self.root, "pat", [self.path], diversity=0.0)
        ids = {it["id"] for it in trackp.pending_items(self.root, "pat", ("label",), [self.path])}
        self.assertEqual({r["id"] for r in rows}, ids)
        # No user model (1.0) first, then 0.52 / 0.55, then 0.6, then 0.95.
        self.assertEqual([r["iter"] for r in rows], [5, 3, 2, 4, 1])
        self.assertEqual(rows[0]["uncertainty_source"], "none")
        self.assertTrue(all(r["decisions"] == self.path for r in rows))

    def test_diversity_moves_a_near_duplicate_down(self):
        plain = [r["iter"] for r in aq.build_queue(self.root, "pat", [self.path], diversity=0.0)]
        spread = [r["iter"] for r in aq.build_queue(self.root, "pat", [self.path], diversity=0.7)]
        # Iterations 2 and 3 are the same question reworded: with diversity they are no longer adjacent.
        self.assertEqual(abs(plain.index(2) - plain.index(3)), 1)
        self.assertGreater(abs(spread.index(2) - spread.index(3)), 1)

    def test_labelled_decisions_leave_the_queue(self):
        item = trackp.pending_items(self.root, "pat", ("label",), [self.path])[0]
        trackp.record(self.root, "pat", item, 1)
        rows = aq.build_queue(self.root, "pat", [self.path])
        self.assertNotIn(item["id"], {r["id"] for r in rows})

    def test_read_queue_rejects_other_files(self):
        bad = os.path.join(self.tmp, "bad.jsonl")
        with open(bad, "w") as f:
            f.write(json.dumps({"id": "seed:x", "rank": 1}) + "\n")
        with self.assertRaises(ValueError):
            aq.read_queue(bad)


class LabelTest(Setup):
    def queue(self):
        path = os.path.join(self.tmp, "queue.jsonl")
        with open(path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in aq.build_queue(self.root, "pat", [self.path], diversity=0.0))
        return path

    def answer(self, picks):
        """ask() that answers each item with the option whose text is in `picks` (by iteration)."""
        shown = []

        def say(text):
            shown.append(text)

        def ask(_):
            options = [s.split(") ", 1)[1] for s in shown if s.startswith("  ") and ") " in s][-2:]
            return str(options.index(picks.pop(0)) + 1)
        return ask, say

    def test_label_in_queue_order_writes_label_and_disagree_facts(self):
        # Queue order is iterations 5, 3, 2, 4, 1. At 3 the model picked "real names"; she picks "messy logs".
        ask, say = self.answer(["hedged claim", "messy logs", "messy logs"])
        rep = aq.label_from_queue(self.root, "pat", self.queue(), self.shared, ask=ask, say=say, limit=3)
        self.assertEqual(rep["answered"], 3)
        labels = trackp._read(os.path.join(self.root, "pat", trackp.LABELS))
        self.assertEqual([r["iter"] for r in labels], [5, 3, 2])
        dis = [f for f in self.shared.facts("t", "DISAGREE", "DISAGREE") if f.get("by") == "researcher"]
        self.assertEqual(len(dis), 1)
        self.assertEqual(dis[0]["taste"], "real names")
        self.assertEqual(dis[0]["label"], "messy logs")
        self.assertEqual(dis[0]["key"], aq.fact_key(self.recs[2]))
        self.assertEqual(len(living.labels(self.shared, "pat")), 3)
        # Answered, so the living model's own queue does not ask again.
        self.assertNotIn(dis[0]["key"], {f["key"] for f in living.pending(self.shared, "pat")})
        # The LABEL fact becomes a Choice that picks her option.
        c = next(c for c in living.choices_from_memory(self.shared, "pat") if c.example_id == dis[0]["key"])
        self.assertEqual(c.a_text if c.chosen == "a" else c.b_text, "messy logs")

    def test_sync_is_idempotent_and_covers_trackp_labels(self):
        items = {it["_src"]["iter"]: it for it in trackp.pending_items(self.root, "pat", ("label",), [self.path])}
        it = items[1]   # model picked "messy logs"; answer with "real names"
        trackp.record(self.root, "pat", it, it["options"].index("real names") + 1)
        first = aq.sync_disagreements(self.shared, self.root, "pat", [self.path])
        second = aq.sync_disagreements(self.shared, self.root, "pat", [self.path])
        self.assertEqual((first["disagreements"], first["written"]), (1, 1))
        self.assertEqual(second["written"], 0)

    def test_taste_cli_label_command(self):
        queue = self.queue()
        from autoresearch.taste.__main__ import main
        out = io.StringIO()
        env = {k: v for k, v in os.environ.items() if k != "PAST_API_KEY"}   # the local store, never past.dev
        with mock.patch.dict(os.environ, env, clear=True), mock.patch("builtins.input", side_effect=["q"]), \
                contextlib.redirect_stdout(out):
            main(["label", "--researcher", "pat", "--queue", queue, "--root", self.root,
                  "--memory", os.path.join(self.tmp, "mem")])
        self.assertEqual(json.loads(out.getvalue().strip().splitlines()[-1])["answered"], 0)


def synthetic_pool(n=120, seed=0):
    """Feature-dict choices from hidden weights, with noise: the demo researchers' format."""
    rng = random.Random(seed)
    w = {"realism": 2.0, "grounding": 1.0, "simplicity": -1.0, "novelty": 0.5}
    rows = []
    for _ in range(n):
        a = {k: rng.random() for k in w}
        b = {k: rng.random() for k in w}
        z = sum(w[k] * (a[k] - b[k]) for k in w)
        rows.append({"a": a, "b": b, "chosen": "a" if rng.random() < 1 / (1 + math.exp(-3 * z)) else "b"})
    return rows


class SimulationTest(unittest.TestCase):
    def pool(self, rows):
        path = os.path.join(tempfile.mkdtemp(), "choices.jsonl")
        with open(path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        return aq.load_pool(path)

    def test_learner_learns_hidden_weights(self):
        pool = self.pool(synthetic_pool(200))
        model = aq.BradleyTerry().fit(pool[:150])
        self.assertGreater(aq.accuracy(model, pool[150:]), 0.7)
        self.assertEqual(aq.accuracy(aq.BradleyTerry().fit([]), pool), 0.5)

    def test_simulation_curves_are_comparable_and_deterministic(self):
        pool = self.pool(synthetic_pool(80))
        kw = dict(init=4, batch=8, max_labels=28, committee=3)
        a = aq.simulate(pool, seeds=(0, 1), **kw)
        b = aq.simulate(pool, seeds=(0, 1), **kw)
        self.assertEqual(a["alc_gain"], b["alc_gain"])
        ns = {s: [n for n, _, _ in a["summary"][s]["curve"]] for s in ("random", "uncertainty")}
        self.assertEqual(ns["random"], ns["uncertainty"])
        self.assertEqual(ns["random"], [4, 12, 20, 28])
        for run in a["per_seed"]:   # both strategies start from the same labels
            self.assertEqual(run["curves"]["random"]["points"][0], run["curves"]["uncertainty"]["points"][0])
        md = aq.markdown(dict(a, source="x"), "synthetic")
        self.assertIn("| labels | random | uncertainty |", md)

    def test_text_choice_rows_and_groups(self):
        rows = [{"context": "c", "a_text": f"probe study {i}", "b_text": f"survey study {i}", "chosen": "a",
                 "group_id": f"g{i // 2}"} for i in range(20)]
        pool = self.pool(rows)
        train, test = aq._split(pool, 0.3, random.Random(0))
        self.assertFalse({r["group"] for r in train} & {r["group"] for r in test})
        rep = aq.simulate_seed(pool, 0, init=2, batch=2, max_labels=6, committee=2)
        self.assertEqual(rep["curves"]["uncertainty"]["points"][-1][0], 6)

    def test_simulate_cli_writes_json_and_markdown(self):
        src = os.path.join(tempfile.mkdtemp(), "choices.jsonl")
        with open(src, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in synthetic_pool(60))
        out = os.path.join(tempfile.mkdtemp(), "sim")
        with contextlib.redirect_stdout(io.StringIO()):
            aq.main(["simulate", "--choices", src, "--out", out, "--seeds", "0", "1", "--max-labels", "20",
                     "--batch", "8", "--committee", "2"])
        with open(out + ".json") as f:
            self.assertEqual(json.load(f)["source"], src)
        self.assertTrue(os.path.exists(out + ".md"))


if __name__ == "__main__":
    unittest.main()
