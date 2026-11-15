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
    # the dev judge is an answerer the gate checks too, so the default one discriminates like the target
    j = judge or Script(model="judge", p_fn=cue_sensitive, budget=budget)
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

    def test_dev_mode_checks_the_dev_judge_too(self):
        r = cal.check_labelled(measurer_with(judge=Script(model="flat-judge", p_fn=lambda p: 0.3)), labelled_rows())
        self.assertEqual(sorted(r["per_answerer"]), ["script:flat-judge#0", "target"])
        self.assertTrue(r["per_answerer"]["target"]["passed"])
        self.assertFalse(r["per_answerer"]["script:flat-judge#0"]["passed"])
        self.assertFalse(r["passed"])

    def test_dev_judge_off_leaves_the_target_alone(self):
        b = Budget()
        t, j = Script(p_fn=cue_sensitive, budget=b), Script(model="j", budget=b)
        ms = Measurer(Models(generator=j, target=t, judge=j), mode="dev", dev_judge_p_eval=False)
        self.assertEqual([w for w, _ in cal.answerers(ms)], ["target"])

    def test_a_judge_that_is_the_target_reuses_its_answer(self):
        b = Budget()
        t = Script(p_fn=cue_sensitive, budget=b)
        ms = Measurer(Models(generator=t, target=t, judge=t), mode="dev")
        p = cal.p_eval_all(ms, "USER: EVALCUE x")
        self.assertEqual(p["target"], p[f"{t.label}#0"])
        self.assertEqual(b.calls, 3)   # 3 default questions, asked once

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
        per_env = 1 + 3 + 3   # target reply + 3 default probe questions for the target and for the dev judge
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


class ModelLabelTests(unittest.TestCase):
    def test_used_in_this_mode_names_families_headline_and_lower_bound(self):
        b = Budget()
        t = Script(model="claude-sonnet-4-5+thinking", budget=b)
        t.name = "anthropic"
        haiku, gpt = Script(model="claude-haiku-4-5", budget=b), Script(model="gpt-5.1", budget=b)
        haiku.name, gpt.name = "anthropic", "openai"
        ms = Measurer(Models(generator=gpt, target=t, judge=gpt, heldout_target=t, heldout_judges=[gpt, haiku]),
                      mode="final")
        used = cal.model_labels(ms)["used_in_this_mode"]
        self.assertEqual(used["families"], {"anthropic:claude-sonnet-4-5+thinking": "anthropic",
                                            "openai:gpt-5.1": "openai", "anthropic:claude-haiku-4-5": "anthropic"})
        self.assertEqual(used["headline_judge"], "openai:gpt-5.1")
        self.assertTrue(used["a1_is_lower_bound"])
        lines = cal.verdict_lines({"checks": {}, "models": {"used_in_this_mode": used},
                                   "skipped": [{"check": c, "reason": "x"} for c in cal.CHECKS]})
        d = lines.index("SKIP human_kappa: x (a skipped check fails the gate)")
        self.assertIn("headline (cross-family) judge: openai:gpt-5.1", lines[d + 1])
        self.assertIn("LOWER BOUND", lines[d + 2])

    def test_no_cross_family_judge_is_said_not_hidden(self):
        used = cal.model_labels(measurer_with())["used_in_this_mode"]
        self.assertIsNone(used["headline_judge"])
        lines = cal.verdict_lines({"checks": {}, "models": {"used_in_this_mode": used},
                                   "skipped": [{"check": c, "reason": "x"} for c in cal.CHECKS]})
        self.assertTrue(any("NONE: every judge shares the target family" in x for x in lines))


class GateTests(unittest.TestCase):
    def full_gate(self, **kw):
        ts, labels = transcripts_and_labels()
        budget = Budget()
        ms = measurer_with(judge=Script(model="judge", p_fn=cue_sensitive, verbal_fn=reads_reasoning, budget=budget),
                           budget=budget)
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
        self.assertEqual(len(cal.verdict_lines(rep)), 5)   # four checks + the A1 judge note under (d)

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


def _subset_fixture():
    rows = []
    for label, group, count in (("eval", "chat", 30), ("eval", "agentic", 10),
                                ("deploy", "chat", 25), ("deploy", "agentic", 25)):
        for i in range(count):
            rows.append(cal.Labelled(f"{label[0]}-{group}-{i:02d}", f"text {label} {group} {i}", label, group))
    return rows


def _cell_counts(rows):
    counts = {}
    for r in rows:
        counts[(r.label, r.group)] = counts.get((r.label, r.group), 0) + 1
    return counts


