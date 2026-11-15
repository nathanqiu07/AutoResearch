import copy
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

    def test_default_manifest_preserves_the_original_format_and_digest(self):
        normalize, build, _ = self.api()
        manifest = build([normalize(row(), "arena", "train")])
        self.assertNotIn("deduplication", manifest)
        self.assertEqual(manifest["manifest_id"],
                         "55eff0dc899104df24cf6a838d901994b75b0db49d0b9bdf0da8c4881cb5a094")

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

    def duplicate_pair(self):
        normalize, _, _ = self.api()
        record = normalize(row(), "arena", "train")
        first = replace(record, choice=replace(record.choice, example_id="a-keep", group_id="g-keep"))
        second = replace(first, choice=replace(first.choice, a_text=first.choice.b_text,
                         b_text=first.choice.a_text,
                         chosen="b" if first.choice.chosen == "a" else "a",
                         example_id="z-remove", group_id="g-remove"))
        return first, second

    def test_deduplication_handles_reversed_options_and_exact_occurrences_deterministically(self):
        from autoresearch.taste.prefdata import deduplicate_records
        a, b = self.duplicate_pair()
        unique, audit = deduplicate_records([b, a, a])
        self.assertEqual(unique, [a])
        self.assertEqual((unique, audit), deduplicate_records(iter([a, b, a])))
        self.assertEqual(audit["input_count"], 3)
        self.assertEqual(audit["retained_count"], 1)
        self.assertEqual(audit["removed_count"], 2)
        self.assertEqual(audit["duplicate_group_count"], 1)
        self.assertEqual([entry["kept_id"] for entry in audit["removed"]], ["a-keep", "a-keep"])
        self.assertCountEqual([entry["removed_id"] for entry in audit["removed"]], ["a-keep", "z-remove"])
        self.assertCountEqual([entry["removed_group_id"] for entry in audit["removed"]], ["g-keep", "g-remove"])

    def test_deduplication_does_not_collapse_different_users(self):
        from autoresearch.taste.prefdata import deduplicate_records
        a, _ = self.duplicate_pair()
        other = replace(a, choice=replace(a.choice, user_id="arena:other", example_id="other-id"))
        unique, audit = deduplicate_records([a, other])
        self.assertEqual(len(unique), 2)
        self.assertEqual(audit["removed_count"], 0)

    def test_deduplication_refuses_conflicting_labels_and_any_partition_boundary(self):
        from autoresearch.taste.prefdata import deduplicate_records
        a, b = self.duplicate_pair()
        conflicting = replace(b, choice=replace(b.choice, chosen=a.choice.chosen))
        cases = [conflicting, replace(b, dataset="prism"), replace(b, user_split="test"),
                 replace(b, choice_split="val"), replace(b, upstream_split="validation")]
        for bad in cases:
            with self.subTest(record=bad):
                with self.assertRaises(ValueError):
                    deduplicate_records([a, bad])

    def test_deduplication_does_not_hide_a_removed_conversations_split_leakage(self):
        from autoresearch.taste.prefdata import deduplicate_records
        a, b = self.duplicate_pair()
        unrelated = replace(a, choice_split="val", choice=replace(a.choice, context="other question",
                            example_id="third", group_id=b.choice.group_id))
        with self.assertRaises(ValueError):
            deduplicate_records([a, b, unrelated])

    def test_deduplication_rejects_a_removed_id_reused_for_different_content(self):
        from autoresearch.taste.prefdata import deduplicate_records
        a, b = self.duplicate_pair()
        c = replace(a, choice=replace(a.choice, context="other question", example_id="b-keep"))
        d = replace(c, choice=replace(c.choice, example_id=b.choice.identity))
        with self.assertRaises(ValueError):
            deduplicate_records([a, b, c, d])

    def test_manifest_hashes_audit_and_rejects_bad_counts_or_retained_references(self):
        from autoresearch.taste.prefdata import build_manifest, deduplicate_records
        a, b = self.duplicate_pair()
        unique, audit = deduplicate_records([a, b])
        manifest = build_manifest(unique, deduplication=audit)
        self.assertEqual(manifest["deduplication"], audit)
        self.assertNotEqual(manifest["manifest_id"], build_manifest(unique)["manifest_id"])
        for key in ("input_count", "retained_count", "removed_count", "duplicate_group_count"):
            bad = copy.deepcopy(audit)
            bad[key] += 1
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    build_manifest(unique, deduplication=bad)
        for key, value in (("kept_id", "missing"), ("content_digest", "wrong"),
                           ("choice_split", "test"), ("kept_group_id", "wrong")):
            bad = copy.deepcopy(audit)
            bad["removed"][0][key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    build_manifest(unique, deduplication=bad)

    def test_download_duplicate_opt_in_returns_raw_rows_but_still_validates(self):
        from autoresearch.taste.prefdata import download_dataset
        def fetch(endpoint, params):
            if endpoint == "splits":
                return {"splits": [{"config": "default", "split": "train"}]}
            return {"rows": [{"row": row(), "truncated_cells": []},
                             {"row": row(), "truncated_cells": []}], "num_rows_total": 2}
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                download_dataset("arena", d, fetch=fetch)
            self.assertEqual(len(download_dataset("arena", d, fetch=fetch, allow_duplicates=True)), 2)
        def conflict(endpoint, params):
            result = fetch(endpoint, params)
            if endpoint == "rows":
                result["rows"][1]["row"]["split"] = "val"
            return result
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                download_dataset("arena", d, fetch=conflict, allow_duplicates=True)
