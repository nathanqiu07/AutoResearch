import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


def row(user="u", group="g", split="train"):
    return {"user_id": user, "conversation_id": group, "split": split,
            "context": [{"role": "user", "content": "question " + group}],
            "chosen": {"role": "assistant", "content": "preferred"},
            "rejected": {"role": "assistant", "content": "other"},
            "reasoning_judge": "LEAK", "agreement": 1.0}


class PreferenceDataTests(unittest.TestCase):
    def api(self):
        from autoresearch.taste.prefdata import normalize_row, build_manifest, write_manifest
        return normalize_row, build_manifest, write_manifest

    def test_normalizes_without_judge_metadata_and_randomizes_labels(self):
        normalize, _, _ = self.api()
        records = [normalize(row(group=str(i)), "arena", "train", seed=3) for i in range(20)]
        self.assertEqual({r.choice.chosen for r in records}, {"a", "b"})
        for record in records:
            c = record.choice
            self.assertEqual(c.a_text if c.chosen == "a" else c.b_text, "preferred")
            self.assertNotIn("LEAK", str(c))
            self.assertEqual(record.user_split, "dev")
            self.assertEqual(record.choice_split, "history")
        self.assertEqual(records[0], normalize(row(group="0"), "arena", "train", seed=3))

    def test_preserves_two_levels_of_partitions(self):
        normalize, build, _ = self.api()
        records = [normalize(row("dev", "d1"), "arena", "validation"),
                   normalize(row("test", "t1"), "arena", "test"),
                   normalize(row("test", "t2", "test"), "arena", "test")]
        m = build(records)
        self.assertEqual(m["users"]["arena:dev"]["partition"], "dev")
        self.assertEqual(m["users"]["arena:test"]["partition"], "test")
        self.assertEqual(len(m["users"]["arena:test"]["history"]), 1)
        self.assertEqual(len(m["users"]["arena:test"]["test"]), 1)

    def test_rejects_user_group_and_duplicate_leakage(self):
        normalize, build, _ = self.api()
        a = normalize(row(), "arena", "train")
        for bad in (replace(a, user_split="test"), replace(a, choice_split="test"), a):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    build([a, bad])
        b = normalize(row(group="other"), "arena", "test")
        with self.assertRaises(ValueError):
            build([a, b])

    def test_unknown_split_and_null_options_fail(self):
        normalize, _, _ = self.api()
        with self.assertRaises(ValueError):
            normalize(row(split="unknown"), "arena", "train")
        r = row()
        r["chosen"]["content"] = None
        with self.assertRaises(ValueError):
            normalize(r, "arena", "train")

    def test_manifest_is_order_independent_and_immutable(self):
        normalize, build, write = self.api()
        records = [normalize(row(group=str(i)), "arena", "train") for i in range(3)]
        m = build(records)
        self.assertEqual(m, build(list(reversed(records))))
        self.assertEqual(m, build(iter(records)))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "splits.json"
            write(path, m)
            write(path, m)
            with self.assertRaises(ValueError):
                write(path, build(records[:2]))

    def test_download_preserves_partitions_and_rejects_truncated_pages(self):
        from autoresearch.taste.prefdata import download_dataset
        def fetch(endpoint, params):
            if endpoint == "splits":
                return {"splits": [{"config": "default", "split": "train"}]}
            return {"rows": [{"row": row(), "truncated_cells": []}], "num_rows_total": 1}
        with tempfile.TemporaryDirectory() as d:
            records = download_dataset("arena", d, fetch=fetch)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].choice_split, "history")
        def truncated(endpoint, params):
            result = fetch(endpoint, params)
            if endpoint == "rows":
                result["rows"][0]["truncated_cells"] = ["context"]
            return result
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                download_dataset("arena", d, fetch=truncated)
