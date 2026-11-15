"""WS B personal track: seed pairs, decision labels, noise ceiling, hold-out split, E2.

Most tests drive the CLI the way an agent does: `pending` to see items, `record` to save
the person's reply."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from autoresearch.cli import resolve_arm
from autoresearch.llm import OfflineLLM
from autoresearch.research.advisor import load_user_model
from autoresearch.research.decisions import DecisionLog
from autoresearch.research.ideas import LIBRARY
from autoresearch.research.measure import SCENARIOS
from autoresearch.taste import trackp
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import Prediction, UserModel

SLUG = "teammate"
LIBRARY_TEXTS = [i.text for i in LIBRARY]


def library_rank(text):
    """A consistent person: always prefers the option listed later in the library."""
    return LIBRARY_TEXTS.index(text)


def read(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


class TrackPTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        trackp.init(self.root, SLUG, "A Teammate")
        self.dir = os.path.join(self.root, SLUG)

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            trackp.main(["--root", self.root, *map(str, args)])
        text = out.getvalue()
        return json.loads(text) if text.lstrip().startswith("{") else text

    def answer(self, kind, prefer, *extra, reason="because"):
        """The agent loop: show each pending item, record the person's pick."""
        items = self.cli("pending", "--kind", kind, "--limit", 1000, *extra)["items"]
        for it in items:
            best = max(range(len(it["options"])), key=lambda j: prefer(it["options"][j]))
            self.cli("record", "--id", it["id"], "--choice", best + 1, "--reason", reason, *extra)
        return items

    def seed(self, n=20, prefer=library_rank):
        self.cli("seed-pairs", "--n", n, "--seed", 1, "--scenarios", "metric_inflation", "fabrication")
        return self.answer("seed", prefer)

    def label_run(self, run_id, records):
        log = DecisionLog(run_id, "R0", root=os.path.join(self.root, "runs"), version="test")
        for point, options, chosen in records:
            log.add(iter=0, point=point, context=f"{point} context", options=options, chosen=chosen,
                    evidence={"delta": 0.1})
        return log.path

    def test_init_sets_track_p_and_keeps_other_tracks(self):
        with open(os.path.join(self.root, "tracks.json"), "w") as f:
            json.dump({"S": "marius"}, f)
        trackp.init(self.root, SLUG, "A Teammate")
        self.assertEqual(resolve_arm("model", track="P", root=self.root), (SLUG, "R1-P"))
        self.assertEqual(resolve_arm("model", track="S", root=self.root)[0], "marius")

    def test_status_defaults_to_the_track_p_person_and_says_what_to_run_next(self):
        fresh = self.cli("status", "--decisions")
        self.assertEqual(fresh["researcher"], SLUG)
        self.assertTrue(any("CONSENT.md" in s for s in fresh["next"]))
        self.assertTrue(any(s.startswith("seed-pairs") for s in fresh["next"]))
        self.cli("seed-pairs", "--n", 4)
        self.assertTrue(any(s.startswith("4 seed item(s) waiting") for s in self.cli("status", "--decisions")["next"]))

    def test_seed_pairs_are_distinct_same_item_and_balanced(self):
        items = [SCENARIOS["metric_inflation"], SCENARIOS["fabrication"]]
        pairs = trackp.make_seed_pairs(items, 30, seed=0)
        self.assertEqual(len({p["pair_id"] for p in pairs}), 30)
        self.assertEqual(sum(p["item"] == "fabrication" for p in pairs), 15)
        for p in pairs:
            self.assertIn(p["a_text"], LIBRARY_TEXTS)
            self.assertIn(p["b_text"], LIBRARY_TEXTS)
            self.assertNotEqual(p["a_text"], p["b_text"])
            self.assertIn(SCENARIOS[p["item"]].goal, p["context"])

    def test_recorded_answers_are_choices_with_reasons_and_leave_nothing_pending(self):
        shown = self.seed(n=6)
        rows = read(os.path.join(self.dir, trackp.SEED_CHOICES))
        self.assertEqual(len(rows), 6)
        for r in rows:
            winner = r["a_text"] if r["chosen"] == "a" else r["b_text"]
            self.assertEqual(winner, max(r["a_text"], r["b_text"], key=library_rank))
            self.assertEqual((r["reason"], r["decision_point"], r["source"]), ("because", "D1", "seed"))
        self.assertEqual(self.cli("pending", "--kind", "seed")["n_pending"], 0)
        with self.assertRaises(SystemExit):
            self.cli("record", "--id", shown[0]["id"], "--choice", 1)

    def test_label_maps_the_shown_number_back_and_never_shows_the_loop_choice(self):
        path = self.label_run("run1", [("D3", ["accept", "reject", "defer"], 0),
                                       ("D5", ["noise", "real effect"], 1),
                                       ("D1", ["only option"], 0)])
        items = self.answer("label", lambda t: t in ("defer", "noise"), "--decisions", path)
        self.assertEqual(len(items), 2)
        for it in items:
            self.assertEqual(set(it), {"id", "kind", "context", "evidence", "options"})
            self.assertNotIn("R0", json.dumps(it))
        labels = read(os.path.join(self.dir, trackp.LABELS))
        self.assertEqual([(l["point"], l["options"][l["label"]]) for l in labels], [("D3", "defer"), ("D5", "noise")])

    def test_label_evidence_shows_measurements_but_not_the_loop_ranking_or_verdicts(self):
        log = DecisionLog("run2", "R1-P", root=os.path.join(self.root, "runs"), version="test")
        log.add(iter=0, point="D1", context="which next", options=["x", "y"], chosen=0,
                evidence={"priority": [{"design": "x", "taste": 0.9, "total": 1.2}], "measured": ["x"]})
        log.add(iter=0, point="D3", context="accept?", options=["accept", "reject"], chosen=0,
                evidence={"p_better": 0.95, "delta": 0.2, "ci90": [0.1, 0.3], "n": 6, "decisive": True})
        items = self.cli("pending", "--kind", "label", "--decisions", log.path)["items"]
        self.assertEqual([it["evidence"] for it in items],
                         [{}, {"p_better": 0.95, "delta": 0.2, "ci90": [0.1, 0.3], "n": 6}])

    def test_a_label_becomes_one_pairwise_choice_per_rejected_option(self):
        path = self.label_run("run1", [("D3", ["accept", "reject", "defer"], 0)])
        self.answer("label", lambda t: t == "reject", "--decisions", path)
        choices = trackp.labels_to_choices(SLUG, read(os.path.join(self.dir, trackp.LABELS)))
        self.assertEqual(len(choices), 2)
        for c in choices:
            self.assertEqual(c.a_text if c.chosen == "a" else c.b_text, "reject")
            self.assertEqual(c.decision_point, "D3")

    def test_recheck_waits_then_a_consistent_person_agrees_with_themselves(self):
        answered = self.seed(n=20)
        self.assertEqual(self.cli("pending", "--kind", "recheck", "--frac", 1)["n_pending"], 0)
        rechecked = self.answer("recheck", library_rank, "--frac", 1, "--min-days", 0)
        self.assertEqual(len(rechecked), len(answered))
        first_shown = {"recheck:" + it["id"]: it["options"] for it in answered}
        for it in rechecked:
            self.assertEqual(it["options"], first_shown[it["id"]][::-1])
        self.assertEqual(trackp.noise_ceiling(self.root, SLUG)["seed"]["agreement"], 1.0)

    def test_noise_ceiling_counts_changed_answers(self):
        self.seed(n=4)
        self.answer("recheck", lambda t: -library_rank(t), "--frac", 1, "--min-days", 0)
        self.assertEqual(trackp.noise_ceiling(self.root, SLUG)["seed"], {"n": 4, "agreement": 0.0, "ci90": [0.0, 0.0]})

    def test_terminal_loop_records_the_same_answer_as_record(self):
        self.cli("seed-pairs", "--n", 3)
        replies = iter(["2", "why not", "skip", "q"])
        n = trackp.ask_items(self.root, SLUG, trackp.pending_items(self.root, SLUG, ("seed",)),
                             ask=lambda _: next(replies), say=lambda _: None)
        self.assertEqual(n, 1)
        (row,) = read(os.path.join(self.dir, trackp.SEED_CHOICES))
        self.assertEqual((row["chosen"], row["reason"]), ("b", "why not"))

    def test_split_holds_out_stable_seed_pairs_and_late_runs(self):
        self.seed(n=20)
        first_test = {c.example_id for c in trackp.split(self.root, SLUG)["test"]}
        self.seed(n=40)
        parts = trackp.split(self.root, SLUG)
        self.assertTrue(first_test <= {c.example_id for c in parts["test"]})
        self.assertTrue(4 <= len(parts["test"]) <= 14)
        path = self.label_run("late", [("D3", ["accept", "reject", "defer"], 0)])
        self.answer("label", lambda t: t == "defer", "--decisions", path)
        run_date = read(os.path.join(self.dir, trackp.LABELS))[0]["run_date"]
        held = trackp.split(self.root, SLUG, label_cutoff=run_date)
        self.assertEqual(sum(c.source == "label" for c in held["test"]), 2)
        self.assertEqual(sum(c.source == "label" for c in held["history"] + held["val"]), 0)

    def test_fit_writes_a_user_model_the_loop_loads_and_history_without_held_out_choices(self):
        self.seed(n=30)
        trackp.fit_user_model(self.root, SLUG, lambda: create_method("m1", OfflineLLM()))
        model, source = load_user_model(self.dir, None, OfflineLLM())
        self.assertEqual(model.method_id, "m1")
        self.assertIn("usermodel.json", source)
        held = {c.example_id for c in trackp.split(self.root, SLUG)["test"]}
        exported = {r["example_id"] for r in read(os.path.join(self.dir, trackp.HISTORY))}
        self.assertEqual(len(exported), 30 - len(held))
        self.assertFalse(exported & held)

    def test_e2_scores_held_out_choices_and_never_overwrites(self):
        self.seed(n=30)
        held = trackp.split(self.root, SLUG)["test"]

        class PrefersLater(UserModel):   # the real fit() checks for history/val leakage
            def predict(self, context, options):
                a_wins = library_rank(options[0]) > library_rank(options[1])
                return Prediction(choice="a" if a_wins else "b", confidence=0.9,
                                  probabilities=[0.9, 0.1] if a_wins else [0.1, 0.9])
        out = os.path.join(self.root, "e2.json")
        rep = trackp.run_e2(self.root, SLUG, {"later": lambda: PrefersLater(OfflineLLM())}, out)
        self.assertEqual(rep["methods"]["later"]["accuracy"], 1.0)
        self.assertEqual(rep["methods"]["later"]["n"], len(held))
        with self.assertRaises(FileExistsError):
            trackp.run_e2(self.root, SLUG, {"later": lambda: PrefersLater(OfflineLLM())}, out)


if __name__ == "__main__":
    unittest.main()
