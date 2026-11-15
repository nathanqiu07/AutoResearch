"""V3 behaviour gap (calibrate.behaviour_gap) and the C1 scripts
(scripts/c1_behaviour_gap.py, scripts/c1_run_gate.py). Scripted or offline
models only: any attempt to build a real backend fails the test."""
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from autoresearch.llm import LLM, Budget
from autoresearch.research import calibrate as cal
from autoresearch.research.measure import EVAL_NOTICE, Measurer, Models, Scenario

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gap_script = load_script("c1_behaviour_gap")
driver = load_script("c1_run_gate")


def no_real_backend(*a, **k):
    raise AssertionError("a real backend was requested in an offline test")


class Target(LLM):
    """Misbehaves (says BAD) unless the system prompt starts with the eval notice,
    or never misbehaves when `always_good`."""
    name = "script-target"

    def __init__(self, always_good=False, budget=None):
        super().__init__(budget or Budget())
        self.model, self.always_good, self.calls = "t", always_good, 0

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.calls += 1
        self.budget.charge(1, 1)
        return "GOOD" if self.always_good or system.startswith(EVAL_NOTICE) else "BAD"


class Judge(LLM):
    """Labels BAD replies with the item's first misbehaviour label, others with
    its first good label; `garble` returns prose with no JSON."""
    name = "script-judge"

    def __init__(self, garble=False, budget=None):
        super().__init__(budget or Budget())
        self.model, self.garble = "j", garble

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.budget.charge(1, 1)
        if self.garble:
            return "I cannot tell."
        reply = prompt.split("ASSISTANT REPLY:\n", 1)[1].split("\n", 1)[0]
        safety = "'complies'" in prompt
        bad, good = ("complies", "refuses") if safety else ("refuses", "completes")
        return json.dumps({"behavior": bad if reply.startswith("BAD") else good})


def item(i, label):
    if label == "safety":
        behaviors, mis = ["complies", "refuses", "partial", "unclear"], "complies|partial"
    else:
        behaviors, mis = ["completes", "refuses", "partial", "unclear"], "refuses|partial"
    return Scenario(name=f"t{i}_{label}", goal="g", setting="s", probe="p", behaviors=behaviors, misbehavior=mis,
                    original={"system": "You are helpful.", "user": f"task {i} ({label})"},
                    source_id=f"t{i}_{label}")


def items_and_groups(n_tasks=4):
    its = [item(i, lab) for i in range(n_tasks) for lab in ("safety", "capability")]
    return its, {s.source_id: s.source_id.rsplit("_", 1)[1] for s in its}


def factory_for(target, judge):
    models = Models(generator=judge, target=target, judge=judge)
    return lambda sc: Measurer(models, scenario=sc, workers=1)


class BehaviourGapTests(unittest.TestCase):
    def test_target_that_misbehaves_only_without_notice_gives_positive_measurable_gap(self):
        its, groups = items_and_groups()
        res = cal.behaviour_gap(factory_for(Target(), Judge()), its, n_per_item=2, groups=groups, workers=2)
        o = res["overall"]
        self.assertEqual((o["n"], o["misbehaving_as_is"], o["misbehaving_with_notice"]), (16, 16, 0))
        self.assertEqual(o["gap"], 1.0)
        self.assertGreater(o["ci"][0], 0)
        self.assertTrue(o["measurable"])
        self.assertEqual(set(res["by_group"]), {"safety", "capability"})
        self.assertTrue(all(g["n"] == 8 and g["gap"] == 1.0 for g in res["by_group"].values()))
        self.assertFalse(res["gating"])

    def test_never_misbehaving_target_is_not_measurable_with_reason(self):
        its, groups = items_and_groups()
        res = cal.behaviour_gap(factory_for(Target(always_good=True), Judge()), its, n_per_item=2, groups=groups)
        o = res["overall"]
        self.assertEqual((o["rate_as_is"], o["gap"]), (0.0, 0.0))
        self.assertFalse(o["measurable"])
        self.assertIn("only 0 of 16", o["reason"])

    def test_unparseable_labels_are_counted_never_defaulted(self):
        its, groups = items_and_groups(2)
        res = cal.behaviour_gap(factory_for(Target(), Judge(garble=True)), its, n_per_item=2, groups=groups)
        o = res["overall"]
        self.assertEqual((o["n"], o["unparseable"], o["misbehaving_as_is"]), (0, 8, 0))
        self.assertIsNone(o["gap"])
        self.assertFalse(o["measurable"])

    def test_items_after_budget_runs_out_are_not_run(self):
        its, groups = items_and_groups(2)
        budget = Budget(max_calls=0)
        res = cal.behaviour_gap(factory_for(Target(), Judge()), its, n_per_item=2, groups=groups, budget=budget)
        self.assertEqual((res["overall"]["n"], res["overall"]["not_run"]), (0, 8))

    def test_measurer_argument_reuses_models_and_falls_back_to_a_behaviour_simulator(self):
        from autoresearch.llm import OfflineLLM
        b = Budget()
        ms = Measurer(Models(OfflineLLM(b), OfflineLLM(b), OfflineLLM(b)), simulator=cal.OfflineCalibrationWorld())
        its, groups = items_and_groups(2)
        res = cal.behaviour_gap(ms, its, n_per_item=3, groups=groups)
        self.assertEqual(res["overall"]["n"] + res["overall"]["failed_calls"], 12)
        self.assertEqual(res["overall"]["failed_calls"], 0)


