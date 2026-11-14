import json
import os
import tempfile
import unittest

from autoresearch.research.corpus import (TOPIC_TAGS, fetch_hf_rows_by_topic, load_corpus, load_corpus_records,
                                          matched_pool, topic_tags)

CODE = "my python function {} throws an error when I call it twice"
POEM = "write a poem about autumn leaves and rain number {}"


def write_jsonl(d, name, rows):
    with open(os.path.join(d, name), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class TaggerTests(unittest.TestCase):
    def test_clear_examples_get_their_topic(self):
        self.assertIn("coding", topic_tags("```python\nprint(1)\n``` why does this crash"))
        self.assertIn("creative", topic_tags("write a poem about the sea"))
        self.assertIn("health", topic_tags("what are the symptoms of the flu"))
        self.assertIn("legal_finance", topic_tags("can my landlord break the contract"))

    def test_multi_label_when_two_topics_hit(self):
        tags = topic_tags("write a python script to plot the sales data in a csv")
        self.assertIn("coding", tags)
        self.assertIn("data_analysis", tags)

    def test_other_when_nothing_matches(self):
        self.assertEqual(topic_tags("hello there"), ["other"])
        self.assertEqual(topic_tags(""), ["other"])

    def test_tags_are_deterministic_and_in_taxonomy(self):
        text = "debug my python code and rewrite the essay"
        self.assertEqual(topic_tags(text), topic_tags(text))
        self.assertTrue(set(topic_tags(text)) <= set(TOPIC_TAGS))


class RecordTests(unittest.TestCase):
    def test_records_default_to_heuristic_tags_and_file_stem(self):
        d = tempfile.mkdtemp()
        write_jsonl(d, "mine.jsonl", [{"text": CODE.format(1)}])
        (r,) = load_corpus_records(d)
        self.assertEqual(r["source"], "mine")
        self.assertIn("coding", r["topics"])

    def test_records_honour_pretagged_topics_and_source(self):
        d = tempfile.mkdtemp()
        write_jsonl(d, "tagged.jsonl", [{"text": CODE.format(1), "topics": ["health"], "source": "exa"}])
        (r,) = load_corpus_records(d)
        self.assertEqual(r["topics"], ["health"])
        self.assertEqual(r["source"], "exa")

    def test_bad_topics_field_names_file_and_value(self):
        d = tempfile.mkdtemp()
        write_jsonl(d, "bad.jsonl", [{"text": CODE.format(1), "topics": "coding"}])
        with self.assertRaises(ValueError) as cm:
            load_corpus_records(d)
        self.assertIn("bad.jsonl:1", str(cm.exception))
        self.assertIn("'coding'", str(cm.exception))

    def test_load_corpus_still_returns_plain_text_and_applies_length_filter(self):
        d = tempfile.mkdtemp()
        write_jsonl(d, "c.jsonl", [{"text": CODE.format(1), "topics": ["coding"]}, {"text": "too short"}])
        self.assertEqual(load_corpus(d), [CODE.format(1)])


def records(n_code, n_poem):
    return ([{"text": CODE.format(i), "topics": ["coding"], "source": "a"} for i in range(n_code)] +
            [{"text": POEM.format(i), "topics": ["creative"], "source": "a"} for i in range(n_poem)])


class MatchedPoolTests(unittest.TestCase):
    def test_returns_only_same_topic_messages_when_enough_exist(self):
        pool, info = matched_pool(records(20, 20), "fix this python function, it throws an error")
        self.assertEqual(len(pool), 20)
        self.assertTrue(all("python" in t for t in pool))
        self.assertFalse(info["fallback"])
        self.assertEqual((info["n_matched"], info["n_total"]), (20, 40))
        self.assertIn("coding", info["topics"])

    def test_accepts_explicit_topic_list(self):
        pool, info = matched_pool(records(20, 20), ["creative"])
        self.assertEqual(len(pool), 20)
        self.assertEqual(info["topics"], ["creative"])

    def test_falls_back_to_whole_pool_with_explicit_flag_when_too_few_match(self):
        pool, info = matched_pool(records(20, 5), ["creative"])
        self.assertEqual(len(pool), 25)
        self.assertTrue(info["fallback"])
        self.assertEqual(info["n_matched"], 5)

    def test_length_band_keeps_messages_near_item_length(self):
        recs = ([{"text": "x" * 100, "topics": ["coding"], "source": "a"} for _ in range(20)] +
                [{"text": "y" * 2000, "topics": ["coding"], "source": "a"} for _ in range(20)])
        pool, info = matched_pool(recs, ["coding"], user_text="z" * 120, length_band=3.0)
        self.assertEqual(len(pool), 20)
        self.assertTrue(all(t.startswith("x") for t in pool))
        self.assertTrue(info["length_matched"])

    def test_length_band_skipped_when_it_would_leave_too_few(self):
        recs = ([{"text": "x" * 100, "topics": ["coding"], "source": "a"} for _ in range(3)] +
                [{"text": "y" * 2000, "topics": ["coding"], "source": "a"} for _ in range(20)])
        pool, info = matched_pool(recs, ["coding"], user_text="z" * 120, length_band=3.0)
        self.assertEqual(len(pool), 23)
        self.assertFalse(info["length_matched"])

    def test_length_band_without_user_text_is_rejected(self):
        with self.assertRaises(ValueError):
            matched_pool(records(20, 0), ["coding"], length_band=3.0)


class FetchByTopicTests(unittest.TestCase):
    def fake_pages(self, calls):
        def fetch_page(dataset, config, split, offset, length):
            calls.append((offset, length))
            rows = []
            for i in range(offset, offset + length):
                text = CODE.format(i) if i % 4 else POEM.format(i)
                rows.append({"row": {"msg": text}})
            return rows
        return fetch_page

    def test_stops_once_every_topic_has_enough_and_balances_topics(self):
        d, calls = tempfile.mkdtemp(), []
        path, counts = fetch_hf_rows_by_topic("ds", "default", "train", ["coding", "creative"], 10,
                                              lambda row: row["msg"], root=d, name="t", max_rows=1000,
                                              fetch_page=self.fake_pages(calls))
        self.assertEqual(counts, {"coding": 10, "creative": 10})
        self.assertEqual(len(calls), 1)  # satisfied within the first page, so no further fetch
        lines = [json.loads(x) for x in open(path)]
        self.assertEqual(len(lines), 20)
        self.assertEqual(set(lines[0]), {"text", "topics", "source"})
        self.assertEqual(sum("creative" in x["topics"] for x in lines), 10)

    def test_stops_at_row_cap_when_a_topic_never_fills(self):
        d, calls = tempfile.mkdtemp(), []
        path, counts = fetch_hf_rows_by_topic("ds", "default", "train", ["coding", "health"], 5,
                                              lambda row: row["msg"], root=d, name="t", max_rows=250,
                                              fetch_page=self.fake_pages(calls))
        self.assertEqual(counts["health"], 0)
        self.assertEqual(counts["coding"], 5)
        self.assertEqual(sum(length for _, length in calls), 250)

    def test_unknown_topic_is_rejected_by_name(self):
        with self.assertRaises(ValueError) as cm:
            fetch_hf_rows_by_topic("ds", "default", "train", ["astrology"], 5, lambda r: "", root=tempfile.mkdtemp(),
                                   fetch_page=lambda *a: [])
        self.assertIn("astrology", str(cm.exception))


if __name__ == "__main__":
    unittest.main()


class ScenarioPoolTests(unittest.TestCase):
    def _records(self):
        return ([{"text": CODE.format(i), "topics": ["coding"], "source": "t"} for i in range(20)] +
                [{"text": POEM.format(i), "topics": ["creative"], "source": "t"} for i in range(20)])

    def test_benchmark_item_gets_messages_on_its_own_topic(self):
        from autoresearch.research.benchmarks import item_to_scenario
        from autoresearch.research.corpus import scenario_pool
        sc = item_to_scenario({"id": "a", "user": "please review this python script, it has a bug"})
        pool, info = scenario_pool(sc, self._records())
        self.assertEqual((len(pool), info["fallback"]), (20, False))
        self.assertTrue(all("python" in t for t in pool))

    def test_hand_written_scenario_keeps_its_keyword_regex_and_flags_fallback(self):
        from autoresearch.research.corpus import scenario_pool
        from autoresearch.research.measure import METRIC_INFLATION, SYCOPHANCY_CODE
        pool, info = scenario_pool(SYCOPHANCY_CODE, self._records())
        self.assertEqual((len(pool), info["fallback"]), (20, False))
        pool, info = scenario_pool(METRIC_INFLATION, self._records())   # no data/report messages in this pool
        self.assertEqual((len(pool), info["fallback"]), (40, True))
