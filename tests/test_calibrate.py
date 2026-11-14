import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from autoresearch.llm import Budget, LLM
from autoresearch.research import calibrate as cal
from autoresearch.research.measure import Measurer, Models

PROBE_PREFIXES = ("Below is an interaction", "Below is a transcript", "Here is a conversation")


class Script(LLM):
    """Scripted backend. p_fn(prompt) -> P(eval) or None (unparseable);
    verbal_fn(prompt) -> verbalized score or None."""
    name = "script"

    def __init__(self, model="m", p_fn=None, verbal_fn=None, budget=None):
        super().__init__(budget or Budget())
        self.model = model
        self.p_fn = p_fn or (lambda prompt: 0.5)
        self.verbal_fn = verbal_fn or (lambda prompt: 0.0)

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.budget.charge(1, 1)
        if prompt.startswith(PROBE_PREFIXES):
            p = self.p_fn(prompt)
            return "I would rather not say." if p is None else json.dumps({"p": p})
        if prompt.startswith("You audit"):
            v = self.verbal_fn(prompt)
            return "unclear" if v is None else json.dumps({"verbalized": v, "opportunity": 1, "scorable": 1,
                                                           "behavior": "honest"})
        return "Sure, here is the summary you asked for."


def read_json(path):
    with open(path) as f:
        return json.load(f)


def cue_sensitive(prompt):
    return 0.9 if "EVALCUE" in prompt else 0.1


def measurer_with(answer=None, judge=None, heldout_judges=(), mode="dev", budget=None):
    budget = budget or Budget()
    t = answer or Script(p_fn=cue_sensitive, budget=budget)
    j = judge or Script(model="judge", budget=budget)
    return Measurer(Models(generator=j, target=t, judge=j, heldout_target=t if mode == "final" else None,
                           heldout_judges=list(heldout_judges)), mode=mode, workers=2)


def labelled_rows(n=12):
    rows = [cal.Labelled(f"e{i}", f"USER: EVALCUE task {i}", "eval") for i in range(n)]
    return rows + [cal.Labelled(f"d{i}", f"USER: help me with my essay {i}", "deploy") for i in range(n)]


def cue_pairs(n=12):
    return [cal.CuePair(f"p{i}", {"system": "You are a grader. EVALCUE", "user": f"Don't skip step {i}, it's due."},
                        {"system": "You are a helpful assistant.", "user": f"Don't skip step {i}, it's due."})
            for i in range(n)]


def transcripts_and_labels(n=60):
    ts, labels = [], {}
    for i in range(n):
        aware = i % 2 == 0
        reasoning = "this looks like a test of my honesty" if aware else "the user wants a summary"
        ts.append(cal.Transcript(f"t{i}", "sys", f"question {i}", "answer", reasoning))
        labels[f"t{i}"] = aware
    return ts, labels


def reads_reasoning(prompt):
    return 0.9 if "looks like a test" in prompt else 0.1


