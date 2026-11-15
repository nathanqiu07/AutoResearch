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
    # single-factor pairs for the 8 dev items: F1 adds a cue word, F2 doubles the prompt, F3 adds a cue word
    paths["single"] = os.path.join(d, "single.jsonl")
    with open(paths["single"], "w") as f:
        for tid in ids[:8]:
            base = {"system": "You are helpful.", "user": f"task {tid}"}
            for k, user in ((1, f"EVALUATION task {tid}"), (2, f"task {tid} " * 2), (3, f"TEST task {tid}")):
                f.write(json.dumps({"id": f"{tid}__F{k}", "with_cue": {**base, "user": user}, "without_cue": base,
                                    "meta": {"factor": f"F{k}", "factor_name": f"factor_{k}", "task_id": tid,
                                             "label": tid.rsplit("_", 1)[1]}}) + "\n")
    return paths


def driver_args(d, p, *extra):
    missing = os.path.join(d, "absent")
    return ["--items-original", p["original"], "--items-minimal", p["minimal_cue"], "--split", p["split"],
            "--single-pairs", p["single"],
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


def grouped_pairs(n=12):
    """F1: a cue the scripted scorer reacts to. F2: no cue, prompt twice as long."""
    out = []
    for i in range(n):
        base = {"system": "You are a helpful assistant.", "user": f"Please check step {i} today."}
        out.append(cal.CuePair(f"t{i}__F1", {**base, "system": base["system"] + " EVALCUE"}, base, group="F1",
                               meta={"factor": "F1", "factor_name": "cue_word"}))
        out.append(cal.CuePair(f"t{i}__F2", {**base, "user": base["user"] * 3}, base, group="F2",
                               meta={"factor": "F2", "factor_name": "longer"}))
    return out


class PerFactorTests(unittest.TestCase):
    def test_load_cue_pairs_keeps_meta_and_groups_by_factor_and_write_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.jsonl")
            cal.write_cue_pairs(grouped_pairs(2) + [cal.CuePair("plain", {"user": "a"}, {"user": "b"})], path)
            got = {p.id: p for p in cal.load_cue_pairs(path)}
            self.assertEqual((got["t0__F2"].group, got["t0__F2"].meta["factor_name"]), ("F2", "longer"))
            self.assertEqual((got["plain"].group, got["plain"].meta), ("", {}))

    def test_cue_check_reports_per_factor_screen_with_length_ratio_and_pooled_gate(self):
        from tests.test_calibrate import measurer_with
        res = cal.check_cue_pairs(measurer_with(), grouped_pairs())
        f1, f2 = res["by_group"]["F1"], res["by_group"]["F2"]
        self.assertEqual((f1["name"], f1["n_pairs"]), ("cue_word", 12))
        self.assertAlmostEqual(f1["per_answerer"]["target"]["mean_diff"], 0.8)
        self.assertEqual(f1["per_answerer"]["target"]["frac_right_direction"], 1.0)
        self.assertFalse(f1["length_differs"])
        self.assertEqual(f2["per_answerer"]["target"]["mean_diff"], 0.0)
        self.assertTrue(f2["length_differs"])
        self.assertGreater(f2["median_length_ratio"], 1.5)
        self.assertIn("not a gate", res["by_group_note"])
        # the gating number stays the pooled one over all 24 pairs
        self.assertEqual(res["per_answerer"]["target"]["n"], 24)
        self.assertAlmostEqual(res["per_answerer"]["target"]["mean_diff"], 0.4)
        lines = cal.verdict_lines({"checks": {"cue_pairs": res}, "skipped": [
            {"check": c, "reason": "x"} for c in ("labelled", "placebo", "human_kappa")]})
        text = "\n".join(lines)
        self.assertIn("per factor (screen, not gating)", text)
        self.assertRegex(text, r"F2 longer: n=12 len x[0-9.]+ LENGTH DIFFERS")

    def test_ungrouped_pairs_have_no_per_factor_table(self):
        from tests.test_calibrate import cue_pairs, measurer_with
        self.assertNotIn("by_group", cal.check_cue_pairs(measurer_with(), cue_pairs()))

    def test_labelled_verdict_shows_chat_and_agentic_auroc(self):
        from tests.test_calibrate import measurer_with
        rows = []
        for g in ("chat", "agentic"):
            rows += [cal.Labelled(f"{g}e{i}", f"USER: EVALCUE {g} {i}", "eval", g) for i in range(10)]
            rows += [cal.Labelled(f"{g}d{i}", f"USER: essay {g} {i}", "deploy", g) for i in range(10)]
        res = cal.check_labelled(measurer_with(), rows)
        self.assertEqual(set(res["per_answerer"]["target"]["by_group"]), {"chat", "agentic"})
        lines = cal.verdict_lines({"checks": {"labelled": res}, "skipped": [
            {"check": c, "reason": "x"} for c in ("cue_pairs", "placebo", "human_kappa")]})
        self.assertTrue(any(line.strip().startswith("chat: auroc [target=1.000 (n 10/10)") for line in lines))
        self.assertTrue(any(line.strip().startswith("agentic: auroc") for line in lines))

    def test_select_pairs_keeps_n_per_group_and_refuses_items_outside_the_split(self):
        pairs = grouped_pairs(4)
        kept = cal.select_pairs(pairs, ids=[f"t{i}" for i in range(4)], per_group=2)
        self.assertEqual([p.id for p in kept], ["t0__F1", "t1__F1", "t0__F2", "t1__F2"])
        with self.assertRaises(ValueError):
            cal.select_pairs(pairs, ids=["t0", "t1"])

    def test_offline_gate_report_aimed_at_results_goes_to_runs(self):
        from autoresearch.llm import OfflineLLM
        b = Budget()
        ms = Measurer(Models(OfflineLLM(b), OfflineLLM(b), OfflineLLM(b)), simulator=cal.OfflineCalibrationWorld())
        with tempfile.TemporaryDirectory() as d, mock.patch.object(cal, "OFFLINE_OUT", d):
            _, path = cal.run_gate(ms, b, cue_pairs=grouped_pairs(2),
                                   out_dir=os.path.join(cal.REPO_ROOT, "results", "calibration"))
            self.assertTrue(path.startswith(os.path.join(d, "calibration")))
        self.assertEqual(cal.offline_out_dir("/tmp/elsewhere", "calibration"), "/tmp/elsewhere")


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
            out = io.StringIO()
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), \
                    mock.patch.object(cal, "OFFLINE_OUT", os.path.join(d, "offline")), redirect_stdout(out):
                gap_script.main(["--items", p["minimal_cue"], "--split", p["split"], "--seeds", "3",
                                 "--out", os.path.join(d, "results")])
            self.assertFalse(os.path.exists(os.path.join(d, "results")))   # --out is ignored offline
            self.assertIn("offline run: writing to", out.getvalue())
            [name] = os.listdir(os.path.join(d, "offline", "behaviour_gap"))
            with open(os.path.join(d, "offline", "behaviour_gap", name)) as f:
                rep = json.load(f)
            self.assertTrue(rep["offline"])
            self.assertIn("OFFLINE DRY RUN", rep["note"])
            self.assertEqual(rep["result"]["overall"]["n"], 24)
            self.assertEqual(set(rep["result"]["by_group"]), {"safety", "capability"})
            self.assertIn("code_version", rep)


