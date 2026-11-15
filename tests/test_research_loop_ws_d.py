"""WS D: decision records, taste advisor, arms, multi-item, agentic wiring, claims."""
import json
import os
import random
import sys
import tempfile
import types
import unittest
from dataclasses import asdict

from autoresearch.llm import LLM, OfflineLLM
from autoresearch.memory import ResearchMemory
from autoresearch.research.advisor import (ProfileUserModel, TasteAdvisor, choice_index, history_text,
                                           load_user_model)
from autoresearch.research.claims import candidate_claims, check_all, check_claim
from autoresearch.research.decisions import DecisionLog, load_decisions, validate_record
from autoresearch.research.ideas import Proposer
from autoresearch.research.loop import (ACCEPT, DEFER, REJECT, OpenResearcher, ResearchConfig, write_report)
from autoresearch.research.measure import Measurer, Models, OfflineWorld, Scenario
from autoresearch.research.multi import ItemPool, paired_compare
from autoresearch.taste import TasteProfile

GOOD = TasteProfile("good", {"realism": 1.0, "validity_care": 1.0, "risk": -1.0})


def offline_models():
    return Models(OfflineLLM(), OfflineLLM(), OfflineLLM())


class Pred:
    def __init__(self, choice, confidence, rationale=""):
        self.choice, self.confidence, self.rationale = choice, confidence, rationale


class ScriptedUserModel:
    """A text user model: picks the option containing `want` (else abstains)."""

    def __init__(self, want="", confidence=0.9):
        self.want, self.confidence, self.calls = want, confidence, 0

    def predict(self, context, options):
        self.calls += 1
        for i, o in enumerate(options):
            if self.want and self.want in o:
                return Pred(i, self.confidence)
        return Pred(None, 0.0)


def researcher(cfg, taste=None, advisor=None, mem=None, proposer=None, measurer=None, pool=None, ddir=None):
    m = measurer if measurer is not None or pool is not None else Measurer(offline_models(), simulator=OfflineWorld())
    pr = proposer or Proposer(OfflineLLM(), taste, random.Random(cfg.seed))
    return OpenResearcher(m, pr, ResearchMemory(mem), taste, cfg, advisor=advisor, pool=pool, decisions_dir=ddir)


class DecisionRecordTests(unittest.TestCase):
    def test_validation_and_jsonl(self):
        d = tempfile.mkdtemp()
        log = DecisionLog("r1", "R1-P", root=d, version="abc")
        log.add(1, "D3", "ctx", ["accept", "reject"], 1, user_model_choice=0, user_model_confidence=0.8,
                evidence={"p_better": 0.7})
        log.add(1, "D2", "ctx", ["6 samples"], 0)
        recs = load_decisions(os.path.join(d, "r1", "decisions.jsonl"))
        self.assertEqual(len(recs), 2)
        self.assertTrue(recs[0]["overrode_taste"])
        self.assertIsNone(recs[1]["user_model_choice"])
        self.assertEqual(recs[0]["code_version"], "abc")
        bad = dict(recs[0], chosen=5)
        self.assertTrue(validate_record(bad))
        self.assertTrue(validate_record(dict(recs[0], overrode_taste=False)))
        self.assertTrue(validate_record(dict(recs[0], point="D9")))
        with self.assertRaises(ValueError):
            log.add(1, "D1", "ctx", ["a"], 3)

    def test_every_point_is_logged_and_valid(self):
        d = tempfile.mkdtemp()
        rep = researcher(ResearchConfig(iterations=6, seed=1), taste=GOOD, ddir=d).run()
        recs = load_decisions(os.path.join(d, rep["run_id"], "decisions.jsonl"))
        points = {r["point"] for r in recs}
        self.assertTrue({"D1", "D2", "D3", "D5", "D6"} <= points, points)
        self.assertTrue(all(r["arm"] == "R1" for r in recs))
        # the feature-weight profile informs D1 and abstains on text decisions
        self.assertTrue(all(r["user_model_choice"] is not None for r in recs if r["point"] == "D1"))
        self.assertTrue(all(r["user_model_choice"] is None for r in recs if r["point"] in ("D2", "D3", "D5")))
        self.assertEqual(len(rep["decisions"]), len(recs))
        out = tempfile.mkdtemp()
        md = open(write_report(rep, out)).read()
        self.assertIn("## Decision points", md)
        self.assertIn("## Claims", md)
        self.assertTrue(os.path.exists(os.path.join(out, f"{rep['scenario']}_{rep['run_id']}_decisions.jsonl")))


