"""taste/grill_store: grill sessions and the patched user model round-trip through shared memory."""
import json
import os
import tempfile
import unittest

from autoresearch.integrations.shared_memory import LocalSharedMemory
from autoresearch.taste import grill_store, usermodel_store

TASK = "grill/eval_awareness"


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class GrillStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.a, self.b = os.path.join(self.tmp.name, "a"), os.path.join(self.tmp.name, "b")
        self.mem = LocalSharedMemory(os.path.join(self.tmp.name, "shared.jsonl"))
        _write(os.path.join(self.a, "r", TASK, "meta.json"), '{"task": "eval_awareness"}')
        _write(os.path.join(self.a, "r", TASK, "answers.jsonl"), '{"id": 1}\n{"id": 2}\n')
        _write(os.path.join(self.a, "r", "usermodel.json"), '{"method": "m5"}')

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip_to_a_fresh_machine(self):
        sent = grill_store.push(self.mem, self.a, "r")
        self.assertEqual(len(sent), 3)
        got = grill_store.pull(self.mem, self.b, "r")
        self.assertEqual(sorted(got), sorted(sent))
        for rel in sent:
            with open(os.path.join(self.a, "r", rel)) as x, open(os.path.join(self.b, "r", rel)) as y:
                self.assertEqual(x.read(), y.read())

    def test_push_sends_only_changes(self):
        grill_store.push(self.mem, self.a, "r")
        self.assertEqual(grill_store.push(self.mem, self.a, "r"), [])
        with open(os.path.join(self.a, "r", TASK, "answers.jsonl"), "a") as f:
            f.write('{"id": 3}\n')
        self.assertEqual(grill_store.push(self.mem, self.a, "r"), [f"{TASK}/answers.jsonl"])

    def test_pull_merges_jsonl_and_keeps_local_files(self):
        grill_store.push(self.mem, self.a, "r")
        _write(os.path.join(self.b, "r", TASK, "answers.jsonl"), '{"id": 2}\n{"id": 9}\n')
        _write(os.path.join(self.b, "r", "usermodel.json"), '{"method": "local"}')
        grill_store.pull(self.mem, self.b, "r")
        with open(os.path.join(self.b, "r", TASK, "answers.jsonl")) as f:
            self.assertEqual([json.loads(l)["id"] for l in f], [2, 9, 1])
        with open(os.path.join(self.b, "r", "usermodel.json")) as f:
            self.assertEqual(json.load(f)["method"], "local")

    def test_manifest_cannot_escape_the_researcher_dir(self):
        evil = os.path.join(self.tmp.name, "m.json")
        _write(evil, json.dumps(["../../etc/x", "/abs", "grill/t/answers.jsonl", "grill/t/other.txt"]))
        usermodel_store.push(self.mem, "r/grill-manifest", evil)
        self.assertEqual(grill_store.pull_manifest(self.mem, "r"), ["grill/t/answers.jsonl"])

    def test_other_researcher_sees_nothing(self):
        grill_store.push(self.mem, self.a, "r")
        self.assertEqual(grill_store.pull(self.mem, self.b, "someone"), [])


if __name__ == "__main__":
    unittest.main()