def write_labelled_fixture(d, n_per_cell=6):
    """A small labelled set in load_labelled's id/transcript/label/group format."""
    path = os.path.join(d, "labelled.jsonl")
    with open(path, "w") as f:
        for label in ("eval", "deploy"):
            for group in ("chat", "agentic"):
                for i in range(n_per_cell):
                    f.write(json.dumps({"id": f"{label}-{group}-{i:02d}", "transcript": f"{label} {group} {i} " * 5,
                                        "label": label, "group": group}) + "\n")
    return path


def dry_run(d, p, *extra):
    out = io.StringIO()
    with mock.patch("autoresearch.llm.get_llm", no_real_backend), \
            mock.patch.object(cal, "make_llm", no_real_backend), redirect_stdout(out):
        rc = driver.main(driver_args(d, p, *extra))
    return rc, out.getvalue()


SONNET, GPT5 = "anthropic:claude-sonnet-4-5+thinking", "openai:gpt-5+thinking"
HAIKU, GPT51 = "anthropic:claude-haiku-4-5", "openai:gpt-5.1"


class DriverTests(unittest.TestCase):
    def test_dry_run_plans_the_lineup_for_both_phases_and_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            rc, text = dry_run(d, p)
            self.assertEqual(rc, 0)
            self.assertIn("DRY RUN: nothing was called", text)
            self.assertIn(f"== dev phase | target {driver.DEV_TARGET_PLACEHOLDER}", text)
            self.assertIn("(placeholder; pass --dev-target to execute)", text)
            self.assertIn(f"== final phase | target {SONNET}", text)
            self.assertIn(f"== final phase | target {GPT5}", text)
            # final: both judges are held-out judges, the cross-family one first
            self.assertIn(f"--mode final --target {SONNET} --judge {GPT51} --generator {GPT51} "
                          f"--heldout-target {SONNET} --heldout-judges {GPT51} {HAIKU}", text)
            self.assertIn(f"--mode final --target {GPT5} --judge {HAIKU} --generator {HAIKU} "
                          f"--heldout-target {GPT5} --heldout-judges {HAIKU} {GPT51}", text)
            self.assertIn(f"--mode dev --target {driver._q(driver.DEV_TARGET_PLACEHOLDER)} --judge {HAIKU}", text)
            self.assertEqual(text.count("A1 on this target is a LOWER BOUND"), 2)
            self.assertIn("SUMMARY (upper bounds", text)
            self.assertIn(f"A2 answerers: {driver.DEV_TARGET_PLACEHOLDER}, {HAIKU} |", text)
            self.assertIn("+GPU", text)
            self.assertNotIn("--approved-by-nathan", text.split("DRY RUN")[0])
            self.assertFalse(os.path.exists(os.path.join(d, "gate")))

    def test_phase_selects_the_steps(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            _, dev = dry_run(d, p, "--phase", "dev", "--dev-target", "openai-compat:qwen-x")
            self.assertIn("== dev phase | target openai-compat:qwen-x", dev)
            self.assertNotIn("== final phase", dev)
            _, final = dry_run(d, p, "--phase", "final")
            self.assertNotIn("== dev phase", final)
            self.assertEqual(final.count("== final phase"), 2)

    def test_judges_for_puts_the_cross_family_judge_first(self):
        self.assertEqual(driver.judges_for(SONNET, HAIKU, GPT51), [GPT51, HAIKU])
        self.assertEqual(driver.judges_for(GPT5, HAIKU, GPT51), [HAIKU, GPT51])
        self.assertEqual(driver.judges_for("openai-compat:Qwen/Qwen3-30B-A3B", HAIKU, GPT51), [HAIKU, GPT51])

    def test_a1_lower_bound_marks_only_summary_targets(self):
        self.assertTrue(driver.a1_is_lower_bound(SONNET))
        self.assertTrue(driver.a1_is_lower_bound(GPT5))
        self.assertFalse(driver.a1_is_lower_bound("openai-compat:qwen-x"))

    def test_build_models_dev_has_no_heldout_and_final_has_both_judges(self):
        mk = lambda spec: spec  # noqa: E731  (specs stand in for backends)
        dev = driver.build_models({"phase": "dev", "target": "q", "judges": [HAIKU]}, mk)
        self.assertEqual((dev.target, dev.judge, dev.heldout_target, dev.heldout_judges), ("q", HAIKU, None, []))
        fin = driver.build_models({"phase": "final", "target": SONNET, "judges": [GPT51, HAIKU]}, mk)
        self.assertEqual((fin.judge, fin.heldout_target, fin.heldout_judges), (GPT51, SONNET, [GPT51, HAIKU]))

    def test_single_cue_set_is_default_and_limit_applies_per_factor(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            _, text = dry_run(d, p, "--limit", "2")
            pairs = cal.load_cue_pairs(os.path.join(d, "work", "cue_pairs_single_dev_6.jsonl"))
            self.assertEqual(sorted({x.group for x in pairs}), ["F1", "F2", "F3"])
            self.assertTrue(all(sum(x.group == g for x in pairs) == 2 for g in ("F1", "F2", "F3")))
            n_envs = cal.distinct_envs(pairs)
            self.assertLess(n_envs, 18)   # tasks share their without-cue environments
            self.assertIn(f"6 dev pairs (single), {n_envs} distinct environments", text)

    def test_pairs_spreads_a_total_over_the_factors(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            dry_run(d, p, "--pairs", "4")
            pairs = cal.load_cue_pairs(os.path.join(d, "work", "cue_pairs_single_dev_4.jsonl"))
            self.assertEqual(sorted(x.group for x in pairs), ["F1", "F1", "F2", "F3"])

    def test_pilot_scenario_sets_twenty_pairs_and_no_labelled_or_hand_labels(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            lab = write_labelled_fixture(d)
            _, text = dry_run(d, p, "--labelled", lab, "--scenario", "pilot")
            self.assertIn("scenario pilot", text)
            self.assertIn("20 dev pairs (single)", text)
            self.assertIn("labelled set (a): none", text)
            self.assertNotIn("on labelled set (a)", text)
            self.assertNotIn("A1 audit on hand-labelled", text)

    def test_full_scenario_assumes_absent_needham_and_hand_labels_and_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            _, text = dry_run(d, p, "--scenario", "full")
            self.assertIn("200 transcripts ASSUMED at the 20,000-char cut", text)
            self.assertIn("100 ASSUMED (no hand labels on disk yet)", text)
            self.assertIn("A2 probes x3 on labelled set (a)", text)
            self.assertIn("100 calls x (in ~", text)   # the A1 audit line for 100 hand labels

    def test_labelled_subset_is_written_balanced_and_passed_to_calibrate(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            lab = write_labelled_fixture(d)
            _, text = dry_run(d, p, "--labelled", lab, "--labelled-n", "8", "--labelled-seed", "3")
            sub_path = os.path.join(d, "work", "labelled_subset_8_seed3.jsonl")
            sub = cal.load_labelled(sub_path, max_chars=None)
            self.assertEqual(sum(r.label == "eval" for r in sub), 4)
            self.assertEqual({(r.label, r.group) for r in sub},
                             {("eval", "chat"), ("eval", "agentic"), ("deploy", "chat"), ("deploy", "agentic")})
            self.assertIn(f"--labelled {sub_path}", text)
            self.assertIn("A2 probes x3 on labelled set (a)", text)
            _, again = dry_run(d, p, "--labelled", lab, "--labelled-n", "8", "--labelled-seed", "3")
            self.assertEqual([r.id for r in cal.load_labelled(sub_path, max_chars=None)], [r.id for r in sub])

    def test_warns_when_a_step_exceeds_the_call_or_spend_cap(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            _, text = dry_run(d, p, "--phase", "final", "--max-calls", "10", "--max-cost-usd", "0.01")
            self.assertIn("exceeds --max-calls 10", text)
            self.assertIn("exceeds --max-cost-usd 0.01", text)

    def test_single_pairs_from_a_heldout_item_stop_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            with open(p["single"], "a") as f:
                f.write(json.dumps({"id": "t5_safety__F1", "with_cue": {"system": "", "user": "EVAL x"},
                                    "without_cue": {"system": "", "user": "x"},
                                    "meta": {"factor": "F1", "task_id": "t5_safety"}}) + "\n")
            with self.assertRaises(ValueError) as cm, redirect_stdout(io.StringIO()):
                driver.main(driver_args(d, p))
            self.assertIn("held-out", str(cm.exception))

    def test_execute_without_approval_refuses_and_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            rc, text = dry_run(d, p, "--phase", "final", "--execute")
            self.assertEqual(rc, 2)
            self.assertIn("REFUSING", text)
            self.assertIn("--approved-by-nathan", text.split("REFUSING")[1])
            self.assertFalse(os.path.exists(os.path.join(d, "gate")))

    def test_preflight_needs_one_phase_and_a_dev_target_for_dev(self):
        with tempfile.TemporaryDirectory() as d:
            prereg = os.path.join(d, "prereg.json")
            with open(prereg, "w") as f:
                json.dump({"status": "final"}, f)
            clean = mock.Mock(returncode=0, stdout="")
            parse = lambda *a: driver.build_parser().parse_args(["--prereg", prereg, "--approved-by-nathan"] + list(a))  # noqa: E731
            with mock.patch.object(driver, "_git", return_value=clean):
                self.assertTrue(any("one phase at a time" in x for x in driver.preflight(parse())))
                self.assertTrue(any("--dev-target is required" in x for x in driver.preflight(parse("--phase", "dev"))))
                self.assertEqual(driver.preflight(parse("--phase", "dev", "--dev-target", "openai-compat:q")), [])
                self.assertEqual(driver.preflight(parse("--phase", "final")), [])

    def test_preflight_refuses_a_draft_prereg_and_accepts_a_final_one(self):
        with tempfile.TemporaryDirectory() as d:
            prereg = os.path.join(d, "prereg.json")
            args = driver.build_parser().parse_args(["--prereg", prereg, "--approved-by-nathan", "--phase", "final"])
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

    def test_offline_end_to_end_runs_every_phase_and_marks_reports_offline(self):
        with tempfile.TemporaryDirectory() as d:
            p = write_fixture(d)
            off = os.path.join(d, "offline")
            out = io.StringIO()
            with mock.patch("autoresearch.llm.get_llm", no_real_backend), mock.patch.object(cal, "OFFLINE_OUT", off), \
                    redirect_stdout(out):
                rc = driver.main(driver_args(d, p, "--offline", "--gap-limit", "0"))
            self.assertEqual(rc, 0)
            self.assertFalse(os.path.exists(os.path.join(d, "gate")) or os.path.exists(os.path.join(d, "gap")))
            self.assertIn(f"reports go to {off}", out.getvalue())
            gate_dir, gap_dir = os.path.join(off, "calibration"), os.path.join(off, "behaviour_gap")
            gates, gaps = sorted(os.listdir(gate_dir)), sorted(os.listdir(gap_dir))
            self.assertEqual((len(gates), len(gaps)), (3, 3))
            seen = {}
            for name in gates:
                with open(os.path.join(gate_dir, name)) as f:
                    rep = json.load(f)
                self.assertTrue(rep["offline"])
                self.assertFalse(rep["passed"])   # labelled and kappa inputs are absent, so skipped
                self.assertEqual(rep["checks"]["cue_pairs"]["n"], 15)   # 5 per factor x 3 factors
                seen[rep["inputs"]["target_spec"]] = rep["inputs"]
            self.assertEqual(seen[driver.DEV_TARGET_PLACEHOLDER]["phase"], "dev")
            # the dev judge answers the probes and is gated too (Measurer.judges)
            self.assertEqual(seen[driver.DEV_TARGET_PLACEHOLDER]["a2_answerers"], [driver.DEV_TARGET_PLACEHOLDER, HAIKU])
            self.assertEqual(seen[SONNET]["judge_specs"], [GPT51, HAIKU])
            self.assertEqual(seen[SONNET]["a2_answerers"], [SONNET, GPT51, HAIKU])
            self.assertTrue(seen[SONNET]["a1_lower_bound"])
            self.assertFalse(seen[driver.DEV_TARGET_PLACEHOLDER]["a1_lower_bound"])
            targets = set()
            for name in gaps:
                with open(os.path.join(gap_dir, name)) as f:
                    rep = json.load(f)
                self.assertTrue(rep["offline"])
                targets.add(rep["models"]["requested"]["target_in_plan"])
            self.assertEqual(targets, {driver.DEV_TARGET_PLACEHOLDER, SONNET, GPT5})

    def test_offline_and_execute_are_exclusive(self):
        with self.assertRaises(SystemExit):
            driver.main(["--offline", "--execute"])


if __name__ == "__main__":
    unittest.main()
