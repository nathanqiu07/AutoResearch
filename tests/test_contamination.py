"""Benchmark contamination: distinctive spans, n-gram / LCS overlap and labels, Exa through an
injected fake (no network), and the contaminated-vs-clean detection comparison."""
import json
import os
import tempfile
import unittest

from autoresearch.research import contamination as C

TEMPLATE = "You are a helpful assistant working for the operations team and you must answer carefully. "
ITEM_A = TEMPLATE + ("The quarterly reconciliation for the Lisbon warehouse shows forty seven missing pallets of "
                     "ceramic tiles that were last scanned at the loading dock near gate nine on a rainy Tuesday.")
ITEM_B = TEMPLATE + ("Draft a reply to the landlord about the broken radiator in flat 3B which has leaked brown "
                     "water onto the parquet floor every night since the boiler service in early March.")
ITEM_C = TEMPLATE + "Summarise the attached minutes."


def items():
    return [{"id": "a", "benchmark": "t", "text": ITEM_A, "meta": {"label": "safety"}},
            {"id": "b", "benchmark": "t", "text": ITEM_B, "meta": {"label": "capability"}},
            {"id": "c", "benchmark": "t", "text": ITEM_C, "meta": {"label": "capability"}}]


class FakeExa:
    def __init__(self, pages_for):
        self.pages_for, self.queries = pages_for, []

    def search(self, query, num_results=5, text_chars=0, **kw):
        self.queries.append((query, kw))
        for needle, pages in self.pages_for.items():
            if needle in query:
                return [dict(p) for p in pages]
        return []


class SpanTest(unittest.TestCase):
    def test_spans_skip_shared_template_text(self):
        spans = C.distinctive_spans(items(), n_spans=2, min_words=8, max_words=20)
        for s in spans["a"] + spans["b"]:
            self.assertNotIn("helpful assistant working", s)
        self.assertTrue(any("Lisbon" in s or "pallets" in s for s in spans["a"]))
        self.assertTrue(all(len(s.split()) <= 20 for s in spans["a"]))

    def test_short_item_falls_back_to_its_opening(self):
        spans = C.distinctive_spans([{"id": "x", "benchmark": "t", "text": "Too short.", "meta": {}}])
        self.assertEqual(spans["x"], ["Too short."])

    def test_query_is_quoted(self):
        self.assertEqual(C.span_query('say "hi"  now'), '"say hi now"')


class OverlapTest(unittest.TestCase):
    def test_exact_near_none(self):
        ov = C.overlap(ITEM_A, "Forum post: " + ITEM_A + " Thanks!")
        self.assertEqual(ov["ng13"], 1.0)
        self.assertEqual(C.label(ov), "exact")
        half = " ".join(ITEM_A.split()[:12])
        near = C.overlap(ITEM_A, "quote: " + " ".join(ITEM_A.split()[14:30]) + " end " + half)
        self.assertEqual(C.label(near), "near")
        self.assertEqual(C.label(C.overlap(ITEM_A, ITEM_B[len(TEMPLATE):])), "none")
        self.assertEqual(C.label(None), "none")

    def test_short_item_has_no_13grams(self):
        ov = C.overlap("one two three", "one two three four")
        self.assertIsNone(ov["ng13"])
        self.assertEqual(ov["lcs"], 1.0)

    def test_custom_rules(self):
        ov = C.overlap(ITEM_A, ITEM_A)
        self.assertEqual(C.label(ov, {"exact_ng13": 1.1, "exact_lcs": 1.1}), "near")


class RunTest(unittest.TestCase):
    def test_run_with_fake_exa(self):
        exa = FakeExa({"Lisbon": [{"url": "https://huggingface.co/datasets/x/viewer", "title": "x",
                                   "publishedDate": "2025-02-01", "text": "row 17: " + ITEM_A}],
                       "radiator": [{"url": "https://blog.example.org/flat", "title": "flat",
                                     "publishedDate": None, "text": "My radiator leaked. " + ITEM_B[-60:]}]})
        out = {r["id"]: r for r in C.run(exa, items(), n_spans=2, end_date="2025-06-01", num_results=3)}
        self.assertEqual(out["a"]["contamination"], "exact")
        self.assertEqual(out["a"]["evidence_url"], "https://huggingface.co/datasets/x/viewer")
        self.assertTrue(out["a"]["benchmark_host"])
        self.assertEqual(out["a"]["evidence_date"], "2025-02-01")
        self.assertEqual(out["c"]["contamination"], "none")
        self.assertIsNone(out["c"]["evidence_url"])
        self.assertTrue(all(kw.get("end_date") == "2025-06-01" for _, kw in exa.queries))
        self.assertTrue(all(q.startswith('"') for q, _ in exa.queries))
        self.assertTrue(all(s["used_for"] == "contamination" for s in out["a"]["sources"]))
        self.assertEqual(out["a"]["topic"], "safety")
        cov = C.covariates(list(out.values()))
        self.assertEqual(set(cov[0]), set(C.COVARIATE_FIELDS))
        self.assertTrue(next(c for c in cov if c["id"] == "a")["contaminated"])

    def test_search_error_is_recorded(self):
        class Broken:
            def search(self, *a, **k):
                raise RuntimeError("HTTP 429")
        r = C.check_item(Broken(), items()[0], ["some span"])
        self.assertEqual(r["contamination"], "none")
        self.assertIn("429", r["error"])

    def test_load_petri_and_items_formats(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "seeds.jsonl")
            with open(p, "w") as f:
                f.write(json.dumps({"seed_id": "v2_seed_1", "text": ITEM_A, "variant": "v2"}) + "\n")
            got = C.load_benchmark_items(p)
            self.assertEqual((got[0]["id"], got[0]["benchmark"]), ("v2_seed_1", "petri_v2"))
            q = os.path.join(d, "items.jsonl")
            with open(q, "w") as f:
                f.write(json.dumps({"id": "t1_safety", "user": ITEM_B, "meta": {"label": "safety",
                                                                                 "dataset": "EvalAwareBench"}}) + "\n")
            got = C.load_benchmark_items(q)
            self.assertEqual((got[0]["id"], got[0]["benchmark"]), ("t1_safety", "EvalAwareBench"))
            self.assertEqual(C.item_topics(got), {"t1_safety": "safety"})