class AdvisorTests(unittest.TestCase):
    def test_choice_index(self):
        opts = ["accept", "reject", "defer"]
        self.assertEqual(choice_index(2, opts), 2)
        self.assertEqual(choice_index("1", opts), 1)
        self.assertEqual(choice_index("c", opts), 2)
        self.assertEqual(choice_index("Reject", opts), 1)
        self.assertIsNone(choice_index(7, opts))
        self.assertIsNone(choice_index(True, opts))
        self.assertIsNone(choice_index("something else", opts))

    def test_low_confidence_falls_back_and_decisive_evidence_wins(self):
        adv = TasteAdvisor(ScriptedUserModel("defer", 0.3), min_confidence=0.6)
        self.assertEqual(adv.decide("c", ["accept", "reject", "defer"], 1, decisive=False)[0], 1)
        adv = TasteAdvisor(ScriptedUserModel("defer", 0.9), min_confidence=0.6)
        self.assertEqual(adv.decide("c", ["accept", "reject", "defer"], 1, decisive=False)[0], 2)
        self.assertEqual(adv.decide("c", ["accept", "reject", "defer"], 0, decisive=True)[0], 0)

    def test_d3_policy_never_lets_taste_accept(self):
        cfg = ResearchConfig(iterations=1)
        r = researcher(cfg, advisor=TasteAdvisor(ScriptedUserModel("accept", 1.0)))
        summ = {"validity": 0.9, "ci90": [0, 0.1], "n": 6}
        from autoresearch.research.ideas import LIBRARY
        idea = LIBRARY[0]
        self.assertEqual(r._d3(1, "add:x", idea, 0.8, 0.05, summ, True, None), REJECT)   # inconclusive: no accept
        self.assertEqual(r._d3(1, "add:x", idea, 0.95, 0.1, summ, True, None), ACCEPT)   # decisive
        self.assertEqual(r._d3(1, "add:x", idea, 0.95, 0.1, dict(summ, validity=0.5), True, None), REJECT)
        self.assertEqual(r._d3(1, "add:x", idea, 0.95, 0.1, summ, True, "drifted"), REJECT)
        r = researcher(cfg, advisor=TasteAdvisor(ScriptedUserModel("defer", 1.0)))
        self.assertEqual(r._d3(1, "add:x", idea, 0.8, 0.05, summ, True, None), DEFER)
        self.assertEqual(r._d3(1, "add:x", idea, 0.8, 0.05, summ, True, None), REJECT)   # taste defers once per idea
        self.assertEqual(r._d3(1, "remove:x", LIBRARY[1], 0.8, 0.05, summ, True, None), REJECT)
        self.assertEqual(r._d3(1, "add:x", LIBRARY[2], 0.3, -0.05, summ, True, None), REJECT)  # clearly not better
        recs = [x for x in r.dlog.records if x.point == "D3"]
        self.assertTrue(recs[1].overrode_taste and not recs[0].overrode_taste)

    def test_eager_taste_cannot_relax_the_evidence_bar(self):
        adv = TasteAdvisor(ScriptedUserModel("accept", 1.0))
        rep = researcher(ResearchConfig(iterations=8, seed=3), advisor=adv).run()
        for f in rep["findings"]:
            if f["status"] in ("validated", "unconfirmed"):
                self.assertGreaterEqual(f["p_better"], 0.9)
        for d in rep["decisions"]:
            if d["point"] == "D3" and d["chosen"] == ACCEPT:
                self.assertGreaterEqual(d["evidence"]["p_better"], 0.9)

    def test_abandon_direction_at_d4(self):
        adv = TasteAdvisor(ScriptedUserModel("abandon", 0.9))
        rep = researcher(ResearchConfig(iterations=10, seed=2, abandon_after_mixed=1), advisor=adv).run()
        d4 = [d for d in rep["decisions"] if d["point"] == "D4" and not d["evidence"]["decisive"]]
        self.assertTrue(d4)
        self.assertTrue(rep["abandoned_directions"])
        for cat in rep["abandoned_directions"]:
            it = next(e["iter"] for e in rep["log"] if e.get("event") == "abandoned_direction" and e["category"] == cat)
            later = [f for f in rep["findings"] if f["iter"] > it and f["category"] == cat and f["move"].startswith("add")
                     and f["status"] != "deferred"]
            self.assertEqual(later, [], cat)

    def test_ws_a_usermodel_loads_and_failures_fall_back(self):
        from autoresearch.taste.methods import create_method
        d = tempfile.mkdtemp()
        um = create_method("m1", OfflineLLM())
        um.fit([], [])
        um.save(os.path.join(d, "usermodel.json"))
        model, src = load_user_model(d, None, llm=OfflineLLM())
        self.assertIn("method m1", src)
        adv = TasteAdvisor(model)
        rep = researcher(ResearchConfig(iterations=2), advisor=adv).run()
        self.assertTrue(adv.errors)   # the offline backend returns no JSON, so the model abstains
        self.assertTrue(all(d["user_model_choice"] is None for d in rep["decisions"]))
        with self.assertRaises(ValueError):
            load_user_model(d, None)

    def test_d1_uses_prediction_probabilities(self):
        class Dist:
            def predict(self, context, options):
                p = [0.0] * len(options)
                p[-1] = 0.7
                p[0] += 0.3
                return Pred(chr(ord("a") + len(options) - 1), 0.7, "")
        class WithProbs(Dist):
            def predict(self, context, options):
                pred = super().predict(context, options)
                pred.probabilities = [0.3] + [0.0] * (len(options) - 2) + [0.7]
                return pred
        ps, adv = TasteAdvisor(WithProbs()).d1_scores("c", ["x", "y", "z"], [{}, {}, {}])
        self.assertEqual(ps, [0.3, 0.0, 0.7])
        ps, adv = TasteAdvisor(Dist()).d1_scores("c", ["x", "y", "z"], [{}, {}, {}])
        self.assertEqual(adv.choice, 2)
        self.assertAlmostEqual(ps[0], 0.15)

    def test_profile_adapter_and_loader(self):
        um = ProfileUserModel(GOOD)
        ps = um.predict_features("c", [{"realism": 1}, {"risk": 1}])
        self.assertGreater(ps[0], ps[1])
        self.assertAlmostEqual(sum(ps), 1.0)
        self.assertEqual(um.predict("c", ["a", "b"]).confidence, 0.0)
        d = tempfile.mkdtemp()
        m, src = load_user_model(d, GOOD)
        self.assertIsInstance(m, ProfileUserModel)
        self.assertIn("D1 only", src)
        self.assertEqual(load_user_model(d, None), (None, "none"))
        with open(os.path.join(d, "choices.jsonl"), "w") as f:
            f.write(json.dumps({"a_text": "x", "b_text": "y", "chosen": "a", "context": "pick", "reason": "r"}) + "\n")
        os.makedirs(os.path.join(d, "corpus"))
        open(os.path.join(d, "corpus", "research__0.txt"), "w").write("my paper")
        h = history_text(d)
        self.assertIn("reason: r", h)
        self.assertIn("my paper", h)

    def test_history_text_reads_personal_track_history(self):
        """trackp writes the fitted rows to history.jsonl; the prompt arm must see them,
        and a row also present in choices.jsonl is listed once."""
        d = tempfile.mkdtemp()
        row = {"user_id": "u", "context": "stance", "a_text": "ship now", "b_text": "wait for data",
               "chosen": "b", "decision_point": "D3"}
        with open(os.path.join(d, "history.jsonl"), "w") as f:
            f.write(json.dumps(row) + "\n")
        self.assertIn("wait for data", history_text(d))
        self.assertIn("[D3]", history_text(d))
        with open(os.path.join(d, "choices.jsonl"), "w") as f:
            f.write(json.dumps(row) + "\n")
        self.assertEqual(history_text(d).count("wait for data"), 1)
        self.assertEqual(history_text(tempfile.mkdtemp()), "")
        # public track: the time-split history is read, its held-out file never is
        d2 = tempfile.mkdtemp()
        with open(os.path.join(d2, "history_timesplit.jsonl"), "w") as f:
            f.write(json.dumps(dict(row, a_text="before cutoff")) + "\n")
        with open(os.path.join(d2, "heldout_timesplit.jsonl"), "w") as f:
            f.write(json.dumps(dict(row, a_text="after cutoff")) + "\n")
        self.assertIn("before cutoff", history_text(d2))
        self.assertNotIn("after cutoff", history_text(d2))


