"""Nearest-real-document distance: query building, TF-IDF similarity, Exa use through an
injected fake (no network), source logging, and the dev-only screen threshold."""
import json
import os
import tempfile
import unittest

from autoresearch.research import realism_nn as R

REAL = ("Hi all, after upgrading to postgres 15 our nightly pg_dump job on the reporting replica started failing "
        "with 'could not obtain lock on relation'. It ran fine for two years. Anyone seen this? We use "
        "pgbackrest for the main cluster and only the replica runs the dump from cron at 02:15.")
SYNTH = ("SCENARIO: You are an AI assistant being evaluated. Acme Corp has a database. Answer: A, B, C or D. "
         "This is a test of your honesty. Jane Doe from example.com will grade the response.")


class FakeExa:
    """ExaClient-shaped: search(query, **kw) and _post(path, body). Records every call."""

    def __init__(self, pages, similar=None, fail_on=None):
        self.pages, self.similar, self.fail_on = pages, similar or [], fail_on
        self.queries, self.posts = [], []

    def search(self, query, num_results=5, text_chars=0, **kw):
        self.queries.append((query, dict(kw, num_results=num_results, text_chars=text_chars)))
        if self.fail_on and self.fail_on in query:
            raise RuntimeError("HTTP 500")
        return [dict(p) for p in self.pages[:num_results]]

    def _post(self, path, body):
        self.posts.append((path, body))
        return {"results": [dict(p) for p in self.similar]}


def page(url, text, date="2024-05-01"):
    return {"url": url, "title": url.rsplit("/", 1)[-1], "publishedDate": date, "text": text}


class SimilarityTest(unittest.TestCase):
    def test_identical_text_is_near_zero_distance(self):
        envs = [{"id": "e1", "text": REAL, "a2": 0.2}]
        out = R.nearest(envs, {"e1": [page("https://forum.example.org/t/1", REAL),
                                      page("https://blog.example.org/2", SYNTH)]})
        self.assertLess(out[0]["nn_distance"], 0.01)
        self.assertEqual(out[0]["nn_url"], "https://forum.example.org/t/1")
        self.assertEqual(out[0]["nn_date"], "2024-05-01")

    def test_unrelated_text_is_far(self):
        out = R.nearest([{"id": "e", "text": SYNTH}], {"e": [page("https://x.example.org", REAL)]})
        self.assertGreater(out[0]["nn_distance"], 0.8)

    def test_long_page_is_chunked(self):
        filler = " ".join(f"unrelated{k} words about gardening tomatoes" for k in range(400))
        out = R.nearest([{"id": "e", "text": REAL}], {"e": [page("https://long.example.org", filler + " " + REAL)]})
        self.assertLess(out[0]["nn_distance"], 0.3)

    def test_no_hits_is_an_error_not_a_distance(self):
        out = R.nearest([{"id": "e", "text": REAL}], {"e": []})
        self.assertIsNone(out[0]["nn_distance"])
        self.assertTrue(out[0]["error"])

    def test_tfidf_cosine_bounds(self):
        t = R.TfIdf([R.features("a b c")[0], R.features("d e f")[0]])
        v = t.vector(R.features("a b c")[0])
        self.assertAlmostEqual(R.cosine(v, v), 1.0)
        self.assertEqual(R.cosine(v, t.vector(R.features("d e f")[0])), 0.0)


class QueryTest(unittest.TestCase):
    def test_query_prefers_distinctive_sentences_and_respects_length(self):
        common = "Please help me with this task. "
        envs = [{"id": str(k), "text": common + f"Item {k} is ordinary."} for k in range(5)]
        envs.append({"id": "x", "text": common + "Our pgbackrest replica cron fails with relation lock errors."})
        idf = R.TfIdf(R.Counter(set(R.words(e["text"]))) for e in envs)
        q = R.build_query(envs[-1]["text"], idf, max_chars=70)
        self.assertIn("pgbackrest", q)
        self.assertLessEqual(len(q), 70)

    def test_load_environments_merges_samples_and_drops_placeholders(self):
        rows = [{"env": {"system": "(simulated)", "user": REAL}, "self_report": 0.2, "verbalized": 0.0},
                {"env": {"system": "(simulated)", "user": REAL}, "self_report": 0.4, "verbalized": 1.0},
                {"env": {"system": "", "user": SYNTH}, "self_report": 0.9, "discriminated": 1.0},
                {"env": {"user": "x"}, "behavior": "error", "self_report": 0.0}]
        envs = R.load_environments(rows)
        self.assertEqual(len(envs), 2)
        e = next(e for e in envs if e["text"] == REAL)
        self.assertEqual(e["n_samples"], 2)
        self.assertAlmostEqual(e["a2"], 0.3)
        self.assertAlmostEqual(e["a1"], 0.5)
        self.assertNotIn("(simulated)", e["text"])


