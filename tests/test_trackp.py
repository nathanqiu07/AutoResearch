"""WS B personal track: trade-off seed items, decision labels, noise ceiling, hold-out split, E2.

Most tests drive the CLI the way an agent does: `pending` to see items, `record` to save
the person's reply."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from autoresearch.cli import resolve_arm
from autoresearch.llm import LLM, OfflineLLM
from autoresearch.research.advisor import load_user_model
from autoresearch.research.decisions import DecisionLog
from autoresearch.taste import agreement, tradeoffs, trackp
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import Prediction, UserModel

SLUG = "teammate"
BANK = tradeoffs.load_bank()
POLE_ONE = {r[k] for r in BANK for k in ("pole_1", "scenario_1") if k in r}
AXIS_NAMES = [r["axis"] for r in BANK]
N_STANCE = len(BANK)
N_SEED = N_STANCE + sum(tradeoffs.has_scenario(r) for r in BANK)


def pole_one(text):
    """A consistent person: always prefers pole 1 of every trade-off."""
    return int(text in POLE_ONE)


class FakeJudge(LLM):
    """Votes for an option in `lopsided` whenever it is shown, else for the first option shown
    (5 of 10, so the pair passes). Asked to rewrite, it prefixes both options with "Reworded: "."""

    def __init__(self, lopsided=()):
        super().__init__()
        self.lopsided = set(lopsided)

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        o1 = prompt.split("Option 1: ", 1)[1].split("\n", 1)[0]
        o2 = prompt.split("Option 2: ", 1)[1].split("\n", 1)[0]
        if "Rewrite both options" in prompt:
            return json.dumps({"option_1": "Reworded: " + o1, "option_2": "Reworded: " + o2})
        return json.dumps({"choice": 2 if o2 in self.lopsided else 1})


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

    def test_gate_call_cap_counts_attempts_before_dispatch(self):
        inner = FakeJudge()
        capped = trackp.CallCappedLLM(inner, 2)
        capped.complete('Option 1: A\nOption 2: B\n')
        capped.complete('Option 1: A\nOption 2: B\n')
        with self.assertRaisesRegex(RuntimeError, 'gate call cap reached: 2'):
            capped.complete('Option 1: A\nOption 2: B\n')
        self.assertEqual(capped.attempts, 2)

    def answer(self, kind, prefer, *extra, reason="because", limit=1000):
        """The agent loop: show each pending item, record the person's pick."""
        items = self.cli("pending", "--kind", kind, "--limit", limit, *extra)["items"]
        for it in items:
            best = max(range(len(it["options"])), key=lambda j: prefer(it["options"][j]))
            self.cli("record", "--id", it["id"], "--choice", best + 1, "--reason", reason, *extra)
        return items

    def seed(self, n=1000, prefer=pole_one, seed=1):
        """Write the seed set and answer the first n items it serves."""
        self.seed_pairs_only(seed)
        return self.answer("seed", prefer, limit=n)

    def judge(self, pairs=None, lopsided=()):
        """Item-gate votes for the pairs (default: this person's), as 'gate' records them."""
        agreement.judge(self.root, self.pairs() if pairs is None else pairs, FakeJudge(lopsided), workers=1)

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
        self.cli("seed-pairs")
        self.assertTrue(any(s.startswith(f"{N_SEED} pair(s) need 'gate'") for s in self.cli("status", "--decisions")["next"]))
        self.judge()
        self.assertTrue(any(s.startswith(f"{N_SEED} seed item(s) waiting") for s in self.cli("status", "--decisions")["next"]))

    def pairs(self):
        return read(os.path.join(self.dir, trackp.SEED_PAIRS))

    def add_llm_pair(self):
        row = {"pair_id": "llm000000001", "form": "scenario", "axis": "grading", "decision_point": "D2",
               "origin": "llm", "item": "metric_inflation", "context": "ctx", "question": "Which?", "a_text": "judge all",
               "b_text": "grade sixty", "a_pole": 1, "b_pole": 2}
        trackp.write_seed_pairs(self.root, SLUG, [row])
        return "seed:" + row["pair_id"]

    def test_seed_pairs_are_every_stance_and_one_scenario_per_scenario_axis(self):
        self.seed_pairs_only()
        forms = [p["form"] for p in self.pairs()]
        self.assertEqual((forms.count("stance"), forms.count("scenario")), (N_STANCE, N_SEED - N_STANCE))

    def test_pending_groups_scenarios_by_item_and_puts_stance_last(self):
        self.seed_pairs_only()
        groups = [it["group"] for it in self.cli("pending", "--kind", "seed", "--limit", 1000)["items"]]
        self.assertEqual(groups[-N_STANCE:], ["stance"] * N_STANCE)
        scenario_groups = groups[:-N_STANCE]
        self.assertEqual(len(set(scenario_groups)), 2)
        switches = sum(a != b for a, b in zip(scenario_groups, scenario_groups[1:]))
        self.assertEqual(switches, 1)

    def test_pending_never_shows_axis_poles_or_decision_point(self):
        self.seed_pairs_only()
        for it in self.cli("pending", "--kind", "seed", "--limit", 1000)["items"]:
            self.assertFalse({"axis", "a_pole", "b_pole", "decision_point", "form"} & set(it))
            self.assertTrue(it["question"])
            for name in AXIS_NAMES:
                self.assertNotIn(name, it["context"] + it["question"])

    def test_rerunning_seed_pairs_keeps_answers_and_adds_no_duplicates(self):
        self.seed(n=15)
        first = read(os.path.join(self.dir, trackp.SEED_CHOICES))
        self.seed_pairs_only()
        self.assertEqual(len(self.pairs()), N_SEED)
        self.assertEqual(read(os.path.join(self.dir, trackp.SEED_CHOICES)), first)
        self.assertEqual(self.cli("pending", "--kind", "seed", "--limit", 1000)["n_pending"], N_SEED - 15)

    def seed_pairs_only(self, seed=1):
        self.cli("seed-pairs", "--seed", seed, "--scenarios", "metric_inflation", "fabrication")
        self.judge()

    def test_no_pair_is_pending_until_the_gate_has_judged_it(self):
        item_id = self.add_llm_pair()
        self.assertEqual(self.cli("pending", "--kind", "seed")["n_pending"], 0)
        with self.assertRaises(SystemExit):
            self.cli("record", "--id", item_id, "--choice", 1)
        self.judge()
        self.assertEqual(self.cli("pending", "--kind", "seed")["items"][0]["id"], item_id)

    def test_gate_hides_a_lopsided_pair_and_serves_its_rewrite_and_writes_it_to_the_bank(self):
        bank = os.path.join(self.root, "bank.jsonl")
        with open(tradeoffs.BANK_PATH) as src, open(bank, "w") as dst:
            dst.write(src.read())
        self.cli("seed-pairs", "--seed", 1, "--scenarios", "metric_inflation", "fabrication")
        target = next(p for p in self.pairs() if p["form"] == "stance")
        favoured = target["a_text"]
        rep = trackp.gate(self.root, SLUG, FakeJudge([favoured]), bank_path=bank, workers=1)
        self.assertEqual((rep["lopsided"], rep["rewritten"]), (1, 1))
        ids = [it["id"] for it in self.cli("pending", "--kind", "seed", "--limit", 1000)["items"]]
        self.assertEqual(len(ids), N_SEED)
        self.assertNotIn("seed:" + target["pair_id"], ids)
        (new,) = [p for p in self.pairs() if p.get("parent") == target["pair_id"]]
        self.assertIn("seed:" + new["pair_id"], ids)
        self.assertEqual(new["a_text"], "Reworded: " + favoured)
        row = next(r for r in tradeoffs.load_bank(bank) if r["axis"] == target["axis"])
        self.assertIn("Reworded: " + favoured, (row["pole_1"], row["pole_2"]))
        again = trackp.gate(self.root, SLUG, FakeJudge([favoured]), bank_path=bank, workers=1)
        self.assertEqual(again["lopsided"], 0)

    def test_recorded_answers_are_choices_with_reasons_and_leave_nothing_pending(self):
        shown = self.seed()
        rows = read(os.path.join(self.dir, trackp.SEED_CHOICES))
        self.assertEqual(len(rows), N_SEED)
        for r in rows:
            winner = r["a_text"] if r["chosen"] == "a" else r["b_text"]
            self.assertEqual(winner, max(r["a_text"], r["b_text"], key=pole_one))
            pair = next(p for p in self.pairs() if p["pair_id"] == r["example_id"])
            self.assertEqual((r["reason"], r["decision_point"], r["source"]), ("because", pair["decision_point"], "seed"))
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
        rechecked = self.answer("recheck", pole_one, "--frac", 1, "--min-days", 0)
        self.assertEqual(len(rechecked), len(answered))
        first_shown = {"recheck:" + it["id"]: it["options"] for it in answered}
        for it in rechecked:
            self.assertEqual(it["options"], first_shown[it["id"]][::-1])
        self.assertEqual(trackp.noise_ceiling(self.root, SLUG)["seed"]["agreement"], 1.0)

    def test_noise_ceiling_counts_changed_answers(self):
        self.seed(n=4)
        self.answer("recheck", lambda t: -pole_one(t), "--frac", 1, "--min-days", 0)
        self.assertEqual(trackp.noise_ceiling(self.root, SLUG)["seed"], {"n": 4, "agreement": 0.0, "ci90": [0.0, 0.0]})

    def test_terminal_loop_records_the_same_answer_as_record(self):
        self.cli("seed-pairs")
        self.judge()
        replies, said = iter(["2", "skip", "q"]), []
        items = trackp.pending_items(self.root, SLUG, ("seed",))
        n = trackp.ask_items(self.root, SLUG, items, ask=lambda _: next(replies), say=said.append)
        self.assertEqual(n, 1)
        self.assertIn(items[0]["question"], said)
        (row,) = read(os.path.join(self.dir, trackp.SEED_CHOICES))
        self.assertEqual((row["chosen"], row["reason"]), ("b", ""))

    def test_start_sets_up_by_name_takes_consent_and_resumes(self):
        from autoresearch.research.measure import SCENARIOS
        self.judge(tradeoffs.build_seed_pairs(BANK, [SCENARIOS[n] for n in sorted(SCENARIOS)], 0))
        said = []
        self.assertEqual(trackp.start(self.root, "Jane Q. Doe", ask=lambda _: "n", say=said.append), 0)
        d = os.path.join(self.root, "jane_q_doe")
        self.assertFalse(os.path.exists(os.path.join(d, trackp.SEED_CHOICES)))
        replies = iter(["yes", "1", "q"])
        self.assertEqual(trackp.start(self.root, "Jane Q. Doe", ask=lambda _: next(replies), say=said.append), 1)
        with open(os.path.join(d, "CONSENT.md")) as f:
            consent = f.read()
        self.assertNotIn("- [ ]", consent)
        self.assertIn("Recorded by: Jane Q. Doe", consent)
        replies = iter(["2", "q"])   # consent is not asked again, and the answered item is not re-served
        self.assertEqual(trackp.start(self.root, "Jane Q. Doe", ask=lambda _: next(replies), say=said.append), 1)
        self.assertEqual(len(read(os.path.join(d, trackp.SEED_CHOICES))), 2)
        self.assertEqual(len(trackp.pending_items(self.root, "jane_q_doe", ("seed",))), N_SEED - 2)

    def test_split_holds_out_stable_seed_pairs_and_late_runs(self):
        self.seed()
        first_test = {c.example_id for c in trackp.split(self.root, SLUG)["test"]}
        self.seed(seed=2)
        parts = trackp.split(self.root, SLUG)
        self.assertTrue(first_test <= {c.example_id for c in parts["test"]})
        n = len(parts["test"] + parts["history"] + parts["val"])
        self.assertTrue(0.05 * n <= len(parts["test"]) <= 0.4 * n)
        path = self.label_run("late", [("D3", ["accept", "reject", "defer"], 0)])
        self.answer("label", lambda t: t == "defer", "--decisions", path)
        run_date = read(os.path.join(self.dir, trackp.LABELS))[0]["run_date"]
        held = trackp.split(self.root, SLUG, label_cutoff=run_date)
        self.assertEqual(sum(c.source == "label" for c in held["test"]), 2)
        self.assertEqual(sum(c.source == "label" for c in held["history"] + held["val"]), 0)

    def test_fit_writes_a_user_model_the_loop_loads_and_history_without_held_out_choices(self):
        self.seed()
        trackp.fit_user_model(self.root, SLUG, lambda: create_method("m1", OfflineLLM()))
        model, source = load_user_model(self.dir, None, OfflineLLM())
        self.assertEqual(model.method_id, "m1")
        self.assertIn("usermodel.json", source)
        held = {c.example_id for c in trackp.split(self.root, SLUG)["test"]}
        exported = {r["example_id"] for r in read(os.path.join(self.dir, trackp.HISTORY))}
        self.assertEqual(len(exported), N_SEED - len(held))
        self.assertFalse(exported & held)

    def test_e2_scores_held_out_choices_and_never_overwrites(self):
        self.seed()
        held = trackp.split(self.root, SLUG)["test"]

        class PrefersLater(UserModel):   # the real fit() checks for history/val leakage
            def predict(self, context, options):
                a_wins = pole_one(options[0]) > pole_one(options[1])
                return Prediction(choice="a" if a_wins else "b", confidence=0.9,
                                  probabilities=[0.9, 0.1] if a_wins else [0.1, 0.9])
        out = os.path.join(self.root, "e2.json")
        rep = trackp.run_e2(self.root, SLUG, {"later": lambda: PrefersLater(OfflineLLM())}, out)
        self.assertEqual(rep["methods"]["later"]["accuracy"], 1.0)
        self.assertEqual(rep["methods"]["later"]["n"], len(held))
        with self.assertRaises(FileExistsError):
            trackp.run_e2(self.root, SLUG, {"later": lambda: PrefersLater(OfflineLLM())}, out)

    def test_e2_and_fit_drop_answers_to_pairs_that_fail_the_gate_in_every_split(self):
        self.seed()   # answered while the gate passed every pair; a stricter judge then fails two
        parts = trackp.split(self.root, SLUG)
        dropped = {parts["test"][0].example_id, parts["history"][0].example_id}
        os.remove(os.path.join(self.root, agreement.AGREEMENT))
        self.judge(lopsided=[next(c.a_text for part in parts.values() for c in part if c.example_id == k)
                             for k in dropped])
        rep = trackp.run_e2(self.root, SLUG, {"m1": lambda: create_method("m1", OfflineLLM())},
                            os.path.join(self.root, "e2.json"))
        self.assertEqual(rep["methods"]["m1"]["n"], len(parts["test"]) - 1)
        trackp.fit_user_model(self.root, SLUG, lambda: create_method("m1", OfflineLLM()))
        exported = {r["example_id"] for r in read(os.path.join(self.dir, trackp.HISTORY))}
        self.assertFalse(exported & dropped)

if __name__ == "__main__":
    unittest.main()
