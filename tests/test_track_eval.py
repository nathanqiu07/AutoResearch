"""WS B public-track E2: paired-order scoring, document-clustered intervals, baselines that see
nothing after the cutoff, and the distractor gate."""
import json
import os
import tempfile
import unittest
from dataclasses import asdict
from unittest import mock

from autoresearch.llm import LLM
from autoresearch.taste import agreement, timesplit, track_eval
from autoresearch.taste.researcher import Researcher
from autoresearch.taste.usermodel import Choice


class OptionLLM(LLM):
    """Answers user-model prediction prompts. `pick(context, options)` returns the index chosen;
    every prompt is recorded."""

    def __init__(self, pick):
        super().__init__()
        self.pick, self.prompts = pick, []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        if "INPUT_JSON:" not in prompt:
            return "{}"
        payload = json.loads(prompt.split("INPUT_JSON:\n", 1)[1])
        i = self.pick(payload["context"], payload["options"])
        return json.dumps({"probabilities": [1.0 if k == i else 0.0 for k in range(len(payload["options"]))],
                           "rationale": ""})


def first_option(context, options):
    return 0


def taken_option(context, options):
    return next(i for i, o in enumerate(options) if o.startswith("TAKEN"))


def choice(k, group, date="2025-01-01", context="A team had to choose."):
    return Choice(user_id="marius_test", context=context, a_text=f"TAKEN_{k}", b_text=f"OTHER_{k}",
                  chosen="a", decision_point="D1", timestamp=date, source="timesplit",
                  example_id=f"p{k}", group_id=group)


def write_identity(root):
    with open(os.path.join(root, timesplit.IDENTITY), "w") as f:
        json.dump({"name": "Marius Hobbhahn", "banned": ["hobbhahn", "marius", "apollo"],
                   "exclude_text": ["Hobbhahn"], "exclude_domains": ["apolloresearch.ai"]}, f)


def write_corpus(root, name, published, body):
    os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
    with open(os.path.join(root, "corpus", name), "w") as f:
        f.write(f"---\nurl: https://ex.org/{name}\npublishedDate: {published}\n---\n{body}")


def write_agreement(root, ids, agreeing=()):
    """Agreement rows as the 'agree' command records them: pairs in `agreeing` get 0.9 both ways."""
    with open(os.path.join(root, agreement.AGREEMENT), "w") as f:
        f.writelines(json.dumps({"example_id": k, "p_chosen": [0.9, 0.9] if k in agreeing else [0.5, 0.5],
                                 "judge": "fake", "timestamp": "t"}) + "\n" for k in ids)


class ScoringTest(unittest.TestCase):
    def test_pair_counts_only_when_both_orders_are_right(self):
        model = track_eval.NamedNoHistory(OptionLLM(first_option), None)
        self.assertFalse(track_eval.paired_correct(model, choice(1, "g")))

    def test_pair_counts_when_both_orders_pick_his_option(self):
        model = track_eval.NamedNoHistory(OptionLLM(taken_option), None)
        self.assertTrue(track_eval.paired_correct(model, choice(1, "g")))

    def test_cluster_ci_resamples_groups_not_pairs(self):
        acc, lo, hi = track_eval.cluster_ci({"g1": [True] * 10, "g2": [False]})
        self.assertAlmostEqual(acc, 10 / 11)
        self.assertLessEqual(lo, 0.5)   # pair-level resampling would put this near 0.73
        self.assertEqual(hi, 1.0)

    def test_intervals_refuse_an_empty_set(self):
        with self.assertRaisesRegex(ValueError, "no pairs"):
            track_eval.cluster_ci({})
        with self.assertRaisesRegex(ValueError, "no pairs"):
            track_eval.cluster_diff_ci({}, {})

    def test_cluster_diff_ci_of_identical_arms_is_zero(self):
        by_group = {"g1": [True, False], "g2": [True]}
        self.assertEqual(track_eval.cluster_diff_ci(by_group, by_group), (0.0, 0.0, 0.0))


class ArmTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        write_corpus(self.root, "research__early.txt", "2023-01-01", "EARLY_TEXT")
        write_corpus(self.root, "research__late.txt", "2025-01-01", "LATE_TEXT")
        self.researcher = Researcher("marius_test", self.root)

    def test_docs_arm_keeps_a_document_longer_than_its_whole_budget(self):
        write_corpus(self.root, "research__long.txt", "2023-06-01", "LONG_START " + "x" * 100_000)
        llm = OptionLLM(first_option)
        track_eval.docs_arm(self.researcher, llm, "2024-06-01").predict("ctx", ["x", "y"])
        self.assertIn("LONG_START", llm.prompts[0])
        self.assertIn("EARLY_TEXT", llm.prompts[0])

    def test_docs_arm_sees_no_document_from_after_cutoff(self):
        llm = OptionLLM(first_option)
        track_eval.docs_arm(self.researcher, llm, "2024-06-01").predict("ctx", ["x", "y"])
        self.assertIn("EARLY_TEXT", llm.prompts[0])
        self.assertNotIn("LATE_TEXT", llm.prompts[0])

    def test_reply_with_json_in_a_code_fence_is_still_read(self):
        class FencedLLM(OptionLLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                return "Here is my answer:\n```json\n" + super().complete(prompt, system, max_tokens, temperature) + "\n```"
        model = track_eval.NamedNoHistory(track_eval.JsonReply(FencedLLM(taken_option)), None)
        self.assertTrue(track_eval.paired_correct(model, choice(1, "g")))

    def test_prose_reply_is_asked_again_for_json(self):
        class ProseOnceLLM(OptionLLM):
            calls = 0

            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                self.calls += 1
                if self.calls == 1:
                    return "Option 1 is the sound reading, since the ablation kept distance constant."
                return super().complete(prompt, system, max_tokens, temperature)
        model = track_eval.NamedNoHistory(track_eval.JsonReply(ProseOnceLLM(taken_option)), None)
        self.assertTrue(track_eval.paired_correct(model, choice(1, "g")))

    def test_self_corrected_reply_uses_the_last_json_object(self):
        class CorrectingLLM(OptionLLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                final = super().complete(prompt, system, max_tokens, temperature)
                wrong = json.dumps({"probabilities": list(reversed(json.loads(final)["probabilities"])),
                                    "rationale": "first try"})
                return wrong + "\n\nCorrection: final answer:\n\n" + final
        model = track_eval.NamedNoHistory(track_eval.JsonReply(CorrectingLLM(taken_option)), None)
        self.assertTrue(track_eval.paired_correct(model, choice(1, "g")))

    def test_probabilities_that_do_not_sum_to_one_are_rescaled(self):
        class SloppyLLM(OptionLLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                reply = json.loads(super().complete(prompt, system, max_tokens, temperature))
                reply["probabilities"] = [0.55 if p else 0.5 for p in reply["probabilities"]]
                return json.dumps(reply)
        model = track_eval.NamedNoHistory(track_eval.JsonReply(SloppyLLM(taken_option)), None)
        self.assertTrue(track_eval.paired_correct(model, choice(1, "g")))

    def test_named_m0_mentions_the_name_and_plain_m0_does_not(self):
        llm = OptionLLM(first_option)
        track_eval.NamedNoHistory(llm, "Marius Hobbhahn").predict("ctx", ["x", "y"])
        track_eval.NamedNoHistory(llm, None).predict("ctx", ["x", "y"])
        self.assertIn("Marius Hobbhahn", llm.prompts[0])
        self.assertNotIn("Marius Hobbhahn", llm.prompts[1])


class GateTest(unittest.TestCase):
    def setup_pairs(self, n_flagged, split="heldout"):
        root = tempfile.mkdtemp()
        rows = [{"pair_id": f"p{k}", "decision_id": f"d{k}", "split": split, "date": "2025-01-01",
                 "source_doc": "x", "url": f"https://ex.org/{k}", "decision_point": "D1",
                 "context": "FLAG" if k < n_flagged else "fine", "a_text": f"TAKEN_{k}", "b_text": f"OTHER_{k}",
                 "chosen": "a", "reason": "", "tag": "exa_verified", "distractor_source": "named",
                 "author_position": "last", "cutoff": "2024-06-01", "seed": 0} for k in range(10)]
        with open(os.path.join(root, timesplit.PAIRS), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        write_identity(root)
        researcher = Researcher("marius_test", root)
        timesplit.write_choice_files(researcher)
        return researcher

    def judge(self):
        return OptionLLM(lambda ctx, opts: taken_option(ctx, opts) if ctx.endswith("FLAG") else 1 - taken_option(ctx, opts))

    def regenerate(self, calls):
        def regen(pair):
            calls.append(pair["pair_id"])
            return dict(pair, pair_id=pair["pair_id"] + "r", context="fine", regenerated_from=pair["pair_id"])
        return regen

    def test_gate_regenerates_only_when_flagged_share_exceeds_threshold(self):
        calls = []
        report = track_eval.distractor_gate(self.setup_pairs(8), self.judge(), self.regenerate(calls))
        self.assertEqual((report["flagged_before"], report["regenerated"], report["flagged_after"]), (8, 8, 0))

    def test_gate_leaves_pairs_alone_at_or_below_threshold(self):
        calls = []
        researcher = self.setup_pairs(7)
        report = track_eval.distractor_gate(researcher, self.judge(), self.regenerate(calls))
        self.assertEqual((calls, report["regenerated"]), ([], 0))

    def test_regenerated_pairs_replace_the_old_ones_in_the_heldout_file(self):
        researcher = self.setup_pairs(8)
        track_eval.distractor_gate(researcher, self.judge(), self.regenerate([]))
        ids = {c.example_id for c in track_eval.load_choices(os.path.join(researcher.root, timesplit.HELDOUT))}
        self.assertIn("p0r", ids)
        self.assertNotIn("p0", ids)

    def test_gate_report_has_the_style_leak_probe(self):
        report = track_eval.distractor_gate(self.setup_pairs(0), self.judge(), self.regenerate([]))
        self.assertEqual(set(report["style_leak"]), {"rate", "ci_low", "ci_high", "n_pairs", "flagged"})
        self.assertEqual(report["style_leak"]["n_pairs"], 10)


    def test_gate_refuses_no_heldout_pairs_and_can_run_again(self):
        researcher = self.setup_pairs(0, split="history")
        with self.assertRaisesRegex(ValueError, "no held-out pairs"):
            track_eval.distractor_gate(researcher, self.judge(), self.regenerate([]))
        self.assertFalse(os.path.exists(os.path.join(researcher.root, track_eval.GATE)))


class StyleLeakTest(unittest.TestCase):
    def test_judge_that_spots_the_real_option_is_flagged(self):
        choices = [choice(k, f"g{k % 3}") for k in range(6)]
        leak = track_eval.style_leak(choices, track_eval.style_scores(choices, OptionLLM(taken_option)))
        self.assertEqual((leak["rate"], leak["flagged"]), (1.0, True))

    def test_position_biased_judge_sits_at_chance(self):
        choices = [choice(k, f"g{k % 3}") for k in range(6)]
        leak = track_eval.style_leak(choices, track_eval.style_scores(choices, OptionLLM(first_option)))
        self.assertEqual((leak["rate"], leak["flagged"]), (0.5, False))


class FakeMethod:
    def __init__(self, fitted):
        self.fitted = fitted

    def fit(self, history, val):
        self.fitted.append([c.example_id for c in history])

    def predict(self, context, options):
        return track_eval.NamedNoHistory(OptionLLM(first_option), None).predict(context, options)


class SelectAndE2Test(unittest.TestCase):
    def test_select_method_fits_on_the_earliest_groups_and_scores_on_the_latest(self):
        history = [choice(k, f"g{k}", date=f"2023-{k + 1:02d}-01") for k in range(10)]
        fitted = []
        with mock.patch.object(track_eval, "create_method", lambda m, llm, **kw: FakeMethod(fitted)):
            best, scores = track_eval.select_method(history, None, candidates=("m2", "m3"))
        self.assertTrue(set(fitted[0]) <= {f"p{k}" for k in range(8)})
        self.assertEqual(set(scores), {"m2", "m3"})
        self.assertIn(best, ("m2", "m3"))

    def test_select_method_refuses_history_from_one_document(self):
        history = [choice(k, "g0", date=f"2023-{k + 1:02d}-01") for k in range(5)]
        with self.assertRaisesRegex(ValueError, "at least two documents"):
            track_eval.select_method(history, None, candidates=("m2",))

    def test_e2_refuses_no_heldout_pairs(self):
        root = tempfile.mkdtemp()
        researcher = Researcher("marius_test", root)
        rows = [dict(asdict(choice(k, f"g{k}")), split="history", pair_id=f"p{k}", date="2023-06-01",
                     tag="exa_verified", cutoff="2024-06-01", author_position="last",
                     distractor_source="named", url=f"g{k}") for k in range(4)]
        with open(os.path.join(root, timesplit.PAIRS), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        write_identity(root)
        timesplit.write_choice_files(researcher)
        with self.assertRaisesRegex(ValueError, "no held-out pairs"):
            track_eval.run_e2(researcher, OptionLLM(taken_option), "Marius Hobbhahn", "m1")

    def e2_root(self):
        root = tempfile.mkdtemp()
        write_corpus(root, "research__early.txt", "2023-01-01", "EARLY_TEXT")
        researcher = Researcher("marius_test", root)
        rows = [dict(asdict(choice(k, f"g{k}")), split="history" if k < 4 else "heldout", pair_id=f"p{k}",
                     date="2023-06-01" if k < 4 else "2025-01-01", tag="exa_verified", cutoff="2024-06-01",
                     author_position="last", distractor_source="named", url=f"g{k}")
                for k in range(8)]
        with open(os.path.join(root, timesplit.PAIRS), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        write_identity(root)
        timesplit.write_choice_files(researcher)
        return root, researcher

    def test_e2_report_has_every_arm_and_the_contamination_gap(self):
        root, researcher = self.e2_root()
        write_agreement(root, [f"p{k}" for k in range(8)])
        llm = OptionLLM(taken_option)
        report = track_eval.run_e2(researcher, llm, "Marius Hobbhahn", "m1",
                                   out_path=os.path.join(root, "e2.json"))
        self.assertEqual(set(report["arms"]), {"m0", "m0_named", "m1_pairs", "m1_docs", "selected:m1"})
        self.assertIn("contamination_gap", report)
        self.assertEqual(report["n_pairs"], 4)
        self.assertEqual(report["arms"]["m0"]["accuracy"], 1.0)
        self.assertTrue(os.path.exists(os.path.join(root, "e2.json")))

    def test_e2_drops_pairs_the_judge_decides_for_him_from_history_and_heldout(self):
        root, researcher = self.e2_root()
        write_agreement(root, [f"p{k}" for k in range(8)], agreeing={"p0", "p5"})
        report = track_eval.run_e2(researcher, OptionLLM(taken_option), "Marius Hobbhahn", "m1")
        self.assertEqual((report["n_history"], report["n_pairs"]), (3, 3))
        self.assertEqual(report["agreement_filter"]["dropped"], {"history": 1, "heldout": 1})

    def test_e2_refuses_pairs_the_judge_never_saw(self):
        root, researcher = self.e2_root()
        write_agreement(root, [f"p{k}" for k in range(7)])
        with self.assertRaisesRegex(ValueError, "1 pair"):
            track_eval.run_e2(researcher, OptionLLM(taken_option), "Marius Hobbhahn", "m1")


if __name__ == "__main__":
    unittest.main()
