"""WS B Track P: seed pairs, decision labels, noise ceiling, hold-out split, E2."""
import datetime
import json
import os
import tempfile
import unittest

from autoresearch.cli import resolve_arm
from autoresearch.llm import OfflineLLM
from autoresearch.research.decisions import DecisionLog
from autoresearch.research.ideas import LIBRARY
from autoresearch.research.measure import SCENARIOS
from autoresearch.taste import trackp
from autoresearch.taste.usermodel import Prediction, UserModel

SLUG = "teammate"


class Script:
    """Stands in for the person: picks the shown option with the highest
    prefer(text), or always answers `fixed`; records everything shown."""

    def __init__(self, prefer=None, reason="because", fixed=None):
        self.prefer, self.reason, self.fixed, self.shown, self.lines = prefer, reason, fixed, [], []

    def say(self, text):
        self.shown.append(text)
        self.lines += [l.strip() for l in text.splitlines() if l.strip()[:2] in {f"{c})" for c in "ab123456789"}]

    def ask(self, prompt):
        if prompt.startswith("why"):
            return self.reason
        lines, self.lines = self.lines, []
        return self.fixed or max(lines, key=lambda l: self.prefer(l[3:]))[0]


def library_rank(text):
    """A consistent person: always prefers the option listed later in the library."""
    return [i.text for i in LIBRARY].index(text)


def read(path):
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


class TrackPTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        trackp.init(self.root, SLUG, "A Teammate")
        self.dir = os.path.join(self.root, SLUG)

    def seed(self, n=20, prefer=library_rank, fixed=None):
        items = [SCENARIOS["metric_inflation"], SCENARIOS["fabrication"]]
        trackp.write_seed_pairs(self.root, SLUG, trackp.make_seed_pairs(items, n, seed=1))
        person = Script(prefer, fixed=fixed)
        trackp.answer_seed_pairs(self.root, SLUG, person.ask, person.say)
        return person

    def label_run(self, run_id, records):
        runs = os.path.join(self.root, "runs")
        log = DecisionLog(run_id, "R0", root=runs, version="test")
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
        self.assertTrue(os.path.exists(os.path.join(self.dir, "CONSENT.md")))

    def test_seed_pairs_are_distinct_same_item_and_balanced(self):
        items = [SCENARIOS["metric_inflation"], SCENARIOS["fabrication"]]
        pairs = trackp.make_seed_pairs(items, 30, seed=0)
        library = {i.text for i in LIBRARY}
        self.assertEqual(len({p["pair_id"] for p in pairs}), 30)
        self.assertEqual(sum(p["item"] == "fabrication" for p in pairs), 15)
        for p in pairs:
            self.assertIn(p["a_text"], library)
            self.assertIn(p["b_text"], library)
            self.assertNotEqual(p["a_text"], p["b_text"])
            self.assertIn(SCENARIOS[p["item"]].goal, p["context"])

    def test_answers_are_stored_as_choices_with_reasons_and_resume(self):
        self.seed(n=6, fixed="a")
        rows = read(os.path.join(self.dir, trackp.SEED_CHOICES))
        self.assertEqual(len(rows), 6)
        self.assertEqual({(r["chosen"], r["reason"], r["decision_point"], r["source"]) for r in rows},
                         {("a", "because", "D1", "seed")})
        again = Script(fixed="a")
        self.assertEqual(trackp.answer_seed_pairs(self.root, SLUG, again.ask, again.say), 0)

    def test_label_maps_shuffled_display_back_to_the_option_and_hides_the_loop_choice(self):
        path = self.label_run("run1", [("D3", ["accept", "reject", "defer"], 0),
                                       ("D5", ["noise", "real effect"], 1),
                                       ("D1", ["only option"], 0)])
        person = Script(lambda t: t in ("defer", "noise"))
        self.assertEqual(trackp.label_decisions(self.root, SLUG, [path], person.ask, person.say), 2)
        labels = read(os.path.join(self.dir, trackp.LABELS))
        self.assertEqual([(l["point"], l["options"][l["label"]]) for l in labels], [("D3", "defer"), ("D5", "noise")])
        self.assertFalse(any("chosen" in s or "R0" in s for s in person.shown))
        self.assertEqual(trackp.label_decisions(self.root, SLUG, [path], person.ask, person.say), 0)

    def test_a_label_becomes_one_pairwise_choice_per_rejected_option(self):
        path = self.label_run("run1", [("D3", ["accept", "reject", "defer"], 0)])
        person = Script(lambda t: t == "reject")
        trackp.label_decisions(self.root, SLUG, [path], person.ask, person.say)
        choices = trackp.labels_to_choices(SLUG, read(os.path.join(self.dir, trackp.LABELS)))
        self.assertEqual(len(choices), 2)
        for c in choices:
            self.assertEqual(c.a_text if c.chosen == "a" else c.b_text, "reject")
            self.assertEqual(c.decision_point, "D3")

    def test_noise_ceiling_is_agreement_on_rechecked_items_after_the_wait(self):
        self.seed(n=20)
        now = datetime.datetime.now(datetime.timezone.utc)
        early = Script(library_rank)
        self.assertEqual(trackp.recheck(self.root, SLUG, early.ask, early.say, frac=1.0, now=now), 0)
        answered = [c for c in read(os.path.join(self.dir, trackp.SEED_CHOICES))]
        later = Script(library_rank)
        n = trackp.recheck(self.root, SLUG, later.ask, later.say, frac=1.0, now=now + datetime.timedelta(days=4))
        self.assertEqual(n, len(answered))
        self.assertEqual(trackp.noise_ceiling(self.root, SLUG)["seed"]["agreement"], 1.0)

    def test_noise_ceiling_counts_changed_answers(self):
        self.seed(n=4, fixed="a")
        flip = Script(fixed="1")   # recheck reverses the order, so "1" is the old b
        later = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=4)
        trackp.recheck(self.root, SLUG, flip.ask, flip.say, frac=1.0, now=later)
        self.assertEqual(trackp.noise_ceiling(self.root, SLUG)["seed"], {"n": 4, "agreement": 0.0, "ci90": [0.0, 0.0]})

    def test_split_holds_out_stable_seed_pairs_and_late_runs(self):
        self.seed(n=20, fixed="a")
        first_test = {c.example_id for c in trackp.split(self.root, SLUG)["test"]}
        self.seed(n=40, fixed="b")
        parts = trackp.split(self.root, SLUG)
        self.assertTrue(first_test <= {c.example_id for c in parts["test"]})
        self.assertTrue(4 <= len(parts["test"]) <= 14)
        path = self.label_run("late", [("D3", ["accept", "reject", "defer"], 0)])
        person = Script(lambda t: t == "defer")
        trackp.label_decisions(self.root, SLUG, [path], person.ask, person.say)
        today = datetime.date.today().isoformat()
        held = trackp.split(self.root, SLUG, label_cutoff=today)
        self.assertEqual(sum(c.source == "label" for c in held["test"]), 2)
        self.assertEqual(sum(c.source == "label" for c in held["history"] + held["val"]), 0)

    def test_e2_scores_held_out_choices_and_never_overwrites(self):
        self.seed(n=30, fixed="a")

        class AlwaysA(UserModel):   # the real fit() checks for history/val leakage
            def predict(self, context, options):
                return Prediction(choice="a", confidence=0.9, probabilities=[0.9, 0.1])
        out = os.path.join(self.root, "e2.json")
        rep = trackp.run_e2(self.root, SLUG, {"always_a": lambda: AlwaysA(OfflineLLM())}, out)
        self.assertEqual(rep["methods"]["always_a"]["accuracy"], 1.0)
        self.assertEqual(rep["methods"]["always_a"]["n"], rep["sizes"]["test"])
        with self.assertRaises(FileExistsError):
            trackp.run_e2(self.root, SLUG, {"always_a": lambda: AlwaysA(OfflineLLM())}, out)


if __name__ == "__main__":
    unittest.main()