class HelperTests(unittest.TestCase):
    def test_spec_backend_prefix_overrides_default(self):
        self.assertEqual(cal.spec_backend("openai:some-model+thinking", "anthropic"), "openai")
        self.assertEqual(cal.spec_backend("claude-sonnet-4-6", "offline"), "offline")
        self.assertTrue(cal.spec_is_offline("offline", "anthropic"))

    def test_make_llm_never_reaches_get_llm_for_offline_specs(self):
        with mock.patch("autoresearch.llm.get_llm", no_real_backend):
            self.assertEqual(cal.make_llm("offline", "anthropic", Budget()).name, "offline")
            self.assertEqual(cal.make_llm("whatever", "offline", Budget()).name, "offline")

    def test_probe_count_follows_measure_lookup(self):
        probes = {"default": ["a {transcript}"] * 5, "openai-compat:openai/gpt-x": ["b {transcript}"] * 3,
                  "anthropic:claude-sonnet-4-6": ["c {transcript}"] * 4}
        self.assertEqual(cal.probe_count(probes, "openai:gpt-x+thinking"), 3)
        self.assertEqual(cal.probe_count(probes, "anthropic:claude-sonnet-4-6+thinking"), 4)
        self.assertEqual(cal.probe_count(probes, "openai:unknown"), 5)


