"""Realism ladder: build, offline end-to-end run, analysis and the draft pre-registration (offline, free)."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from autoresearch.research import ladder
from autoresearch.research.petri_measure import validate_audit_seed

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [{"seed_id": "s1", "text": "Seed one.", "variant": "v2", "tools": "sandbox", "split": "hidden"},
         {"seed_id": "s2", "text": "Seed two.", "variant": "v2", "split": "hidden"},
         {"seed_id": "s3", "text": "Seed three.", "variant": "v2", "split": "dev"}]
REPOS = [{"url": "https://github.com/b-org/b", "licence": "MIT", "extra": "kept"},
         {"url": "https://github.com/a-org/a", "ref": "main", "depth": 50}]


def sample(seed, level, a1, a2, epoch=0, **kw):
    """A PetriSample-style row as PetriMeasurer writes it."""
    d = {"seed_id": f"{seed}{ladder.LEVEL_SEP}{level}@s{epoch}", "verbalized": a1, "self_report": a2,
         "behavior": "aligned", "error": ""}
    d.update(kw)
    return d


class BuildTest(unittest.TestCase):
    def test_every_seed_at_every_level_deterministic(self):
        rows = ladder.build(SEEDS, REPOS)
        self.assertEqual(rows, ladder.build(SEEDS, REPOS))
        self.assertEqual(len(rows), len(SEEDS) * 4)
        self.assertEqual([r["realism_level"] for r in rows[:4]], list(ladder.LEVELS))
        self.assertEqual([r["base_seed_id"] for r in rows[::4]], ["s1", "s2", "s3"])
        for r in rows:
            validate_audit_seed(r)
            self.assertEqual(r["tools"], ladder.LEVEL_TOOLS[r["realism_level"]])
            self.assertEqual("repo" in r, r["realism_level"] == "L3_repo")
            self.assertEqual(ladder.split_id(r["seed_id"]), (r["base_seed_id"], r["realism_level"]))
        l0 = rows[0]
        self.assertTrue(l0["text"].startswith("Seed one.") and l0["text"].endswith(ladder.TEXT_ONLY_INSTRUCTION))
        self.assertEqual(rows[1]["text"], "Seed one.")
        self.assertEqual(l0["split"], "hidden")

    def test_repo_assignment(self):
        seeds = [dict(SEEDS[0], repo={"url": "https://github.com/own/repo"}), SEEDS[1], SEEDS[2]]
        repos = REPOS + [{"url": "https://github.com/tag/t", "seed_id": "s3"}]
        got = {r["base_seed_id"]: r["repo"] for r in ladder.build(seeds, repos) if r["realism_level"] == "L3_repo"}
        self.assertEqual(got["s1"], {"url": "https://github.com/own/repo"})
        self.assertEqual(got["s2"], {"url": "https://github.com/a-org/a", "ref": "main", "depth": 50})
        self.assertEqual(got["s3"], {"url": "https://github.com/tag/t"})
        cycled = ladder.assign_repos([{"seed_id": f"x{i}"} for i in range(3)], REPOS)
        self.assertEqual([cycled[f"x{i}"]["url"] for i in range(3)],
                         ["https://github.com/a-org/a", "https://github.com/b-org/b", "https://github.com/a-org/a"])
        self.assertEqual(cycled["x1"]["extra"], "kept")            # repo fields pass through as given
        local = ladder.assign_repos([{"seed_id": "y"}], [{"local_path": "/r", "seed_id": "y", "scrub": False}])
        self.assertEqual(local["y"], {"local_path": "/r", "scrub": False})
        with self.assertRaises(ValueError):
            ladder.assign_repos([{"seed_id": "z"}], [{"licence": "MIT"}])

    def test_errors(self):
        with self.assertRaises(ValueError):
            ladder.build(SEEDS, [])                       # L3 without repos
        self.assertEqual(len(ladder.build(SEEDS, [], levels=["L0_text", "L1_simulated"])), 6)
        with self.assertRaises(ValueError):
            ladder.build([SEEDS[0], SEEDS[0]], REPOS)
        with self.assertRaises(ValueError):
            ladder.build([{"seed_id": "a__b", "text": "x"}], REPOS)

    def test_cli_build_split(self):
        with tempfile.TemporaryDirectory() as d:
            s, r, o = Path(d, "s.jsonl"), Path(d, "r.jsonl"), Path(d, "o.jsonl")
            s.write_text("".join(json.dumps(x) + "\n" for x in SEEDS))
            r.write_text("".join(json.dumps(x) + "\n" for x in REPOS))
            with contextlib.redirect_stderr(io.StringIO()):
                ladder.main(["build", "--seeds", str(s), "--repos", str(r), "--split", "hidden", "--out", str(o)])
            rows = [json.loads(l) for l in o.read_text().splitlines()]
            self.assertEqual(sorted({x["base_seed_id"] for x in rows}), ["s1", "s2"])


class AnalyzeTest(unittest.TestCase):
    def rows(self):
        out = []
        for i, seed in enumerate(["a", "b", "c", "d"]):
            for k, level in enumerate(ladder.LEVELS):
                for e in range(2):   # two epochs, averaged per seed before pairing
                    out.append(sample(seed, level, 0.8 - 0.2 * k + 0.01 * i, 0.9 - 0.1 * k + (0.02 if e else 0.0), e))
        out.append(sample("a", "L1_simulated", 0.0, 0.0, 9, error="audit error: boom", behavior="error"))
        out.append({"seed_id": "unlabelled@s0", "verbalized": 1.0, "self_report": 1.0})
        return out

    def test_levels_adjacent_and_trend(self):
        rep = ladder.analyze(self.rows(), {"code_version": "abc1234", "cost_usd": 1.5})
        self.assertEqual(rep["levels"], list(ladder.LEVELS))
        self.assertEqual(rep["seeds"], ["a", "b", "c", "d"])
        self.assertEqual((rep["code_version"], rep["cost_usd"], rep["n_unlabelled_rows"]), ("abc1234", 1.5, 1))
        l1 = rep["per_level"]["L1_simulated"]
        self.assertEqual((l1["n"], l1["n_ok"], l1["n_errors"]), (9, 8, 1))
        self.assertAlmostEqual(rep["per_level"]["L0_text"]["A1"]["mean"], 0.815)
        for step, d in rep["adjacent"]["A1"].items():
            self.assertEqual(d["n_seeds"], 4)
            self.assertAlmostEqual(d["mean_diff"], -0.2)
            self.assertEqual(d["p_lower"], 1.0)
        self.assertAlmostEqual(rep["adjacent"]["A2"]["L0_text->L1_simulated"]["mean_diff"], -0.1)
        t = rep["trend"]["A1"]
        self.assertEqual((t["n_seeds"], t["n_seeds_all_levels"]), (4, 4))
        self.assertAlmostEqual(t["mean_slope"], -0.2)
        self.assertAlmostEqual(t["p_two_sided"], 2 / 16)   # exact sign-flip: all four slopes negative
        md = ladder.markdown(rep)
        self.assertIn("| L0_text | 8/8 | 4 |", md)
        self.assertNotIn("OFFLINE", md)

    def test_sign_flip_and_slope(self):
        self.assertEqual(ladder.sign_flip_p([1.0, 1.0, 1.0]), 2 / 8)
        self.assertEqual(ladder.sign_flip_p([1.0, -1.0]), 1.0)
        self.assertIsNone(ladder.sign_flip_p([]))
        self.assertLess(ladder.sign_flip_p([0.5] * 20, n_perm=2000), 0.01)
        self.assertAlmostEqual(ladder.slope([(0, 1.0), (1, 0.5), (3, -0.5)]), -0.5)

    def test_missing_levels_pair_on_shared_seeds(self):
        rows = [sample("a", "L0_text", 1.0, 1.0), sample("a", "L2_sandbox", 0.0, 0.5), sample("b", "L0_text", 1.0, 1.0)]
        rep = ladder.analyze(rows)
        self.assertEqual(rep["levels"], ["L0_text", "L2_sandbox"])
        d = rep["adjacent"]["A1"]["L0_text->L2_sandbox"]
        self.assertEqual((d["n_seeds"], d["mean_diff"], d["ci"]), (1, -1.0, None))
        self.assertEqual(rep["trend"]["A1"]["n_seeds"], 1)

    def test_explicit_fields_win_over_the_id(self):
        # a row's own realism_level / base_seed_id are read first; the "<id>__<level>" parse is the fallback
        tagged = {"seed_id": "renamed@s0", "base_seed_id": "a", "realism_level": "L2_sandbox",
                  "verbalized": 0.2, "self_report": 0.3}
        self.assertEqual((ladder.row_level(tagged), ladder.row_seed(tagged)), ("L2_sandbox", "a"))
        clash = dict(tagged, seed_id=f"b{ladder.LEVEL_SEP}L0_text@s0")
        self.assertEqual((ladder.row_level(clash), ladder.row_seed(clash)), ("L2_sandbox", "a"))
        old = sample("c", "L1_simulated", 0.5, 0.5)                    # older results: no fields, parsed from the id
        self.assertEqual((ladder.row_level(old), ladder.row_seed(old)), ("L1_simulated", "c"))
        legacy = dict(old, base_seed_id=f"c{ladder.LEVEL_SEP}L1_simulated")   # ladder id stored as base_seed_id
        self.assertEqual(ladder.row_seed(legacy), "c")
        at = {"seed_id": "x@cond@s1", "base_seed_id": "x@cond", "realism_level": "L0_text"}
        self.assertEqual(ladder.row_seed(at), "x@cond")                # an explicit base id is used as given
        rep = ladder.analyze([tagged, clash, old])
        self.assertEqual(rep["levels"], ["L1_simulated", "L2_sandbox"])
        self.assertEqual(rep["per_level"]["L2_sandbox"]["n"], 2)
        self.assertEqual(rep["seeds"], ["a", "c"])

    def test_offline_run_samples_carry_the_fields(self):
        rows = ladder.build(SEEDS[:2], REPOS)
        with contextlib.redirect_stderr(io.StringIO()):
            rep = ladder.run(rows, offline=True, epochs=2)
        for s in rep["samples"]:
            self.assertIn(s["realism_level"], ladder.LEVELS)
            self.assertIn(s["base_seed_id"], ("s1", "s2"))
            self.assertEqual(ladder.split_id(s["seed_id"]), (s["base_seed_id"], s["realism_level"]))

    def test_load_formats(self):
        with tempfile.TemporaryDirectory() as d:
            rows = self.rows()
            Path(d, "r.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            Path(d, "CODE_VERSION").write_text("deadbee\n")
            got = ladder.load_results(str(Path(d, "r.jsonl")))
            self.assertEqual((len(got["rows"]), got["meta"]["code_version"]), (len(rows), "deadbee"))
            Path(d, "e3b.json").write_text(json.dumps({"code_version": "c0ffee1", "offline": True,
                                                       "samples": {"x": rows[:3], "y": rows[3:5]}}))
            got = ladder.load_results(str(Path(d, "e3b.json")))
            self.assertEqual((len(got["rows"]), got["meta"]["code_version"], got["meta"]["offline"]), (5, "c0ffee1", True))


class OfflineEndToEndTest(unittest.TestCase):
    def test_smoke(self):
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                ladder.main(["smoke", "--out-dir", d, "--limit", "3", "--epochs", "2"])
            seeds = [json.loads(l) for l in Path(d, "ladder_seeds.jsonl").read_text().splitlines()]
            self.assertEqual(len(seeds), 12)
            rep = json.loads(Path(d, "ladder_report.json").read_text())
            self.assertTrue(rep["offline"])
            self.assertEqual(rep["levels"], list(ladder.LEVELS))
            for lvl in ladder.LEVELS:
                s = rep["per_level"][lvl]
                self.assertEqual((s["n"], s["n_ok"], len(s["seeds"])), (6, 6, 3))
            self.assertEqual(rep["trend"]["A2"]["n_seeds_all_levels"], 3)
            self.assertEqual(rep["cost_usd"], 0)
            self.assertIn("OFFLINE SIMULATOR", Path(d, "ladder_report.md").read_text())
            run = json.loads(Path(d, "ladder_run.json").read_text())
            self.assertEqual({ladder.row_level(r) for r in run["samples"]}, set(ladder.LEVELS))

    def test_paid_run_refuses_without_flag(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "s.jsonl").write_text(json.dumps(ladder.build(SEEDS[:1], REPOS)[0]) + "\n")
            with self.assertRaises(SystemExit):
                ladder.main(["run", "--seeds", str(Path(d, "s.jsonl")), "--out", str(Path(d, "o.json"))])


class PreregTest(unittest.TestCase):
    def test_draft_prereg(self):
        p = json.loads((ROOT / "results" / "prereg" / "realism_ladder.json").read_text())
        self.assertEqual(p["experiment"], "realism_ladder")
        self.assertTrue(p["status"].startswith("DRAFT"))
        self.assertEqual(list(p["levels"]), list(ladder.LEVELS))
        self.assertIn(ladder.TEXT_ONLY_INSTRUCTION.strip(), p["levels"]["L0_text"]["instruction"])


if __name__ == "__main__":
    unittest.main()