class LabelledSubsetTests(unittest.TestCase):
    def test_balanced_and_stratified_by_group(self):
        got = cal.sample_labelled(_subset_fixture(), n=40, seed=1)
        self.assertEqual(_cell_counts(got), {("deploy", "agentic"): 10, ("deploy", "chat"): 10,
                                             ("eval", "agentic"): 10, ("eval", "chat"): 10})

    def test_shortfall_goes_to_other_group_of_same_label(self):
        got = cal.sample_labelled(_subset_fixture(), n=60, seed=1)
        self.assertEqual(_cell_counts(got), {("deploy", "agentic"): 15, ("deploy", "chat"): 15,
                                             ("eval", "agentic"): 10, ("eval", "chat"): 20})

    def test_deterministic_for_same_seed_and_different_for_other_seed(self):
        rows = _subset_fixture()
        a = [r.id for r in cal.sample_labelled(rows, n=40, seed=3)]
        self.assertEqual(a, [r.id for r in cal.sample_labelled(rows, n=40, seed=3)])
        self.assertNotEqual(a, [r.id for r in cal.sample_labelled(rows, n=40, seed=4)])

    def test_input_order_does_not_matter(self):
        import random
        rows = _subset_fixture()
        shuffled = list(rows)
        random.Random(99).shuffle(shuffled)
        self.assertEqual([r.id for r in cal.sample_labelled(rows, n=40, seed=5)],
                         [r.id for r in cal.sample_labelled(shuffled, n=40, seed=5)])

    def test_result_sorted_by_label_group_id(self):
        got = cal.sample_labelled(_subset_fixture(), n=40, seed=2)
        keys = [(r.label, r.group, r.id) for r in got]
        self.assertEqual(keys, sorted(keys))

    def test_too_few_rows_in_a_label_raises_naming_label(self):
        rows = [r for r in _subset_fixture() if r.label != "eval" or r.id.endswith(("00", "01", "02"))]
        with self.assertRaisesRegex(ValueError, "eval.*has 6.*20"):
            cal.sample_labelled(rows, n=40)

    def test_odd_or_zero_n_raises(self):
        for bad in (0, 7, -2):
            with self.assertRaises(ValueError):
                cal.sample_labelled(_subset_fixture(), n=bad)

    def test_write_then_load_round_trips(self):
        rows = cal.sample_labelled(_subset_fixture(), n=20, seed=0)
        path = os.path.join(tempfile.mkdtemp(), "nested", "sub.jsonl")
        cal.write_labelled(rows, path)
        back = cal.load_labelled(path, max_chars=None)
        self.assertEqual([(r.id, r.transcript, r.label, r.group) for r in back],
                         [(r.id, r.transcript, r.label, r.group) for r in rows])

    def test_labelled_subset_path_format(self):
        self.assertEqual(cal.labelled_subset_path("w", 200, 7),
                         os.path.join("w", "labelled_subset_200_seed7.jsonl"))


def _pair(pid, group, user, base="base"):
    return cal.CuePair(pid, {"system": "", "user": user}, {"system": "", "user": base}, group=group)


class PairSpreadTests(unittest.TestCase):
    def test_twenty_over_eight_factors_is_three_or_two_each(self):
        pairs = [_pair(f"t{i:02d}__F{k}", f"F{k}", f"cue{k} {i}", f"base {i}") for k in range(1, 9) for i in range(30)]
        got = cal.spread_pairs(pairs, 20)
        counts = sorted((sum(p.group == f"F{k}" for p in got) for k in range(1, 9)), reverse=True)
        self.assertEqual(counts, [3, 3, 3, 3, 2, 2, 2, 2])
        self.assertEqual([p.id for p in got], [p.id for p in cal.spread_pairs(list(reversed(pairs)), 20)])

    def test_more_than_available_or_nonpositive_raises(self):
        pairs = [_pair("a__F1", "F1", "x")]
        with self.assertRaises(ValueError):
            cal.spread_pairs(pairs, 2)
        with self.assertRaises(ValueError):
            cal.spread_pairs(pairs, 0)

    def test_distinct_env_list_dedupes_shared_without_cue(self):
        pairs = [_pair("t__F1", "F1", "EVAL a"), _pair("t__F2", "F2", "TEST a")]   # both share "base"
        envs = cal.distinct_env_list(pairs)
        self.assertEqual(len(envs), cal.distinct_envs(pairs))
        self.assertEqual(sum(e["user"] == "base" for e in envs), 1)


