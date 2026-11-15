"""Source-to-decision trail (integrations/trail.py) over artifacts written by the real loops, offline."""
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from autoresearch.integrations import trail
from autoresearch.integrations.exa import Source
from autoresearch.integrations.shared_memory import LocalSharedMemory, format_fact
from autoresearch.llm import OfflineLLM
from autoresearch.loop import LoopConfig, Researcher
from autoresearch.memory import ResearchMemory
from autoresearch.research.ideas import FEATURES, Intervention, Proposer
from autoresearch.research.loop import OpenResearcher, ResearchConfig, write_report
from autoresearch.research.market import Market, Wallets
from autoresearch.research.measure import Measurer, Models, OfflineWorld
from autoresearch.tasks import get_task

REFUTED_KNOBS = ("framing", "names")


class FactCheckScout:
    """Stands in for WebScout: logs Sources exactly as WebScout._log does and
    refutes every change to REFUTED_KNOBS, supports noise changes."""

    def __init__(self):
        self.sources = []

    def check_assumption(self, goal, change, hypothesis):
        urls = [f"https://example.org/{change.replace('=', '-')}/{k}" for k in range(2)]
        self.sources += [Source(u, f"Page about {change} <{k}>", "2026-01-0%d" % (k + 1), "fact_check", change)
                         for k, u in enumerate(urls)]
        stance = ("refute" if change.split("=")[0] in REFUTED_KNOBS
                  else "support" if change.startswith("noise") else "none")
        return {"stance": stance, "confidence": 0.9 if stance != "none" else 0.0, "urls": urls}

    def discover_options(self, *a):
        return []


def run_v1(root, seed=1, iterations=6):
    shared = LocalSharedMemory(os.path.join(root, "shared.jsonl"))
    r = Researcher(get_task("eval_awareness"), OfflineLLM(), ResearchMemory(os.path.join(root, "memory")), None,
                   LoopConfig(iterations=iterations, seed=seed), log_dir=os.path.join(root, "out"),
                   scout=FactCheckScout(), shared=shared)
    return r.run()


class _Exa:
    def search(self, q, num_results=5, since_days=None, **kw):
        return [{"url": "https://example.org/paper-a", "title": "Paper A", "publishedDate": "2026-03-01"},
                {"url": "https://example.org/paper-b", "title": "Paper B", "publishedDate": None}]


class _V2Scout:
    def __init__(self):
        self.exa, self.since_days, self.sources = _Exa(), 540, []

    def grounding_material(self, topic, n=2):
        return []


class _WebProposer(Proposer):
    """The offline proposer turns no web results into ideas; this one turns the first into one."""

    def from_web(self, results, goal):
        return [Intervention("Quote a stale changelog line from the vendor's release notes.", "tool_traces",
                             {f: 0.5 for f in FEATURES}, "from the paper", "exa", results[0]["url"], p_validated=0.6)]


def run_v2(root, iterations=4):
    shared = LocalSharedMemory(os.path.join(root, "shared.jsonl"))
    cfg = ResearchConfig(iterations=iterations, seed=0, allocation="market", faithfulness_samples=0, taste_mode="none")
    r = OpenResearcher(Measurer(Models(OfflineLLM(), OfflineLLM(), OfflineLLM()), simulator=OfflineWorld()),
                       _WebProposer(OfflineLLM(), None, random.Random(0)), ResearchMemory(os.path.join(root, "mem")),
                       None, cfg, scout=_V2Scout(), shared=shared,
                       market=Market(Wallets(os.path.join(root, "mem", "wallets.json")), shared=shared))
    rep = r.run()
    write_report(rep, os.path.join(root, "out"))
    return rep


def fields(data):
    return {m["field"] for m in data["missing_fields"]}