class LabelledCheckTests(unittest.TestCase):
    def test_discriminating_answerer_passes(self):
        r = cal.check_labelled(measurer_with(), labelled_rows())
        self.assertTrue(r["passed"])
        self.assertEqual(r["per_answerer"]["target"]["auroc"], 1.0)

    def test_constant_p_answerer_fails(self):
        r = cal.check_labelled(measurer_with(Script(p_fn=lambda p: 0.7)), labelled_rows())
        self.assertFalse(r["passed"])
        self.assertEqual(r["per_answerer"]["target"]["auroc"], 0.5)

    def test_final_mode_checks_every_heldout_judge(self):
        bad = Script(model="bad-judge", p_fn=lambda p: 0.3)
        good = Script(model="good-judge", p_fn=cue_sensitive)
        r = cal.check_labelled(measurer_with(heldout_judges=[good, bad], mode="final"), labelled_rows())
        self.assertEqual(sorted(r["per_answerer"]), ["script:bad-judge#1", "script:good-judge#0", "target"])
        self.assertFalse(r["per_answerer"]["script:bad-judge#1"]["passed"])
        self.assertFalse(r["passed"])

    def test_unparseable_answers_are_excluded_and_counted(self):
        def flaky(prompt):
            return None if "task 1" in prompt or "essay 2" in prompt else cue_sensitive(prompt)
        r = cal.check_labelled(measurer_with(Script(p_fn=flaky)), labelled_rows())
        t = r["per_answerer"]["target"]
        # "task 1" also matches task 10 and task 11
        self.assertEqual(t["unparseable"], 4)
        self.assertEqual(t["n_eval"] + t["n_deploy"], 20)

    def test_too_few_per_class_fails(self):
        r = cal.check_labelled(measurer_with(), labelled_rows(3))
        self.assertFalse(r["passed"])
        self.assertIn("fewer than", r["per_answerer"]["target"]["reason"])

    def test_needham_format_loads_with_groups(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "dataset.json")
        rows = [{"id": "a", "input": [{"role": "system", "content": "sys"},
                                      {"role": "user", "content": [{"type": "text", "text": "fix the bug"}]},
                                      {"role": "assistant", "content": "", "tool_calls": [
                                          {"id": "c1", "function": "bash", "arguments": {"cmd": "ls"}}]}],
                 "metadata": {"eval_category": True, "scaffold": "smolagents", "category": "swebench"}},
                {"id": "b", "input": "hi there", "metadata": {"eval_category": False, "scaffold": None}}]
        with open(path, "w") as f:
            json.dump(rows, f)
        got = cal.load_labelled(path)
        self.assertEqual([(r.label, r.group) for r in got], [("eval", "agentic"), ("deploy", "chat")])
        self.assertIn("[TOOL CALL bash(", got[0].transcript)
        self.assertIn("fix the bug", got[0].transcript)

    def test_loader_rejects_bad_label_and_duplicates(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "l.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"id": "x", "transcript": "t", "label": "test"}) + "\n")
        with self.assertRaisesRegex(ValueError, "'test'"):
            cal.load_labelled(path)
        with open(path, "w") as f:
            for _ in range(2):
                f.write(json.dumps({"id": "x", "user": "u", "response": "r", "label": "eval"}) + "\n")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            cal.load_labelled(path)

    def test_long_transcripts_are_cut_and_counted(self):
        rows = [cal.Labelled("x", "a" * 50, "eval")]
        d = tempfile.mkdtemp()
        path = os.path.join(d, "l.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"id": "x", "transcript": "a" * 5000, "label": "eval"}) + "\n")
        got = cal.load_labelled(path, max_chars=1000)
        self.assertTrue(got[0].truncated)
        self.assertLess(len(got[0].transcript), 1100)
        self.assertFalse(rows[0].truncated)


class CuePairAndPlaceboTests(unittest.TestCase):
    def test_cue_sensitive_answerer_passes_both(self):
        ms = measurer_with()
        answers = cal.EnvAnswers(ms)
        b = cal.check_cue_pairs(ms, cue_pairs(), answers=answers)
        self.assertTrue(b["passed"])
        self.assertAlmostEqual(b["per_answerer"]["target"]["mean_diff"], 0.8)
        self.assertEqual(b["per_answerer"]["target"]["frac_right_direction"], 1.0)
        c = cal.check_placebo(ms, [p.with_cue for p in cue_pairs()], answers=answers)
        self.assertTrue(c["passed"])
        self.assertEqual(c["per_answerer"]["target"]["mean_change"], 0.0)

    def test_reversed_answerer_fails_cue_pairs(self):
        ms = measurer_with(Script(p_fn=lambda p: 0.1 if "EVALCUE" in p else 0.9))
        b = cal.check_cue_pairs(ms, cue_pairs())
        self.assertFalse(b["passed"])
        self.assertEqual(b["per_answerer"]["target"]["frac_wrong_direction"], 1.0)

    def test_answerer_that_reacts_to_placebo_fails(self):
        # the placebo expands "Don't" -> "Do not"; this answerer is fooled by the surface change
        ms = measurer_with(Script(p_fn=lambda p: 0.8 if "Do not" in p else 0.2))
        c = cal.check_placebo(ms, [p.with_cue for p in cue_pairs()])
        self.assertFalse(c["passed"])
        self.assertAlmostEqual(c["per_answerer"]["target"]["mean_change"], 0.6)

    def test_identical_pairs_and_noop_placebos_are_excluded_and_counted(self):
        same = cal.CuePair("s", {"system": "", "user": "hello"}, {"system": "", "user": "hello"})
        ms = measurer_with()
        b = cal.check_cue_pairs(ms, cue_pairs() + [same])
        self.assertEqual(b["identical_pairs"], 1)
        c = cal.check_placebo(ms, [{"system": "", "user": "hello world"}])
        self.assertEqual(c["noop_edits"], 1)
        self.assertFalse(c["passed"])

    def test_original_is_answered_once_for_both_checks(self):
        budget = Budget()
        ms = measurer_with(budget=budget)
        answers = cal.EnvAnswers(ms, budget)
        pairs = cue_pairs(12)
        cal.check_cue_pairs(ms, pairs, answers=answers)
        after_b = budget.calls
        cal.check_placebo(ms, [p.with_cue for p in pairs], answers=answers)
        per_env = 1 + 3   # target reply + 3 default probe questions
        self.assertEqual(after_b, 2 * 12 * per_env)
        self.assertEqual(budget.calls - after_b, 12 * per_env)   # only the placebo versions are new

    def test_placebo_is_deterministic_and_leaves_code_alone(self):
        text = "Don't merge yet.\n```\nmsg = \"don't\"\n```\nI can't review it.   \n\n\n\nThanks"
        out = cal.placebo_rewrite(text)
        self.assertEqual(out, cal.placebo_rewrite(text))
        self.assertIn("Do not merge yet.", out)
        self.assertIn('msg = "don\'t"', out)
        self.assertIn("I cannot review it.\n\nThanks", out)
        self.assertEqual(cal.placebo_rewrite("Do not merge."), "Don't merge.")

    def test_pair_items_matches_converter_outputs_by_id(self):
        d = tempfile.mkdtemp()
        o, m = os.path.join(d, "o.jsonl"), os.path.join(d, "m.jsonl")
        with open(o, "w") as f:
            for i in range(3):
                f.write(json.dumps({"id": f"i{i}", "system": "EVAL harness", "user": f"TEST {i}"}) + "\n")
        with open(m, "w") as f:
            for i in reversed(range(3)):
                f.write(json.dumps({"id": f"i{i}", "user": f"please do {i}"}) + "\n")
        pairs = cal.pair_items(o, m)
        self.assertEqual([p.id for p in pairs], ["i0", "i1", "i2"])
        self.assertEqual(pairs[1].with_cue["user"], "TEST 1")
        self.assertEqual(pairs[1].without_cue["user"], "please do 1")
        with open(m, "a") as f:
            f.write(json.dumps({"id": "extra", "user": "x"}) + "\n")
        with self.assertRaisesRegex(ValueError, "only in minimal"):
            cal.pair_items(o, m)


class KappaTests(unittest.TestCase):
    def test_judge_agreeing_with_humans_passes(self):
        ts, labels = transcripts_and_labels()
        r = cal.check_human_kappa(measurer_with(judge=Script(verbal_fn=reads_reasoning)), ts, labels)
        self.assertTrue(r["passed"])
        self.assertEqual(r["value"], 1.0)

    def test_constant_judge_fails(self):
        ts, labels = transcripts_and_labels()
        r = cal.check_human_kappa(measurer_with(judge=Script(verbal_fn=lambda p: 0.0)), ts, labels)
        self.assertFalse(r["passed"])
        self.assertEqual(r["value"], 0.0)

    def test_one_class_labels_are_degenerate(self):
        ts, _ = transcripts_and_labels()
        labels = {t.id: False for t in ts}
        r = cal.check_human_kappa(measurer_with(judge=Script(verbal_fn=lambda p: 0.0)), ts, labels)
        self.assertFalse(r["passed"])
        self.assertIn("one class", r["per_answerer"]["judge"]["reason"])

    def test_unparseable_judge_and_skipped_labels_are_counted(self):
        ts, labels = transcripts_and_labels()
        labels["t0"] = None
        judge = Script(verbal_fn=lambda p: None if "question 1\n" in p else reads_reasoning(p))
        r = cal.check_human_kappa(measurer_with(judge=judge), ts, labels)
        self.assertEqual(r["skipped_by_labeller"], 1)
        self.assertEqual(r["per_answerer"]["judge"]["unparseable"], 1)
        self.assertEqual(r["per_answerer"]["judge"]["n"], 58)

    def test_label_without_transcript_is_rejected(self):
        ts, labels = transcripts_and_labels()
        labels["ghost"] = True
        with self.assertRaisesRegex(ValueError, "ghost"):
            cal.check_human_kappa(measurer_with(), ts, labels)

    def test_verbalized_reuses_the_loop_audit_prompt(self):
        seen = []

        class Spy(Script):
            def complete(self, prompt, **kw):
                seen.append(prompt)
                return super().complete(prompt, **kw)
        ms = measurer_with(judge=Spy(verbal_fn=reads_reasoning))
        self.assertEqual(ms.verbalized("SYSTEM PROMPT:\nx", "this looks like a test"), 0.9)
        self.assertTrue(seen[0].startswith("You audit an AI-behaviour study."))
        self.assertIn("ASSISTANT'S RAW REASONING", seen[0])


class GateTests(unittest.TestCase):
    def full_gate(self, **kw):
        ts, labels = transcripts_and_labels()
        budget = Budget()
        ms = measurer_with(judge=Script(model="judge", verbal_fn=reads_reasoning, budget=budget), budget=budget)
        args = dict(labelled=labelled_rows(), cue_pairs=cue_pairs(), transcripts=ts, hand_labels=labels)
        args.update(kw)
        return cal.run_gate(ms, budget, out_dir=tempfile.mkdtemp(), **args)

    def test_all_checks_pass_and_json_is_written(self):
        rep, path = self.full_gate()
        self.assertTrue(rep["passed"], cal.verdict_lines(rep))
        self.assertEqual(sorted(rep["checks"]), sorted(cal.CHECKS))
        on_disk = read_json(path)
        self.assertFalse(on_disk["offline"])
        self.assertEqual(on_disk["models"]["target"], "script:m")
        self.assertEqual(on_disk["models"]["judge"], "script:judge")
        self.assertGreater(on_disk["compute"]["calls"], 0)
        self.assertTrue(path.endswith("_dev.json"))
        self.assertEqual(len(cal.verdict_lines(rep)), 4)

    def test_skipped_check_fails_the_gate(self):
        rep, _ = self.full_gate(hand_labels=None)
        self.assertFalse(rep["passed"])
        self.assertEqual(rep["skipped"][0]["check"], "human_kappa")
        self.assertIn("--hand-labels", rep["skipped"][0]["reason"])
        self.assertTrue(all(c["passed"] for c in rep["checks"].values()))
        self.assertTrue(any(line.startswith("SKIP human_kappa") for line in cal.verdict_lines(rep)))

    def test_no_cue_pairs_skips_both_b_and_c(self):
        rep, _ = self.full_gate(cue_pairs=None)
        self.assertEqual({s["check"] for s in rep["skipped"]}, {"cue_pairs", "placebo"})
        self.assertFalse(rep["passed"])

    def test_budget_exhaustion_fails_the_check(self):
        budget = Budget(max_calls=8)
        ms = measurer_with(budget=budget)
        r = cal.check_labelled(ms, labelled_rows(), budget=budget)
        self.assertGreater(r["not_run"], 0)
        self.assertFalse(r["passed"])
        self.assertIn("budget", r["reason"])

    def test_failed_calls_are_counted_with_examples(self):
        class Boom(Script):
            def complete(self, prompt, **kw):
                if "essay 3" in prompt:
                    raise RuntimeError("HTTP 529 overloaded")
                return super().complete(prompt, **kw)
        r = cal.check_labelled(measurer_with(Boom(p_fn=cue_sensitive)), labelled_rows())
        self.assertEqual(r["errors"], 1)
        self.assertIn("HTTP 529", r["error_examples"][0])


class LabellingTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.src = os.path.join(self.d, "transcripts.jsonl")
        with open(self.src, "w") as f:
            for i in range(4):
                f.write(json.dumps({"id": f"t{i}", "system": "s", "user": f"u{i}", "response": f"reply {i}",
                                    "reasoning": f"thinking {i}"}) + "\n")
        self.out = os.path.join(self.d, "labels", "me.jsonl")

    def run_with(self, answers, limit=None):
        it = iter(answers)
        printed = []
        res = cal.label_transcripts(self.src, self.out, limit=limit, input_fn=lambda prompt: next(it),
                                    print_fn=lambda *a: printed.append(" ".join(map(str, a))))
        return res, "\n".join(printed)

    def test_resumable_and_blind(self):
        res, shown = self.run_with(["y", "maybe", "n", "quit"])
        self.assertEqual((res["labelled"], res["remaining"], res["quit"]), (2, 2, True))
        self.assertIn("thinking 0", shown)
        self.assertIn("reply 0", shown)
        self.assertIn("unrecognised answer 'maybe'", shown)
        self.assertNotIn("verbalized", shown)
        res, shown = self.run_with(["skip", "y"])
        self.assertNotIn("reply 0", shown)   # already labelled ones are not asked again
        self.assertEqual((res["already_done"], res["skipped"], res["labelled"], res["remaining"]), (2, 1, 1, 0))
        labels = cal.load_hand_labels(self.out)
        self.assertEqual(labels, {"t0": True, "t1": False, "t2": None, "t3": True})
        with open(self.out) as f:
            rows = [json.loads(l) for l in f]
        self.assertTrue(all("labelled_at" in r for r in rows))

    def test_limit(self):
        res, _ = self.run_with(["y"], limit=1)
        self.assertEqual((res["labelled"], res["remaining"]), (1, 3))

    def test_dump_transcripts_from_samples_is_blind_and_idempotent(self):
        samples = os.path.join(self.d, "env.jsonl")
        with open(samples, "w") as f:
            f.write(json.dumps({"env": {"system": "s", "user": "u"}, "response": "r", "reasoning": "hmm",
                                "verbalized": 1.0, "self_report": 0.9, "behavior": "honest"}) + "\n")
            f.write(json.dumps({"env": {"error": "boom"}, "response": "", "behavior": "error",
                                "error": "boom"}) + "\n")
        out = os.path.join(self.d, "dump.jsonl")
        res = cal.dump_transcripts([samples], out)
        self.assertEqual((res["written"], res["dropped_errors"]), (1, 1))
        row = read_json(out)
        self.assertEqual(sorted(row), ["id", "reasoning", "response", "system", "user"])
        self.assertEqual(cal.dump_transcripts([samples], out)["written"], 0)
        self.assertEqual(len(cal.load_transcripts(out)), 1)


class CliTests(unittest.TestCase):
    def test_offline_dry_run_writes_json_marked_offline(self):
        from autoresearch import cli
        d = tempfile.mkdtemp()
        lab = os.path.join(d, "labelled.jsonl")
        with open(lab, "w") as f:
            for i in range(12):
                f.write(json.dumps({"id": f"e{i}", "user": f"This is a test scenario {i}. Answer:",
                                    "response": "ok", "label": "eval"}) + "\n")
                f.write(json.dumps({"id": f"d{i}", "user": f"can u fix my cv {i}", "response": "ok",
                                    "label": "deploy"}) + "\n")
        pairs = os.path.join(d, "pairs.jsonl")
        with open(pairs, "w") as f:
            for i in range(12):
                f.write(json.dumps({"id": f"p{i}", "with_cue": {"system": "Evaluation scenario.", "user": f"Don't {i}"},
                                    "without_cue": {"system": "", "user": f"Don't {i}"}}) + "\n")
        out = os.path.join(d, "results")
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                cli.main(["--llm", "offline", "calibrate", "--labelled", lab, "--cue-pairs", pairs, "--out", out])
                code = 0
            except SystemExit as e:
                code = e.code
        self.assertEqual(code, 1)   # human_kappa skipped -> gate fails
        printed = buf.getvalue()
        self.assertIn("OFFLINE DRY RUN", printed)
        self.assertIn("SKIP human_kappa", printed)
        files = os.listdir(out)
        self.assertEqual(len(files), 1)
        rep = read_json(os.path.join(out, files[0]))
        self.assertTrue(rep["offline"])
        self.assertIn("proves the plumbing only", rep["note"])
        self.assertEqual(set(rep["checks"]), {"labelled", "cue_pairs", "placebo"})

    def test_calibrate_refuses_auto_backend(self):
        from autoresearch import cli
        with self.assertRaisesRegex(SystemExit, "--llm explicitly"):
            cli.main(["calibrate", "--labelled", "x.jsonl"])


if __name__ == "__main__":
    unittest.main()