class ArmTests(unittest.TestCase):
    def _args(self, *extra):
        from autoresearch.cli import build_parser
        return build_parser().parse_args(["--llm", "offline", "research", *extra])

    def test_arms_differ_only_in_taste_mode(self):
        from autoresearch.cli import research_config, resolve_arm
        variants = [("none",), ("model", "--researcher", "demo_realist"), ("prompt", "--researcher", "demo_realist"),
                    ("model", "--researcher", "demo_contrarian")]
        cfgs, arms = [], []
        for v in variants:
            a = self._args("--taste-mode", v[0], *v[1:])
            slug, arm = resolve_arm(a.taste_mode, a.taste_track, a.researcher, a.arm)
            arms.append(arm)
            cfgs.append(asdict(research_config(a, arm)))
        self.assertEqual(arms, ["R0", "R1-demo_realist", "R1-demo_realist-prompt", "R1-bad"])
        for c in cfgs[1:]:
            diff = {k for k in c if c[k] != cfgs[0][k]}
            self.assertTrue(diff <= {"taste_mode", "arm"}, diff)
        a = self._args("--no-taste")
        self.assertTrue(a.no_taste)

    def test_tracks_resolution(self):
        from autoresearch.cli import resolve_arm
        d = tempfile.mkdtemp()
        with self.assertRaises(SystemExit):
            resolve_arm("model", "P", None, None, root=d)
        json.dump({"P": "alice", "S": "bob"}, open(os.path.join(d, "tracks.json"), "w"))
        self.assertEqual(resolve_arm("model", "P", None, None, root=d), ("alice", "R1-P"))
        self.assertEqual(resolve_arm("prompt", "S", None, None, root=d), ("bob", "R1-S-prompt"))
        with self.assertRaises(SystemExit):
            resolve_arm("model", None, None, None, root=d)

    def test_abstaining_user_model_reproduces_r0(self):
        """With a user model that never commits, R1 must behave exactly like
        R0: the only difference between arms is what taste contributes."""
        def run(mode, adv):
            cfg = ResearchConfig(iterations=6, seed=4, taste_mode=mode)
            return researcher(cfg, advisor=adv).run()
        r0 = run("none", None)
        r1 = run("model", TasteAdvisor(ScriptedUserModel("", 0.0)))
        rp = run("prompt", None)
        key = lambda rep: [(f["move"], f["status"], round(f["delta"], 9)) for f in rep["findings"]]  # noqa: E731
        self.assertEqual(key(r0), key(r1))
        self.assertEqual(key(r0), key(rp))
        self.assertEqual({d["arm"] for d in r0["decisions"]}, {"R0"})
        self.assertTrue(all(d["user_model_choice"] is None for d in r0["decisions"] + rp["decisions"]))

    def test_cli_offline_arms_end_to_end(self):
        from autoresearch.cli import main
        tmp = tempfile.mkdtemp()
        for extra in (["--taste-mode", "none"], ["--researcher", "demo_realist"],
                      ["--researcher", "demo_realist", "--taste-mode", "prompt"],
                      ["--researcher", "demo_contrarian"]):
            main(["--llm", "offline", "research", "--iterations", "2", "--no-web", "--no-shared",
                  "--faithfulness-samples", "0", "--memory", os.path.join(tmp, "mem"), "--out",
                  os.path.join(tmp, "out"), "--decisions-dir", os.path.join(tmp, "runs"), *extra])
        files = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(tmp, "runs")) for f in fs]
        self.assertEqual(len(files), 4)
        arms = {load_decisions(f)[0]["arm"] for f in files}
        self.assertEqual(arms, {"R0", "R1-demo_realist", "R1-demo_realist-prompt", "R1-bad"})