class TestV1Trail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = cls.tmp.name
        cls.rep = run_v1(cls.root)
        cls.data = trail.trail(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_veto_is_traced(self):
        vetoes = [e for e in self.rep.drift_events if e["kind"] == "web_refuted"]
        self.assertTrue(vetoes, "fixture should produce at least one web veto")
        run = self.data["runs"][0]
        traced = [t for t in run["vetoes"] if t["kind"] == "web_refuted"]
        self.assertEqual([(t["iter"], t["change"]) for t in traced],
                         [(e["iteration"], e["detail"].split()[0]) for e in vetoes])
        history = {h["iter"]: h for h in self.rep.history}
        for t in traced:
            self.assertIn(t["change"].split("=")[0], REFUTED_KNOBS)
            # 1. sources: the cited URLs resolve to this run's fact_check Sources, with publish dates
            self.assertTrue(t["sources"] and all(s["linked"] for s in t["sources"]))
            self.assertTrue(all(s["used_for"] == "fact_check" and s["published"] for s in t["sources"]))
            # 2. evidence: the refuting fact the veto cites, placed in the veto's iteration by write order
            cited = [e for e in t["evidence"] if e["cited_by_veto"]]
            self.assertEqual(len(cited), 1)
            self.assertEqual((cited[0]["stance"], cited[0]["iter"]), ("refute", t["iter"]))
            # 3. the credence change it caused (rule-derived weight), with the final credence below 0.5
            ups = t["credence"]["updates"]
            self.assertTrue(ups and all(u["direction"] == "-" and u["weight"] == 0.45 for u in ups))
            self.assertLess(t["credence"]["final"]["credence"], 0.5)
            # 4. what ran instead: the history entry, decision record and OUTCOME fact of that iteration
            self.assertEqual(t["ran_instead"]["change"], history[t["iter"]]["change"])
            self.assertEqual(t["decision"]["chosen"], history[t["iter"]]["change"])
            self.assertIn(t["change"], t["decision"]["options"])
            self.assertFalse(t["veto_overridden"])
            self.assertEqual(len(t["ran_instead_outcomes"]), 1)
            self.assertAlmostEqual(float(t["ran_instead_outcomes"][0]["delta"]), round(history[t["iter"]]["delta"], 4))

    def test_credence_updates(self):
        run = self.data["runs"][0]
        with open(os.path.join(self.root, "shared.jsonl")) as fh:
            rows = [json.loads(l) for l in fh]
        expected = [r for r in rows if r["content"].startswith("EVIDENCE")
                    and re.search(r"stance=(support|refute)", r["content"])]
        self.assertEqual(len(run["credence_updates"]), len(expected))
        for u in run["credence_updates"]:
            self.assertIsNotNone(u["iter"])
            self.assertEqual(u["experiment_at_iter"]["iter"], u["iter"])
            self.assertEqual(u["direction"], "-" if u["evidence"]["stance"] == "refute" else "+")
            self.assertEqual(u["vetoed"], u["evidence"]["stance"] == "refute")

    def test_unrecorded_links_are_listed_as_missing(self):
        f = fields(self.data)
        for k in ("veto.evidence_refs", "veto.refute_confidence", "source.iter", "credence.before_after",
                  "outcome.iter"):
            self.assertIn(k, f)
        self.assertNotIn("shared.memory_file", f)
        self.assertNotIn("v1.decisions_file", f)

    def test_without_shared_memory_and_sources_nothing_is_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(self.root, "out")
            name = os.listdir(src)[0]
            with open(os.path.join(src, name)) as fh:
                rep = json.load(fh)
            rep["sources"] = []
            with open(os.path.join(d, name), "w") as fh:
                json.dump(rep, fh)
            data = trail.trail(d)
            t = data["runs"][0]["vetoes"][0]
            self.assertEqual(t["evidence"], [])
            self.assertTrue(t["evidence_link"].startswith("MISSING"))
            self.assertTrue(t["sources"] and not any(s["linked"] for s in t["sources"]))   # only the veto's own URLs
            self.assertIsNone(t["decision"])
            self.assertEqual(t["ran_instead_outcomes"], [])
            self.assertEqual(data["runs"][0]["credence_updates"], [])
            self.assertTrue({"shared.memory_file", "v1.decisions_file"} <= fields(data))
            # an explicit --memory/--decisions brings the facts back
            data = trail.trail(d, [os.path.join(self.root, "shared.jsonl")],
                               [os.path.join(self.root, "memory", "decisions.jsonl")])
            t = data["runs"][0]["vetoes"][0]
            self.assertTrue(any(e["cited_by_veto"] for e in t["evidence"]))
            self.assertIsNotNone(t["decision"])

    def test_evidence_from_another_run(self):
        with tempfile.TemporaryDirectory() as d:
            for sub in ("out", "memory"):
                shutil.copytree(os.path.join(self.root, sub), os.path.join(d, sub))
            with open(os.path.join(self.root, "shared.jsonl")) as fh:
                rows = fh.read()
            veto = self.data["runs"][0]["vetoes"][0]
            other = format_fact("EVIDENCE", task="eval_awareness", change=veto["change"], stance="support",
                                confidence=0.8, urls="https://example.org/elsewhere", run="otherrun")
            outcome = format_fact("OUTCOME", task="eval_awareness", change=veto["change"], delta=0.05, valid=True,
                                  run="otherrun")
            with open(os.path.join(d, "shared.jsonl"), "w") as fh:
                fh.write(json.dumps({"author": "scout", "content": other}) + "\n" + rows
                         + json.dumps({"author": "experimenter", "content": outcome}) + "\n")
            t = trail.trail(d)["runs"][0]["vetoes"][0]
            foreign = [e for e in t["evidence"] if e["run"] == "otherrun"]
            self.assertEqual(len(foreign), 1)
            self.assertFalse(foreign[0]["this_run"])
            self.assertIsNone(foreign[0]["iter"])
            src = [s for s in t["sources"] if s["url"] == "https://example.org/elsewhere"]
            self.assertFalse(src[0]["linked"])
            self.assertEqual(t["evidence_counts"]["support"], 1)
            self.assertEqual([o["run"] for o in t["vetoed_change_elsewhere"]["other_runs"]], ["otherrun"])

    def test_renderers_and_cli(self):
        md = trail.render_markdown(self.data)
        self.assertIn("### Veto 1:", md)
        self.assertIn("## Fields the loop does not record", md)
        page = trail.render_html(self.data)
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertNotIn("<script", page)
        self.assertIsNone(re.search(r"<link|\bsrc=", page))           # self-contained: no external assets
        self.assertNotIn("<0>", page)                                   # source titles are escaped
        self.assertIn("&lt;0&gt;", page)
        with tempfile.TemporaryDirectory() as d:
            out = StringIO()
            with redirect_stdout(out):
                rc = trail.main([self.root, "--json", "--html", os.path.join(d, "t.html"), "--md", os.path.join(d, "t.md")])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue())["n_vetoes"], self.data["n_vetoes"])
            self.assertTrue(os.path.getsize(os.path.join(d, "t.html")) > 0)
            with open(os.path.join(d, "t.md")) as fh:
                self.assertEqual(fh.read(), md)