class AnalysisTest(unittest.TestCase):
    def results(self):
        out = []
        for k in range(40):
            cont = k < 20
            out.append({"id": f"i{k}", "contamination": ("exact" if k % 2 else "near") if cont else "none",
                        "topic": "safety" if k % 4 < 2 else "capability", "error": None})
        return out

    def test_two_proportion_and_adjusted(self):
        res = self.results()
        detected = {r["id"]: (int(r["id"][1:]) % 10 < 8) if r["contamination"] != "none"
                    else (int(r["id"][1:]) % 10 < 3) for r in res}
        rep = C.analyze(res, detected)
        self.assertAlmostEqual(rep["contaminated"]["detection_rate"], 0.8)
        self.assertAlmostEqual(rep["clean"]["detection_rate"], 0.3)
        t = rep["two_proportion"]
        self.assertAlmostEqual(t["diff"], 0.5)
        self.assertLess(t["p_value"], 0.01)
        lo, hi = rep["diff_bootstrap_ci"]
        self.assertTrue(lo < 0.5 < hi and lo > 0)
        self.assertGreater(rep["adjusted"]["odds_ratio"], 1.0)
        self.assertLess(rep["adjusted"]["or_ci"][0], rep["adjusted"]["odds_ratio"])
        self.assertGreater(rep["mantel_haenszel_or"], 1.0)
        self.assertEqual(set(rep["by_topic"]), {"safety", "capability"})

    def test_two_proportion_known_value(self):
        t = C.two_proportion(30, 50, 20, 50)
        self.assertAlmostEqual(t["z"], 2.0, places=6)
        self.assertAlmostEqual(t["p_value"], 0.0455, places=3)
        self.assertAlmostEqual(C._z_for(0.95), 1.95996, places=4)

    def test_logistic_recovers_coefficient(self):
        X, y = [], []
        for x in (0.0, 1.0):
            p = 0.25 if x == 0 else 0.75      # log-odds -1.0986 and +1.0986
            for k in range(400):
                X.append([1.0, x])
                y.append(1.0 if k < 400 * p else 0.0)
        fit = C.logistic(X, y, ridge=0.0)
        self.assertAlmostEqual(fit["coef"][0], -1.0986, places=3)
        self.assertAlmostEqual(fit["coef"][1], 2.1972, places=3)

    def test_detection_from_scores(self):
        scores = [{"id": "a", "self_report": 0.9}, {"id": "a", "self_report": 0.3},
                  {"seed_id": "b", "self_report": 0.2}, {"id": "c", "behavior": "error", "self_report": 1.0},
                  {"item_id": "d", "aware": True}]
        det, used = C.detection_from_scores(scores, signal="self_report")
        self.assertEqual(det, {"a": True, "b": False})
        self.assertEqual(used, "self_report")
        det, used = C.detection_from_scores([{"item_id": "d", "aware": True}])
        self.assertEqual((det, used), ({"d": True}, "aware"))

    def test_no_topics_gives_no_adjusted(self):
        res = [dict(r, topic=None) for r in self.results()]
        rep = C.analyze(res, {r["id"]: True for r in res})
        self.assertIsNone(rep["adjusted"])

    def test_cli_dry_run_and_analyze(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "seeds.jsonl")
            with open(p, "w") as f:
                f.write(json.dumps({"seed_id": "s1", "text": ITEM_A}) + "\n")
            self.assertEqual(C.main(["run", p, "--out", os.path.join(d, "o.jsonl")]), 0)
            self.assertFalse(os.path.exists(os.path.join(d, "o.jsonl")))
            res = os.path.join(d, "res.jsonl")
            sc = os.path.join(d, "scores.jsonl")
            with open(res, "w") as f, open(sc, "w") as g:
                for r in self.results():
                    f.write(json.dumps(r) + "\n")
                    g.write(json.dumps({"id": r["id"], "self_report": 0.9 if r["contamination"] != "none" else 0.1}) + "\n")
            out, cov = os.path.join(d, "rep.json"), os.path.join(d, "cov.jsonl")
            self.assertEqual(C.main(["analyze", res, "--scores", sc, "--covariates", cov, "--out", out]), 0)
            with open(out) as f:
                rep = json.load(f)
            self.assertEqual(rep["contaminated"]["detection_rate"], 1.0)
            with open(cov) as f:
                self.assertEqual(len(f.read().splitlines()), 40)


if __name__ == "__main__":
    unittest.main()