class D1RecordTests(unittest.TestCase):
    def test_measured_design_below_top_six_is_recorded(self):
        from autoresearch.research.ideas import LIBRARY
        r = researcher(ResearchConfig(iterations=1), taste=GOOD)
        designs = [(f"add:{i.id}", [i], i) for i in LIBRARY[:9]]
        um_top = r._d1(1, designs, r._measure([]))
        pri = {d[0]: {"taste": 0.0, "memory": 0.0, "novelty": 0.0, "total": 0.0} for d in designs}
        r._record_d1(1, designs, [designs[8]], pri, designs[um_top])
        rec = r.dlog.records[-1]
        self.assertEqual(rec.options[rec.chosen], f"add [{LIBRARY[8].category}] {LIBRARY[8].text}")
        self.assertIn(rec.chosen, rec.evidence["measured"])


class SettingDriftTests(unittest.TestCase):
    def test_drifted_environment_is_never_accepted(self):
        class Gate(LLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                return json.dumps({"keep": "realistic_identity" not in prompt and "realistic full names" not in prompt,
                                   "why": "turned into a repo"})
        pr = Proposer(OfflineLLM(), None, random.Random(0), gate_llm=Gate())
        rep = researcher(ResearchConfig(iterations=8, seed=0), proposer=pr).run()
        drifted = [f for f in rep["findings"] if f["status"] == "drifted"]
        self.assertTrue(drifted)
        self.assertTrue(rep["setting_drift"])
        self.assertNotIn("realistic_identity", [i["category"] for i in rep["best_design"]])
        self.assertIn("left the fixed setting", open(write_report(rep, tempfile.mkdtemp())).read())


class MultiItemTests(unittest.TestCase):
    def _pool(self, n=6):
        items = [Scenario(name=f"item_{k}", goal="g", setting="s", probe="p", source_id=f"i{k}",
                          original={"system": "", "user": f"task {k}"}) for k in range(n)]
        return ItemPool(items, lambda sc: Measurer(offline_models(), scenario=sc, simulator=OfflineWorld()))

    def test_paired_compare(self):
        p, d, per = paired_compare([1, 1, 0.5, 0.5], ["a", "a", "b", "b"], [0.5, 0.5, 0.2, 0.2], ["a", "a", "b", "b"])
        self.assertAlmostEqual(d, 0.4)
        self.assertEqual(p, 1.0)
        self.assertEqual(set(per), {"a", "b"})

    def test_multi_item_run_reports_per_item_and_pooled(self):
        pool = self._pool()
        cfg = ResearchConfig(iterations=4, samples=2, items_per_iter=3, faithfulness_samples=6)
        rep = researcher(cfg, taste=GOOD, pool=pool).run()
        mi = rep["multi_item"]
        self.assertEqual(len(mi["per_item"]), 3)
        self.assertEqual(mi["pool_size"], 6)
        self.assertTrue(all("per_item_delta" in f for f in rep["findings"]))
        self.assertTrue(all(len(f["per_item_delta"]) == 3 for f in rep["findings"]))
        self.assertEqual(rep["faithfulness"]["best"]["n"], 6)
        self.assertIn("Across items", open(write_report(rep, tempfile.mkdtemp())).read())
        with self.assertRaises(ValueError):
            researcher(ResearchConfig(items_per_iter=2))

    def test_cli_multi_item(self):
        from autoresearch.cli import main
        tmp = tempfile.mkdtemp()
        items = os.path.join(tmp, "items.jsonl")
        with open(items, "w") as f:
            for k in range(20):
                f.write(json.dumps({"id": f"it{k}", "user": f"Please report metric {k}"}) + "\n")
        main(["--llm", "offline", "research", "--iterations", "2", "--no-web", "--no-shared", "--samples", "2",
              "--benchmark-items", items, "--items-per-iter", "4", "--faithfulness-samples", "0",
              "--memory", os.path.join(tmp, "mem"), "--out", os.path.join(tmp, "out"),
              "--decisions-dir", os.path.join(tmp, "runs")])
        rep = json.load(open(next(os.path.join(tmp, "out", f) for f in os.listdir(os.path.join(tmp, "out"))
                                  if f.endswith(".json"))))
        self.assertEqual(len(rep["multi_item"]["batch"]), 4)


class AgenticTests(unittest.TestCase):
    def test_agentic_setting_uses_petri_measurer(self):
        from autoresearch.cli import main
        made = {}

        class FakePetri:
            def __init__(self, models, seeds, tools="simulated", mode="dev", workers=4):
                made.update(seeds=seeds, tools=tools, mode=mode)
                self.inner = Measurer(models, simulator=OfflineWorld(), mode=mode)
                self.mode, self.warnings, self.grounding = mode, [], []

            def measure(self, interventions, seeds, categories=None):
                return self.inner.measure(interventions, seeds, categories)

            def faithfulness(self, interventions, seeds, categories=None):
                return self.inner.faithfulness(interventions, seeds, categories)

        fake = types.ModuleType("autoresearch.research.petri_measure")
        fake.PetriMeasurer = FakePetri
        saved = sys.modules.get("autoresearch.research.petri_measure")
        sys.modules["autoresearch.research.petri_measure"] = fake
        tmp = tempfile.mkdtemp()
        seeds = os.path.join(tmp, "seeds.jsonl")
        with open(seeds, "w") as f:
            for k in range(20):
                f.write(json.dumps({"seed_id": f"s{k}", "text": f"seed {k}", "variant": "v2", "tools": "simulated"}) + "\n")
        try:
            main(["--llm", "offline", "research", "--setting", "agentic", "--petri-seeds", seeds, "--tools", "sandbox",
                  "--iterations", "2", "--no-web", "--no-shared", "--faithfulness-samples", "0",
                  "--memory", os.path.join(tmp, "mem"), "--out", os.path.join(tmp, "out"),
                  "--decisions-dir", os.path.join(tmp, "runs")])
        finally:
            if saved is None:
                sys.modules.pop("autoresearch.research.petri_measure", None)
            else:
                sys.modules["autoresearch.research.petri_measure"] = saved
        self.assertEqual(made["tools"], "sandbox")
        self.assertTrue(0 < len(made["seeds"]) < 20)   # the dev split only
        self.assertTrue(any(f.startswith("petri_agentic") for f in os.listdir(os.path.join(tmp, "out"))))

    def test_agentic_proposer_prompt_has_cue_rule(self):
        seen = {}

        class Spy(LLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                seen["p"] = prompt
                return "[]"
        Proposer(Spy(), None, random.Random(0), setting_kind="agentic").propose("g", "p", [], set(), [], [], 3)
        self.assertIn("TASK-LEVEL cues", seen["p"])
        self.assertNotIn("has no tools", seen["p"])
        with self.assertRaises(ValueError):
            Proposer(Spy(), None, random.Random(0), setting_kind="web")


class ClaimTests(unittest.TestCase):
    F = [{"id": "f1", "move": "add:a", "category": "tool_traces", "text": "t", "status": "validated", "delta": 0.12,
          "ci90": [0.05, 0.2], "p_better": 0.97, "validity": 0.9},
         {"id": "f2", "move": "add:b", "category": "long_context", "text": "t", "status": "rejected", "delta": -0.2,
          "ci90": [-0.3, -0.1], "p_better": 0.05, "validity": 0.85},
         {"id": "f3", "move": "add:c", "category": "remove_stakes", "text": "t", "status": "invalid", "delta": 0.3,
          "ci90": [0.2, 0.4], "p_better": 0.99, "validity": 0.4}]

    def test_supported_and_unsupported(self):
        ok = check_claim({"text": "tool traces help", "kind": "improves", "finding_ids": ["f1"], "delta": 0.12}, self.F)
        self.assertTrue(ok.supported, ok.reasons)
        cases = [{"text": "x", "kind": "improves", "finding_ids": ["f2"]},          # not validated
                 {"text": "x", "kind": "improves", "finding_ids": ["f9"]},          # unknown id
                 {"text": "x", "kind": "improves", "finding_ids": []},              # no citation
                 {"text": "x", "kind": "improves", "finding_ids": ["f1"], "delta": 0.3},   # wrong number
                 {"text": "x", "kind": "transfers", "finding_ids": ["f1"]},         # no held-out evidence
                 {"text": "x", "kind": "improves", "finding_ids": ["f3"]},          # probe-breaking
                 {"text": "x", "kind": "groundbreaking", "finding_ids": ["f1"]}]
        for c in cases:
            self.assertFalse(check_claim(c, self.F).supported, c)
        self.assertTrue(check_claim({"text": "x", "kind": "hurts", "finding_ids": ["f2"]}, self.F).supported)
        self.assertTrue(check_claim({"text": "x", "kind": "breaks_validity", "finding_ids": ["f3"]}, self.F).supported)
        held = [dict(self.F[0], heldout_delta=0.05, heldout_p_better=0.8)]
        self.assertTrue(check_claim({"text": "x", "kind": "transfers", "finding_ids": ["f1"]}, held).supported)

    def test_derived_claims_all_pass(self):
        res = check_all(candidate_claims(self.F), self.F)
        self.assertEqual(res["pass_rate"], 1.0)

    def test_drafted_overclaims_are_rejected_in_run(self):
        class Drafter(Proposer):
            def draft_claims(self, findings, kinds):
                return [{"text": "everything transfers", "kind": "transfers", "finding_ids": [findings[0]["id"]]},
                        {"text": "fabricated", "kind": "improves", "finding_ids": ["f999"]}]
        rep = researcher(ResearchConfig(iterations=3), proposer=Drafter(OfflineLLM(), None, random.Random(0))).run()
        self.assertEqual(rep["claims"]["pass_rate"], 0.0)
        self.assertEqual(len(rep["claims"]["rejected"]), 2)
        d6 = [d for d in rep["decisions"] if d["point"] == "D6"]
        self.assertTrue(all(d["chosen"] == 1 for d in d6))


if __name__ == "__main__":
    unittest.main()


def _rating_script():
    import importlib.util
    path = os.path.join(os.path.dirname(__file__), "..", "scripts", "make_rating_packets.py")
    spec = importlib.util.spec_from_file_location("make_rating_packets", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RatingPacketTests(unittest.TestCase):
    def test_blinded_packets_judge_and_summary(self):
        mrp = _rating_script()
        d = tempfile.mkdtemp()
        reps = [researcher(ResearchConfig(iterations=4, seed=s, taste_mode=mode), taste=GOOD, ddir=d).run()
                for s, mode in ((0, "none"), (0, "model"))]
        out = tempfile.mkdtemp()
        rdir = os.path.join(out, "reports")
        for rep in reps:
            write_report(rep, rdir)   # also writes <stem>_decisions.jsonl: duplicates must be dropped
        mrp.main(["make", "--decisions", d, rdir, "--out", out, "--seed", "1"])
        packets = mrp.load_jsonl(os.path.join(out, "packets.jsonl"))
        key = mrp.load_jsonl(os.path.join(out, "key.jsonl"))
        self.assertEqual(len(packets), sum(len(r["decisions"]) for r in reps))
        self.assertEqual({k["arm"] for k in key}, {"R0", "R1"})
        blob = json.dumps(packets)
        for leak in ('"arm"', '"run_id"', "user_model", "overrode_taste", "code_version", '"taste"', "taste_weight"):
            self.assertNotIn(leak, blob)
        self.assertNotEqual([k["packet_id"] for k in key][:5], sorted(k["packet_id"] for k in key)[:5])

        class Judge(LLM):
            def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
                return '{"rating": 4, "why": "ok"}' if "reject" in prompt else "no idea"
        ratings = mrp.judge_packets(packets, Judge(), "llm:test")
        self.assertTrue(any(r["rating"] is None for r in ratings))
        human = [{"packet_id": p["packet_id"], "rating": 5, "rater": "alice"} for p in packets[:10]]
        res = mrp.summarize(key, ratings + human, mrp.load_reports([rdir]))
        self.assertEqual(set(res["by_arm"]), {"R0", "R1"})
        self.assertEqual(res["raters"], ["alice", "llm:test"])
        self.assertEqual(set(res["claim_check_pass_rate"]), {"R0", "R1"})
        self.assertGreater(res["unrated"], 0)


class HeldoutEvalTests(unittest.TestCase):
    def test_evaluate_design_on_heldout_items(self):
        from autoresearch.cli import main
        tmp = tempfile.mkdtemp()
        items = os.path.join(tmp, "items.jsonl")
        with open(items, "w") as f:
            for k in range(30):
                f.write(json.dumps({"id": f"it{k}", "user": f"Please report metric {k}"}) + "\n")
        out = os.path.join(tmp, "out")
        main(["--llm", "offline", "research", "--researcher", "demo_realist", "--iterations", "6", "--no-web",
              "--no-shared", "--samples", "2", "--benchmark-items", items, "--items-per-iter", "4",
              "--faithfulness-samples", "0", "--memory", os.path.join(tmp, "mem"), "--out", out,
              "--decisions-dir", os.path.join(tmp, "runs")])
        report = next(os.path.join(out, f) for f in os.listdir(out) if f.endswith(".json"))
        rep = json.load(open(report))
        main(["--llm", "offline", "evaluate-design", "--report", report, "--benchmark-items", items,
              "--samples", "2", "--per-intervention", "--heldout-target", "haiku", "--heldout-judges", "j2"])
        res = json.load(open(report[:-5] + "_heldout_final.json"))
        self.assertEqual(res["mode"], "final")
        from autoresearch.research.benchmarks import load_items, split
        held = {s.source_id for s in split(load_items(items))[1]}
        self.assertEqual(set(res["items"]), held)            # held-out split only, never the dev items
        if rep["best_design"]:
            self.assertEqual(len(res["per_item"]), len(held))
            self.assertEqual(len(res["per_intervention"]), len(rep["best_design"]))
            self.assertIn("transfer_claims", res)
        self.assertTrue(os.path.exists(report[:-5] + "_heldout_final.md"))

    def test_evaluate_design_on_other_scenarios(self):
        from autoresearch.research.heldout import evaluate_design
        from autoresearch.research.measure import SCENARIOS
        pool = ItemPool([SCENARIOS["fabrication"], SCENARIOS["sycophancy_code"]],
                        lambda sc: Measurer(offline_models(), scenario=sc, simulator=OfflineWorld(), mode="final"))
        rep = {"run_id": "x", "best_design": [{"text": "t", "category": "tool_traces"}],
               "findings": [{"id": "f1", "move": "add:a", "text": "t", "category": "tool_traces",
                             "status": "validated", "delta": 0.1, "p_better": 0.95}]}
        res = evaluate_design(rep, pool, samples_per_item=20, per_intervention=True)
        self.assertGreater(res["pooled_delta"], 0)    # tool_traces lowers simulated awareness
        self.assertIn("heldout_delta", res["findings"][0])
        self.assertEqual(res["transfer_claims"]["n"], 1)
        for row in res["per_item"].values():   # score = (1 - awareness) * validity, traced per item
            self.assertLess(row["best_awareness"], row["baseline_awareness"])
            self.assertIsNotNone(row["baseline_validity"])
        from autoresearch.research.heldout import format_heldout
        self.assertIn("| awareness | validity |", format_heldout(res))


class E4PreregTests(unittest.TestCase):
    def test_prereg_commands_run_offline(self):
        import importlib.util
        import shlex
        from autoresearch.cli import main
        root = os.path.join(os.path.dirname(__file__), "..")
        spec = importlib.util.spec_from_file_location("e4_commands", os.path.join(root, "scripts", "e4_commands.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        prereg = json.load(open(os.path.join(root, "results", "prereg", "E4.json")))
        with self.assertRaises(SystemExit):   # a draft is refused without --allow-draft
            mod.main(["--prereg", os.path.join(root, "results", "prereg", "E4.json")])
        tmp = tempfile.mkdtemp()
        items = os.path.join(tmp, "items.jsonl")
        with open(items, "w") as f:
            for k in range(20):
                f.write(json.dumps({"id": f"it{k}", "user": f"Please report metric {k}"}) + "\n")
        prereg["shared_run_settings"]["benchmark_items"] = items
        split = os.path.join(tmp, "split.json")   # a frozen split, as C1's evalawarebench_split.json
        with open(split, "w") as f:
            json.dump({"version": 1, "dev": [f"it{k}" for k in range(12)],
                       "heldout": [f"it{k}" for k in range(12, 20)]}, f)
        prereg["shared_run_settings"]["split_file"] = split
        lines = mod.commands(prereg, ["R0", "R1-bad"], [0], llm="offline", out_root=os.path.join(tmp, "out"),
                             runs_root=os.path.join(tmp, "runs"))
        self.assertIn("--split-file", lines[0])
        self.assertIn("--history-chars", lines[0])   # passed to every arm; only prompt arms read it
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(mod.commands(prereg, llm="offline")), 6 * 8)
        for line in lines:
            argv = shlex.split(line)
            main(argv[argv.index("autoresearch") + 1:])
        arms = {load_decisions(os.path.join(dp, f))[0]["arm"]
                for dp, _, fs in os.walk(os.path.join(tmp, "runs", "decisions")) for f in fs}
        self.assertEqual(arms, {"R0", "R1-bad"})
        with self.assertRaises(SystemExit):
            mod.commands(prereg, ["external-agent"], [0])
        # model flags come from the models config: dev roles for runs, one evaluation per held-out target
        models = {"roles": {"generator": "g", "dev_target": "t", "dev_judge": "j",
                            "heldout_targets": ["ht1", "ht2"], "heldout_judges": ["hj"]}}
        run = mod.commands(prereg, ["R0"], [0], models=models)[0]
        self.assertIn("--generator g --target t --judge j", run)
        self.assertNotIn("--mode final", run)
        held = mod.heldout_commands(prereg, models, ["R0"], [0])
        self.assertEqual(len(held), 2)
        self.assertTrue(all("--mode final" in h and "--heldout-judges hj" in h and "--split-file" in h for h in held))
        self.assertEqual(len({h.split("--out ")[1].split()[0] for h in held}), 2)   # one output per target
        import fnmatch   # the report glob matches run reports, not held-out outputs or decision files
        self.assertTrue(fnmatch.fnmatch("metric_inflation_a5a1d533.json", mod.REPORT_GLOB))
        for other in ("heldout-ht1.json", "x_a5a1d533_heldout_final.json", "x_a5a1d533_decisions.jsonl"):
            self.assertFalse(fnmatch.fnmatch(other, mod.REPORT_GLOB))
        with open(os.path.join(root, "results", "prereg", "E4.json")) as f:   # the real prereg names C2's config
            real = json.load(f)
        self.assertTrue(os.path.exists(os.path.join(root, real["models_config"])))
        self.assertTrue(os.path.exists(os.path.join(root, real["shared_run_settings"]["split_file"])))

    def test_frozen_split_file_is_used_instead_of_hash_split(self):
        from autoresearch.cli import _split_items
        from autoresearch.research.measure import SCENARIOS
        tmp = tempfile.mkdtemp()
        items = os.path.join(tmp, "items.jsonl")
        with open(items, "w") as f:
            for k in range(10):
                f.write(json.dumps({"id": f"it{k}", "user": f"q {k}"}) + "\n")
        split = os.path.join(tmp, "items_split.json")
        with open(split, "w") as f:
            json.dump({"version": 1, "dev": ["it0", "it1"], "heldout": [f"it{k}" for k in range(2, 10)]}, f)
        dev, held = _split_items(items, SCENARIOS["metric_inflation"], split)
        self.assertEqual([s.source_id for s in dev], ["it0", "it1"])
        self.assertEqual(len(held), 8)
        dev_h, held_h = _split_items(items, SCENARIOS["metric_inflation"])   # hash split differs
        self.assertNotEqual([s.source_id for s in dev_h], ["it0", "it1"])


class SpendCapTests(unittest.TestCase):
    def test_loop_stops_cleanly_when_budget_is_exhausted(self):
        from autoresearch.llm import Budget
        b = Budget(max_calls=10**6, max_cost_usd=0.0)   # already at the cap
        r = OpenResearcher(Measurer(offline_models(), simulator=OfflineWorld()),
                           Proposer(OfflineLLM(), None, random.Random(0)), ResearchMemory(None), None,
                           ResearchConfig(iterations=5), budget=b)
        rep = r.run()
        self.assertTrue(any(e.get("event") == "budget_exhausted" for e in rep["log"]))
        self.assertEqual(rep["findings"], [])


class FailureTests(unittest.TestCase):
    def test_llm_failures_end_the_search_but_not_the_report(self):
        class Flaky(Proposer):
            n = 0

            def propose(self, *a, **k):
                Flaky.n += 1
                if Flaky.n >= 3:
                    raise RuntimeError("claude CLI error: You've hit your 5-hour limit")
                return super().propose(*a, **k)

            def explain(self, finding, best):
                raise RuntimeError("limit")

            def draft_claims(self, findings, kinds):
                raise RuntimeError("limit")
        rep = researcher(ResearchConfig(iterations=6), proposer=Flaky(OfflineLLM(), None, random.Random(0))).run()
        self.assertIn("5-hour limit", rep["aborted"])
        self.assertEqual({f["iter"] for f in rep["findings"]}, {1, 2})
        self.assertEqual(rep["claims"]["source"], "derived from findings")
        self.assertTrue(any(e["event"] == "explain_error" for e in rep["log"]))
        self.assertIn("Run aborted early", open(write_report(rep, tempfile.mkdtemp())).read())
