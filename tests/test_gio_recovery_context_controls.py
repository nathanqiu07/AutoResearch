"""Offline controls must preserve exact source exposure at the auditor boundary."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "scripts/gio_recovery/context_controls.py"


def sources():
    return [
        {"source_id": "a", "author": "Researcher", "text": "First paragraph.\n\n終わり 🧪 {seed} e\u0301",
         "provenance": {"url": "https://example.invalid/a"}},
        {"source_id": "b", "author": "Researcher", "text": "Exact duplicate stays.\n\nExact duplicate stays.",
         "provenance": {"url": "https://example.invalid/b"}},
    ]


class ContextControlTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), "missing auditor context control implementation")
        spec = importlib.util.spec_from_file_location("context_controls", MODULE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def build(self, method="raw", docs=None, **kwargs):
        return self.module.build_control(
            sources() if docs is None else docs, method=method,
            researcher_id="fixture-researcher", source_bundle_digest="a" * 64,
            implementation_commit="b" * 40, **kwargs)

    def test_raw_preserves_all_documents_and_late_unicode_exactly(self):
        result = self.build()
        rows = json.loads(result["model_facing_text"].split("\n\n", 1)[1])["source_passages"]
        self.assertEqual([row["text"] for row in rows], [doc["text"] for doc in sources()])
        self.assertTrue(all(row["complete_permitted_coverage"] for row in result["provenance"]["coverage"]))
        exposure = result["exposure"]
        actual = result["model_facing_text"].encode("utf-8")
        self.assertEqual(exposure["utf8_bytes"], len(actual))
        self.assertEqual(exposure["sha256"], hashlib.sha256(actual).hexdigest())
        self.assertIsNone(exposure["tokens"])
        self.assertEqual(exposure["token_count_method"], "unavailable")
        # Petri formats the template once. Braces must round-trip unchanged.
        self.assertEqual(result["auditor_template_suffix"].format(), result["model_facing_text"])

    def test_generic_never_exposes_source_text_or_researcher_identity(self):
        result = self.build("generic")
        self.assertNotIn("First paragraph", result["model_facing_text"])
        self.assertNotIn("fixture-researcher", result["model_facing_text"])
        self.assertEqual(result["provenance"]["selected_passages"], [])
        self.assertTrue(all(row["selected_chars"] == 0 for row in result["provenance"]["coverage"]))

    def test_raw_overflow_fails_instead_of_dropping_tail(self):
        full = self.build()
        size = len(full["model_facing_text"].encode("utf-8"))
        self.assertEqual(self.build(max_utf8_bytes=size)["model_facing_text"], full["model_facing_text"])
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.build(max_utf8_bytes=size - 1)

    def test_retrieval_finds_late_passage_and_reports_omissions(self):
        text = "Unrelated opening.\n\n" * 30 + "Shutdown interruption stop compliance."
        docs = [{"source_id": "late", "author": "R", "text": text, "provenance": {}}]
        result = self.build("retrieved", docs, query="shutdown stop", max_passages=1, max_utf8_bytes=800)
        selected = result["provenance"]["selected_passages"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["text"], "Shutdown interruption stop compliance.")
        self.assertEqual(text[selected[0]["start"]:selected[0]["end"]], selected[0]["text"])
        coverage = result["provenance"]["coverage"][0]
        self.assertFalse(coverage["complete_permitted_coverage"])
        self.assertEqual(coverage["selected_chars"] + coverage["omitted_chars"], len(text))
        self.assertLessEqual(result["exposure"]["utf8_bytes"], 800)

    def test_permissions_preserve_overlaps_and_gaps_without_disclosure(self):
        docs = [{"source_id": "p", "author": "R", "text": "abcdefSECRETxyz",
                 "provenance": {}, "permitted_spans": [{"start": 0, "end": 4},
                     {"start": 2, "end": 6}, {"start": 12, "end": 15}]}]
        result = self.build(docs=docs)
        rows = result["provenance"]["selected_passages"]
        self.assertEqual([row["text"] for row in rows], ["abcdef", "xyz"])
        self.assertNotIn("SECRET", result["model_facing_text"])
        self.assertEqual(result["provenance"]["coverage"][0]["permitted_chars"], 9)
        docs[0]["permitted_spans"] = []
        with self.assertRaisesRegex(ValueError, "no approved"):
            self.build(docs=docs)

    def test_retrieval_is_deterministic_and_query_is_bound(self):
        first = self.build("retrieved", query="no overlap", max_passages=1)
        second = self.build("retrieved", query="no overlap", max_passages=1)
        self.assertEqual(first, second)
        self.assertEqual(first["provenance"]["selected_passages"][0]["source_id"], "a")
        changed = self.build("retrieved", query="Exact duplicate", max_passages=1)
        self.assertNotEqual(first["settings"]["query_sha256"], changed["settings"]["query_sha256"])
        self.assertNotEqual(first["model_facing_text"], changed["model_facing_text"])

    def test_no_fit_retrieval_is_explicit_and_never_slices_paragraph(self):
        docs = [{"source_id": "long", "author": "R", "text": "long " * 500, "provenance": {}}]
        with self.assertRaisesRegex(ValueError, "no complete passage"):
            self.build("retrieved", docs, query="long", max_utf8_bytes=500)
        with self.assertRaises(ValueError):
            self.build("generic", max_utf8_bytes=1)

    def test_crlf_retrieval_reaches_late_paragraph_without_normalization(self):
        tail = "Shutdown interruption.\r\n"
        text = "Opening " * 200 + "\r\n\r\n" + tail
        docs = [{"source_id": "crlf", "author": "R", "text": text, "provenance": {}}]
        result = self.build("retrieved", docs, query="shutdown", max_utf8_bytes=500, max_passages=1)
        selected = result["provenance"]["selected_passages"][0]
        self.assertEqual(selected["text"], tail)
        self.assertEqual(text[selected["start"]:selected["end"]], tail)

    def test_invalid_source_identity_and_permission_are_rejected(self):
        duplicate = sources() + [copy.deepcopy(sources()[0])]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.build(docs=duplicate)
        bad = sources()
        bad[0]["permitted_spans"] = [{"start": -1, "end": 4}]
        with self.assertRaisesRegex(ValueError, "permitted"):
            self.build(docs=bad)

    def bundle_fixture(self, directory):
        records = sources()
        for record in records:
            record["researcher_id"] = "fixture-researcher"
            record["author"] = "fixture-researcher"
            record["provenance"].update({"role": "fit", "source_review_disposition": "approved_atemporal",
                "text_sha256": hashlib.sha256(record["text"].encode()).hexdigest(),
                "permitted_spans": [{"start": 0, "end": len(record["text"]), "speaker": "fixture-researcher"}]})
        bundle = {"schema_version": "gio-source-bundle-v1", "sources": records,
                  "researchers": ["fixture-researcher"]}
        canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        bundle["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        path = Path(directory) / "bundle.json"
        path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_bundle_loader_pins_file_bytes_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path, expected = self.bundle_fixture(directory)
            rows, digest = self.module.load_sources(path, "fixture-researcher", expected)
            self.assertEqual(digest, expected)
            self.assertEqual([row["text"] for row in rows], [row["text"] for row in sources()])
            path.write_text(path.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "file SHA256"):
                self.module.load_sources(path, "fixture-researcher", expected)

    def morning_bundle_fixture(self, directory, *, scope="morning_petri_only"):
        path, _ = self.bundle_fixture(directory)
        bundle = json.loads(path.read_text())
        bundle["protocol_version"] = "morning-petri-new-source-condition-v2"
        for record in bundle["sources"]:
            record["authors"] = ["Fixture researcher", "Collaborator"]
            record["provenance"].update({"source_review_disposition": "approved_morning_petri_public_original",
                                         "fit_scope": scope,
                                         "attribution_basis": "Collaborative position, not individual testimony."})
        first = bundle["sources"][0]
        first["text"] = "Left.OTHER SPEECHRight."
        first["provenance"]["text_sha256"] = hashlib.sha256(first["text"].encode()).hexdigest()
        first["provenance"]["permitted_spans"] = [
            {"start": 0, "end": 5, "speaker": "fixture-researcher"},
            {"start": 17, "end": 23, "speaker": "fixture-researcher"}]
        bundle.pop("digest_sha256")
        canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        bundle["digest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_morning_sources_exclude_other_speaker_and_preserve_coauthorship(self):
        with tempfile.TemporaryDirectory() as directory:
            path, expected = self.morning_bundle_fixture(directory)
            docs, _ = self.module.load_sources(path, "fixture-researcher", expected)
            result = self.build(docs=docs)
            self.assertNotIn("OTHER SPEECH", result["model_facing_text"])
            rows = result["provenance"]["selected_passages"]
            self.assertEqual([r["text"] for r in rows if r["source_id"] == "a"], ["Left.", "Right."])
            self.assertIn("Collaborative position, not individual testimony.", result["model_facing_text"])
            self.assertIn("Collaborator", result["model_facing_text"])
            payload = json.loads(result["model_facing_text"].split("\n\n", 1)[1])
            self.assertEqual(len(payload["source_attribution"]), 2)
            self.assertTrue(all("attribution" not in row for row in payload["source_passages"]))
            coverage = result["provenance"]["coverage"][0]
            self.assertEqual(coverage["unapproved_chars"], 12)
            self.assertEqual(coverage["unapproved_intervals"], [[5, 17]])
            self.assertEqual(coverage["selected_chars"], 11)
            self.assertEqual(coverage["omitted_chars"], 0)

    def test_new_source_disposition_requires_exact_morning_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            path, expected = self.morning_bundle_fixture(directory, scope="old_heldout")
            with self.assertRaisesRegex(ValueError, "scope"):
                self.module.load_sources(path, "fixture-researcher", expected)

    def test_explicit_larger_raw_cap_keeps_all_large_source_bytes(self):
        docs = [{"source_id": "long", "author": "R", "text": "Long source. " * 3000,
                 "provenance": {}}]
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.build(docs=docs, max_utf8_bytes=32768)
        result = self.build(docs=docs, max_utf8_bytes=65536)
        self.assertEqual(result["provenance"]["selected_passages"][0]["text"], docs[0]["text"])
        self.assertGreater(result["exposure"]["utf8_bytes"], 32768)

    def test_cli_exports_three_handoffs_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path, expected = self.bundle_fixture(directory)
            output = Path(directory) / "controls"
            command = [sys.executable, str(MODULE), "--bundle", str(path), "--bundle-sha256", expected,
                       "--researcher", "fixture-researcher", "--query", "late experiment",
                       "--implementation-commit", "b" * 40, "--out", str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(sorted(p.name for p in output.glob("*.context.json")),
                             ["generic.context.json", "raw.context.json", "retrieved.context.json"])
            raw = json.loads((output / "raw.context.json").read_text())
            self.assertEqual(raw["source_bundle_digest"], expected)
            self.assertEqual(hashlib.sha256((output / "source-bundle.json").read_bytes()).hexdigest(), expected)
            self.assertTrue((output / "CONTROL_RECEIPT.json").exists())
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)

    def test_export_rejects_bundle_changed_after_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path, expected = self.bundle_fixture(directory)
            output = Path(directory) / "controls"
            original_read = Path.read_bytes
            bundle_reads = []

            def changing_read(file_path):
                raw = original_read(file_path)
                if file_path == path:
                    bundle_reads.append(True)
                    if len(bundle_reads) > 1:
                        return raw + b" "
                return raw

            argv = ["--bundle", str(path), "--bundle-sha256", expected,
                    "--researcher", "fixture-researcher", "--query", "late experiment",
                    "--implementation-commit", "b" * 40, "--out", str(output)]
            with patch.object(Path, "read_bytes", changing_read):
                with self.assertRaisesRegex(ValueError, "changed"):
                    self.module.main(argv)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