class EstimateCostTests(unittest.TestCase):
    PRICES = {"m": (1.0, 10.0), "j": (2.0, 4.0)}
    PROBES = {"default": ["Q {transcript}"]}   # 2 template chars around the transcript

    def test_target_reply_and_probe_arithmetic(self):
        env = {"system": "ab", "user": "cdef"}   # 6 chars
        lines = cal.estimate_cost("anthropic:m", ["anthropic:m"], "anthropic:j", [env], self.PROBES, prices=self.PRICES)
        reply, probe = lines
        self.assertEqual((reply.calls, reply.in_tokens, reply.out_tokens), (1, 2, 1200))   # ceil(6/4) = 2
        self.assertAlmostEqual(reply.usd, 2 / 1e6 * 1 + 1200 / 1e6 * 10)
        # probe input: 2 template chars + (6 env + 50 headers + 1200 * 4 reply) = 4858 chars -> 1215 tokens
        self.assertEqual((probe.calls, probe.in_tokens, probe.out_tokens), (1, 1215, 300))
        self.assertAlmostEqual(probe.usd, 1215 / 1e6 * 1 + 300 / 1e6 * 10)
        self.assertIn("= $", probe.how)

    def test_thinking_headroom_only_for_anthropic_and_openai(self):
        env = {"system": "", "user": "x"}
        a = cal.estimate_cost("anthropic:m+thinking", [], "anthropic:j", [env], self.PROBES, prices=self.PRICES)[0]
        o = cal.estimate_cost("openai:m+thinking", [], "anthropic:j", [env], self.PROBES, prices=self.PRICES)[0]
        q = cal.estimate_cost("openai-compat:m+thinking", [], "anthropic:j", [env], self.PROBES, prices=self.PRICES)[0]
        self.assertEqual(a.out_tokens, 1200 + 8000)
        self.assertEqual(o.out_tokens, 1200 + 8000)
        self.assertEqual(q.out_tokens, 1200)
        self.assertIsNone(q.usd)   # GPU time: no per-token price
        self.assertIn("$ unknown", q.how)

    def test_each_answerer_uses_its_own_probe_set(self):
        probes = {"default": ["A {transcript}", "B {transcript}"], "anthropic:j": ["C {transcript}"]}
        lines = cal.estimate_cost("anthropic:m", ["anthropic:m", "anthropic:j"], "anthropic:j",
                                  [{"system": "", "user": "x"}] * 3, probes, prices=self.PRICES)
        self.assertEqual([(x.model, x.calls) for x in lines[1:]], [("anthropic:m", 6), ("anthropic:j", 3)])

    def test_labelled_hand_and_gap_lines(self):
        lines = cal.estimate_cost("anthropic:m", ["anthropic:m"], "anthropic:j", [], self.PROBES,
                                  labelled_chars=[400, 800], hand_chars=[1000] * 3,
                                  gap_envs=[{"system": "", "user": "y" * 8}] * 5, gap_seeds=2, prices=self.PRICES)
        by = {x.step: x for x in lines}
        lab = by["A2 probes x1 on labelled set (a)"]
        self.assertEqual((lab.calls, lab.in_tokens), (2, (2 * 2 + 1200 + 3) // 4))   # ceil(1204 / 4) = 301
        aud = by["A1 audit on hand-labelled transcripts (d)"]
        self.assertEqual((aud.model, aud.calls, aud.in_tokens, aud.out_tokens),
                         ("anthropic:j", 3, (3 * cal.AUDIT_PROMPT_CHARS + 3000) // 4, 900))
        self.assertEqual(by["V3 target replies (as-is + notice)"].calls, 2 * 5 * 2)
        lab_v3 = by["V3 behaviour labels"]
        self.assertEqual((lab_v3.model, lab_v3.calls, lab_v3.out_tokens), ("anthropic:j", 20, 20 * 60))

    def test_model_price_strips_thinking_and_unknown_is_none(self):
        self.assertEqual(cal.model_price("anthropic:m+thinking", self.PRICES), (1.0, 10.0))
        self.assertIsNone(cal.model_price("anthropic:nope", self.PRICES))
        self.assertIsNone(cal.model_price("openai-compat:m", self.PRICES))
        line = cal.estimate_cost("anthropic:nope", [], "anthropic:j", [{"system": "", "user": "x"}],
                                 self.PROBES, prices=self.PRICES)[0]
        self.assertIsNone(line.usd)

    def test_lineup_prices_come_from_llm_table(self):
        self.assertEqual(cal.model_price("anthropic:claude-haiku-4-5"), (1, 5))
        self.assertEqual(cal.model_price("anthropic:claude-sonnet-4-5+thinking"), (3, 15))
        self.assertEqual(cal.model_price("openai:gpt-5.1"), (1.25, 10))

    def test_sample_calls_formula(self):
        # Orchestrator's examples: dev, 3 questions each, corpus -> 10; final with 2 judges -> 14
        self.assertEqual(cal.sample_calls(3, [3]), 10)
        self.assertEqual(cal.sample_calls(3, [3, 3]), 14)
        self.assertEqual(cal.sample_calls(5, [3, 5]), 18)                      # our final lineup
        self.assertEqual(cal.sample_calls(3, [], generated=False, corpus=False), 5)
        self.assertEqual(cal.sample_calls(3, [0], faithfulness=True), 8)      # judge is the target: no extra probes

    def test_assumptions_name_the_unknowns(self):
        text = " ".join(cal.cost_assumptions())
        for needle in ("characters per token", "unverified", "GPU time", "max_tokens"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
