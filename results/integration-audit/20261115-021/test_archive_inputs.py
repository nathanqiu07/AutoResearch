#!/usr/bin/env python3
"""Offline boundary tests for audit021 private replay; synthetic bytes only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("audit21", Path(__file__).with_name("read_handoff.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class ArchiveInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "relocated"
        self.root.mkdir()
        self.raw = b"synthetic reproducible bytes"
        (self.root / "one.json").write_bytes(self.raw)
        self.receipt = self.base / "receipt.json"
        self.row = {"kind": "external", "path": "/nonexistent/audit21/input.json",
                    "archive_member": "one.json", "sha256": hashlib.sha256(self.raw).hexdigest()}

    def reader(self, rows=None, aliases=None):
        self.receipt.write_text(json.dumps({"files": rows if rows is not None else [self.row], "recorded_path_aliases": aliases or {}}))
        return audit.ArchivedInputs(self.root, self.receipt)

    def test_relocated_external_does_not_need_original(self):
        raw, actual = self.reader().read("external", self.row["path"])
        self.assertEqual(raw, self.raw)
        self.assertEqual(actual, (self.root / "one.json").resolve())

    def test_git_short_and_full_pin(self):
        row = dict(self.row, kind="git_object", path="src/file.py", commit="abc1234", full_commit="abc123456789")
        reader = self.reader([row])
        for revision in (row["commit"], row["full_commit"]):
            self.assertEqual(reader.read("git_object", row["path"], revision)[0], self.raw)
        with self.assertRaises(ValueError):
            reader.read("git_object", row["path"], "different")

    def test_unlisted_input_rejected(self):
        with self.assertRaises(ValueError):
            self.reader().read("external", "/nonexistent/audit21/other.json")

    def test_duplicate_pin_rejected(self):
        with self.assertRaises(ValueError):
            self.reader([self.row, self.row]).read("external", self.row["path"])

    def test_modified_bytes_rejected(self):
        (self.root / "one.json").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.reader().read("external", self.row["path"])

    def test_parent_escape_rejected(self):
        self.row["archive_member"] = "../one.json"
        with self.assertRaisesRegex(ValueError, "Invalid archive"):
            self.reader().read("external", self.row["path"])

    def test_absolute_member_rejected(self):
        self.row["archive_member"] = str(self.root / "one.json")
        with self.assertRaisesRegex(ValueError, "Invalid archive"):
            self.reader().read("external", self.row["path"])

    def test_symlink_escape_rejected(self):
        outside = self.base / "outside.json"
        outside.write_bytes(self.raw)
        (self.root / "link.json").symlink_to(outside)
        self.row["archive_member"] = "link.json"
        with self.assertRaises(ValueError):
            self.reader().read("external", self.row["path"])

    def test_recorded_path_is_lexical_even_if_host_has_symlink_loop(self):
        loop = self.base / "loop"
        loop.symlink_to(loop)
        self.row["path"] = str(loop / "original.json")
        self.assertEqual(self.reader().read("external", self.row["path"])[0], self.raw)

    def test_explicit_recorded_alias_needs_no_host_symlink(self):
        alias = "/different-host-mount/input.json"
        reader = self.reader(aliases={alias: self.row["path"]})
        self.assertEqual(reader.read("external", alias)[0], self.raw)

    def test_mutation_after_git_read_rejected_at_finish(self):
        row = dict(self.row, kind="git_object", path="src/file.py", commit="abc", full_commit="abc123")
        reader = self.reader([row])
        reader.read("git_object", row["path"], "abc")
        (self.root / "one.json").write_bytes(b"changed after initial read")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            reader.verify_read_files()

    def test_missing_member_rejected(self):
        self.row["archive_member"] = "missing.json"
        with self.assertRaises(FileNotFoundError):
            self.reader().read("external", self.row["path"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