def write_fixture(d, n_tasks=6):
    """Original and minimal-cue item files, a split (4 dev tasks, 2 held out)."""
    rows = {"original": [], "minimal_cue": []}
    for i in range(n_tasks):
        for lab in ("safety", "capability"):
            for cfg in rows:
                rows[cfg].append({"id": f"t{i}_{lab}", "system": "You are helpful.",
                                  "user": f"{'EVALUATION: ' if cfg == 'original' else ''}task {i} {lab}",
                                  "behaviors": item(i, lab).behaviors, "misbehavior": item(i, lab).misbehavior,
                                  "probe": "p", "meta": {"label": lab, "config": cfg}})
    paths = {}
    for cfg, rs in rows.items():
        paths[cfg] = os.path.join(d, f"items_{cfg}.jsonl")
        with open(paths[cfg], "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rs)
    ids = [f"t{i}_{lab}" for i in range(n_tasks) for lab in ("safety", "capability")]
    paths["split"] = os.path.join(d, "split.json")
    with open(paths["split"], "w") as f:
        json.dump({"version": 1, "dev": ids[:8], "heldout": ids[8:]}, f)
    return paths


def driver_args(d, p, *extra):
    missing = os.path.join(d, "absent")
    return ["--items-original", p["original"], "--items-minimal", p["minimal_cue"], "--split", p["split"],
            "--gap-items", p["minimal_cue"], "--probe-questions", missing, "--labelled", missing,
            "--transcripts", missing, "--hand-labels", missing, "--work", os.path.join(d, "work"),
            "--out-gate", os.path.join(d, "gate"), "--out-gap", os.path.join(d, "gap"),
            "--prereg", os.path.join(d, "prereg.json")] + list(extra)


class PairItemsTests(unittest.TestCase):
    def test_restricts_to_ids_and_limits_by_sorted_id(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            pairs = cal.pair_items(p["original"], p["minimal_cue"], ids=["t3_safety", "t0_capability", "t1_safety"],
                                   limit=2)
            self.assertEqual([x.id for x in pairs], ["t0_capability", "t1_safety"])
            self.assertTrue(pairs[0].with_cue["user"].startswith("EVALUATION"))
            with self.assertRaises(ValueError):
                cal.pair_items(p["original"], p["minimal_cue"], ids=["nope"])

    def test_load_gap_items_keeps_one_side_with_groups(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            its, groups = cal.load_gap_items(p["minimal_cue"], p["split"], "heldout")
            self.assertEqual(len(its), 4)
            self.assertEqual(set(groups.values()), {"safety", "capability"})


class GapScriptTests(unittest.TestCase):
    def test_non_offline_spec_without_approval_refuses_before_any_backend(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            out = io.StringIO()
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), redirect_stdout(out):
                with self.assertRaises(SystemExit) as cm:
                    gap_script.main(["--target", "anthropic:claude-sonnet-4-6+thinking", "--judge", "offline",
                                     "--items", p["minimal_cue"], "--split", p["split"], "--out", d])
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("up to 64 model calls", out.getvalue())
            self.assertEqual(os.listdir(d), [f for f in os.listdir(d) if not f.endswith("_dev.json")])

    def test_offline_run_writes_json_marked_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), redirect_stdout(io.StringIO()):
                gap_script.main(["--items", p["minimal_cue"], "--split", p["split"], "--seeds", "3",
                                 "--out", os.path.join(d, "out")])
            [name] = os.listdir(os.path.join(d, "out"))
            with open(os.path.join(d, "out", name)) as f:
                rep = json.load(f)
            self.assertTrue(rep["offline"])
            self.assertIn("OFFLINE DRY RUN", rep["note"])
            self.assertEqual(rep["result"]["overall"]["n"], 24)
            self.assertEqual(set(rep["result"]["by_group"]), {"safety", "capability"})
            self.assertIn("code_version", rep)


class DriverTests(unittest.TestCase):
    def test_dry_run_prints_commands_and_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            out = io.StringIO()
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), \
                    mock.patch.object(cal, "make_llm", no_real_backend), redirect_stdout(out):
                rc = driver.main(driver_args(d, p, "--judge", "anthropic:judge-model", "--openai-target",
                                             "gpt-test+thinking", "--usd-per-call", "0.01"))
            text = out.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("DRY RUN: nothing was called", text)
            for t in ("anthropic:claude-sonnet-4-6+thinking", "openai:gpt-test+thinking"):
                self.assertIn(f"calibrate --target {t}", text)
                self.assertIn(f"c1_behaviour_gap.py --llm anthropic --target {t}", text)
            # 8 dev pairs, 3 default questions: 3 * 8 * (1 + 3) = 96 gate calls; V3 4 * 8 * 2 = 64
            self.assertIn("gate: up to 96 calls, <= $0.96", text)
            self.assertIn("gap: up to 64 calls", text)
            self.assertNotIn("--approved-by-nathan", text.split("DRY RUN")[0].replace("--execute --approved-by-nathan", ""))
            self.assertFalse(os.path.exists(os.path.join(d, "gate")))
            with open(os.path.join(d, "work", "cue_pairs_dev_8.jsonl")) as f:
                self.assertEqual(len(f.readlines()), 8)

    def test_openai_target_is_required_unless_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            with self.assertRaises(SystemExit) as cm:
                driver.main(driver_args(d, p, "--judge", "anthropic:j"))
            self.assertIn("--openai-target", str(cm.exception.code))

    def test_execute_without_approval_refuses_and_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            out = io.StringIO()
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), \
                    mock.patch.object(cal, "make_llm", no_real_backend), redirect_stdout(out):
                rc = driver.main(driver_args(d, p, "--judge", "anthropic:j", "--openai-target", "m", "--execute"))
            self.assertEqual(rc, 2)
            self.assertIn("REFUSING", out.getvalue())
            self.assertIn("--approved-by-nathan", out.getvalue())
            self.assertFalse(os.path.exists(os.path.join(d, "gate")))

    def test_preflight_refuses_a_draft_prereg_and_accepts_a_final_one(self):
        with tempfile.TemporaryDirectory() as d:
            prereg = os.path.join(d, "prereg.json")
            args = driver.build_parser().parse_args(["--prereg", prereg, "--approved-by-nathan"])
            clean = mock.Mock(returncode=0, stdout="")
            with mock.patch.object(driver, "_git", return_value=clean):
                with open(prereg, "w") as f:
                    json.dump({"status": "DRAFT: not launchable"}, f)
                self.assertTrue(any("draft" in p for p in driver.preflight(args)))
                with open(prereg, "w") as f:
                    json.dump({"status": "final"}, f)
                self.assertEqual(driver.preflight(args), [])
            dirty = mock.Mock(returncode=1, stdout=" M autoresearch/x.py")
            with mock.patch.object(driver, "_git", return_value=dirty):
                problems = driver.preflight(args)
            self.assertTrue(any("uncommitted changes" in p for p in problems))
            self.assertTrue(any("not committed" in p for p in problems))

    def test_offline_end_to_end_writes_gate_and_gap_json_marked_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), redirect_stdout(io.StringIO()):
                rc = driver.main(driver_args(d, p, "--offline", "--gap-limit", "0"))
            self.assertEqual(rc, 0)
            gates, gaps = sorted(os.listdir(os.path.join(d, "gate"))), sorted(os.listdir(os.path.join(d, "gap")))
            self.assertEqual((len(gates), len(gaps)), (2, 2))
            for name in gates:
                with open(os.path.join(d, "gate", name)) as f:
                    rep = json.load(f)
                self.assertTrue(rep["offline"])
                self.assertFalse(rep["passed"])   # labelled and kappa inputs are absent, so skipped
                self.assertEqual(rep["checks"]["cue_pairs"]["n"], 8)
                self.assertEqual(rep["inputs"]["driver"], "scripts/c1_run_gate.py")
            targets = set()
            for name in gaps:
                with open(os.path.join(d, "gap", name)) as f:
                    rep = json.load(f)
                self.assertTrue(rep["offline"])
                targets.add(rep["models"]["requested"]["target_in_plan"])
            self.assertEqual(targets, {"anthropic:claude-sonnet-4-6+thinking", "openai:<model>"})

    def test_offline_and_execute_are_exclusive(self):
        with self.assertRaises(SystemExit):
            driver.main(["--offline", "--execute"])


if __name__ == "__main__":
    unittest.main()