class TestV2Trail(unittest.TestCase):
    def test_exa_idea_to_findings_outcomes_and_decisions(self):
        with tempfile.TemporaryDirectory() as d:
            rep = run_v2(d)
            data = trail.trail(d)
            run = data["runs"][0]
            self.assertEqual((run["loop"], run["vetoes"], run["credence_updates"]), ("v2", [], []))
            self.assertIn("v2.fact_check", fields(data))
            self.assertEqual(len(run["source_trails"]), 1)          # discovered twice, one trail
            t = run["source_trails"][0]
            self.assertEqual(t["idea"]["times_discovered"], sum(w["origin"] == "exa" for w in rep["web_ideas"]))
            self.assertEqual(t["sources"][0]["url"], "https://example.org/paper-a")
            self.assertTrue(t["sources"][0]["linked"])
            self.assertEqual(t["sources"][0]["published"], "2026-03-01")
            self.assertTrue(any(b["agent"] == "scout" for b in t["bids"]))
            self.assertTrue(t["critic"] and all(b["against"] for b in t["critic"]))
            mine = [f for f in rep["findings"] if f["origin"] == "exa"]
            self.assertEqual([f["id"] for f in t["findings"]], [f["id"] for f in mine])
            self.assertEqual(len(t["outcomes"]), len(mine))
            self.assertTrue(any(x["point"] == "D1" for x in t["decisions"]))
            self.assertIn("&lt;", trail.render_html({**data, "source": "<x>"}))


class TestDemoMoment(unittest.TestCase):
    def test_trail_is_an_optional_fifth_moment(self):
        spec = importlib.util.spec_from_file_location("track_e_demo_trail",
                                                      Path(__file__).resolve().parents[1] / "scripts/demo.py")
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            def git(*args):
                return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                                      cwd=root, check=True, capture_output=True)
            git("init", "-q")
            run_v1(str(root / "results" / "v1"))
            git("add", ".")
            git("commit", "-qm", "evidence")
            self.assertEqual(len(demo.replay(root=root)["moments"]), 4)
            data = demo.replay(root=root, trail=True)
            self.assertEqual(len(data["moments"]), 5)
            m = data["moments"][4]
            self.assertTrue(m["available"])
            self.assertGreater(m["evidence"]["vetoes"], 0)
            self.assertIn("veto.evidence_refs", m["evidence"]["missing_fields"])
            self.assertFalse(data["complete"])   # the other four moments have no evidence here


if __name__ == "__main__":
    unittest.main()