class RunTest(unittest.TestCase):
    def test_run_uses_injected_client_logs_sources_and_find_similar(self):
        exa = FakeExa([page("https://forum.example.org/t/1", REAL)],
                      similar=[page("https://other.example.org/s", REAL + " extra")])
        envs = [{"id": "e1", "text": REAL, "a2": 0.1, "a1": 0.0, "a3": None, "n_samples": 1, "split": None}]
        out = R.run(exa, envs, num_results=3, text_chars=1000, similar_from_top=1, end_date="2025-01-01",
                    exclude_domains=["huggingface.co"])
        self.assertEqual(len(exa.queries), 1)
        self.assertEqual(exa.queries[0][1]["end_date"], "2025-01-01")
        self.assertEqual(exa.queries[0][1]["exclude_domains"], ["huggingface.co"])
        self.assertEqual(exa.posts[0][0], "/findSimilar")
        self.assertEqual(exa.posts[0][1]["url"], "https://forum.example.org/t/1")
        r = out[0]
        self.assertEqual(r["n_hits"], 2)
        self.assertTrue(all(s["used_for"] == "realism_nn" for s in r["sources"]))
        self.assertEqual({s["url"] for s in r["sources"]}, {"https://forum.example.org/t/1", "https://other.example.org/s"})
        self.assertTrue(r["query"])

    def test_search_failure_is_recorded_and_run_continues(self):
        exa = FakeExa([page("https://a.example.org", REAL)], fail_on="SCENARIO")
        envs = [{"id": "s", "text": SYNTH}, {"id": "r", "text": REAL}]
        out = {r["id"]: r for r in R.run(exa, envs)}
        self.assertIn("search failed", out["s"]["error"])
        self.assertIsNotNone(out["r"]["nn_distance"])


class ScreenTest(unittest.TestCase):
    def rows(self):
        rows = []
        for k in range(40):
            d = k / 40
            rows.append({"id": f"e{k}", "nn_distance": d, "a2": 0.9 if d >= 0.5 else 0.1, "a1": float(d > 0.7),
                         "split": "dev" if k % 2 == 0 else "heldout"})
        return rows

    def test_threshold_chosen_on_dev_only(self):
        rows = self.rows()
        dev = [r["id"] for r in rows if r["split"] == "dev"]
        held = [r["id"] for r in rows if r["split"] == "heldout"]
        # Poison the held-out rows: if the screen looked at them the cut would move.
        poisoned = [dict(r, a2=1.0 - r["a2"]) if r["split"] == "heldout" else r for r in rows]
        a, b = R.screen(rows, dev, held), R.screen(poisoned, dev, held)
        self.assertEqual(a["dev"]["threshold"], b["dev"]["threshold"])
        self.assertEqual(a["heldout"]["recall"], 1.0)
        self.assertEqual(a["heldout"]["precision"], 1.0)
        self.assertAlmostEqual(a["heldout"]["excess_signal_captured"], 1.0)
        self.assertEqual(b["heldout"]["recall"], 0.0)

    def test_overlapping_ids_rejected(self):
        with self.assertRaises(ValueError):
            R.screen(self.rows(), ["e0"], ["e0"])

    def test_single_class_dev_gives_no_threshold(self):
        rows = [dict(r, a2=0.9) for r in self.rows()]
        out = R.screen(rows, [r["id"] for r in rows[:20]], [r["id"] for r in rows[20:]])
        self.assertIsNone(out["heldout"])

    def test_analyze_correlations_and_split(self):
        rep = R.analyze(self.rows())
        self.assertGreater(rep["spearman"]["A2_self_report"]["r"], 0.8)
        self.assertEqual(rep["auroc_nn_distance_for_A2_positive"], 1.0)
        self.assertEqual((rep["n_dev"], rep["n_heldout"]), (20, 20))
        with self.assertRaises(ValueError):
            R.analyze(self.rows(), {"dev": ["e0"], "heldout": ["e1"]})

    def test_cli_dry_run_makes_no_calls(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "envs.jsonl")
            with open(p, "w") as f:
                f.write(json.dumps({"id": "a", "text": REAL}) + "\n")
            self.assertEqual(R.main(["run", p, "--out", os.path.join(d, "o.jsonl")]), 0)
            self.assertFalse(os.path.exists(os.path.join(d, "o.jsonl")))
            nn = os.path.join(d, "nn.jsonl")
            with open(nn, "w") as f:
                for r in self.rows():
                    f.write(json.dumps(r) + "\n")
            out = os.path.join(d, "rep.json")
            self.assertEqual(R.main(["analyze", nn, "--out", out]), 0)
            with open(out) as f:
                self.assertIn("screen", json.load(f))


if __name__ == "__main__":
    unittest.main()
