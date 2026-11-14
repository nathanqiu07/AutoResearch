"""WS B: user models kept in shared memory (past.dev when PAST_API_KEY is set)."""
import json
import os
import tempfile
import unittest

from autoresearch.integrations.shared_memory import LocalSharedMemory, SharedMemory
from autoresearch.llm import OfflineLLM
from autoresearch.taste import usermodel_store as store
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import load_model


class PastDevLikeMemory(SharedMemory):
    """What PastDevMemory.recall hands back: each fact prefixed with its author,
    and excerpts that repeat only part of a fact."""

    def __init__(self):
        self.rows = []

    def write(self, agent, content, label="", metadata=None):
        self.rows.append(f"[author={agent}] {content}")

    def recall(self, agent, query, limit=50):
        out = []
        for content in self.rows:
            out.append({"author": agent, "content": content[:len(content) // 2]})
            out.append({"author": agent, "content": content})
        return out[:limit]


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def read_text(path):
    with open(path) as f:
        return f.read()


class UserModelStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.shared = LocalSharedMemory(os.path.join(self.tmp, "shared.jsonl"))

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)

    def test_pulled_model_loads_like_the_saved_one(self):
        llm = OfflineLLM()
        model = create_method("m0", llm, seed=0)
        model.fit([], [])
        model.save(self.path("a", "alice", "usermodel.json"))

        store.push(self.shared, "alice", self.path("a", "alice", "usermodel.json"))
        sha = store.pull(self.shared, "alice", self.path("b", "alice", "usermodel.json"))

        self.assertIsNotNone(sha)
        self.assertEqual(read_text(self.path("b", "alice", "usermodel.json")),
                         read_text(self.path("a", "alice", "usermodel.json")))
        self.assertEqual(load_model(self.path("b", "alice", "usermodel.json"), llm).method_id, "m0")

    def test_large_model_round_trips_byte_for_byte(self):
        body = json.dumps({"persona": "line one\n  indented, trailing spaces   \n" * 600}, indent=2) + "\n"
        write_text(self.path("a.json"), body)

        store.push(self.shared, "alice", self.path("a.json"))
        store.pull(self.shared, "alice", self.path("b.json"))

        self.assertEqual(read_text(self.path("b.json")), body)

    def test_pull_returns_the_newest_version(self):
        write_text(self.path("v1.json"), '{"version": 1}\n')
        write_text(self.path("v2.json"), '{"version": 2}\n')
        store.push(self.shared, "alice", self.path("v1.json"))
        store.push(self.shared, "alice", self.path("v2.json"))

        store.pull(self.shared, "alice", self.path("out.json"))

        self.assertEqual(read_text(self.path("out.json")), '{"version": 2}\n')

    def test_an_altered_copy_is_never_restored(self):
        write_text(self.path("v1.json"), '{"version": 1}\n')
        write_text(self.path("v2.json"), '{"version": 2}\n')
        store.push(self.shared, "alice", self.path("v1.json"))
        store.push(self.shared, "alice", self.path("v2.json"))
        rows = [json.loads(line) for line in read_text(self.shared.path).splitlines()]
        rows[-1]["content"] = rows[-1]["content"][:-4] + "AAAA"   # damage the newest version
        write_text(self.shared.path, "".join(json.dumps(r) + "\n" for r in rows))

        store.pull(self.shared, "alice", self.path("out.json"))

        self.assertEqual(read_text(self.path("out.json")), '{"version": 1}\n')

    def test_nothing_is_written_when_memory_has_no_intact_copy(self):
        self.assertIsNone(store.pull(self.shared, "alice", self.path("out.json")))
        self.assertFalse(os.path.exists(self.path("out.json")))

    def test_another_researchers_model_is_never_returned(self):
        write_text(self.path("alice.json"), '{"who": "alice"}\n')
        write_text(self.path("bob.json"), '{"who": "bob"}\n')
        store.push(self.shared, "bob", self.path("bob.json"))
        store.push(self.shared, "alice", self.path("alice.json"))

        store.pull(self.shared, "bob", self.path("out.json"))

        self.assertEqual(read_text(self.path("out.json")), '{"who": "bob"}\n')

    def test_pastdev_style_recall_with_author_prefix_and_excerpts(self):
        shared = PastDevLikeMemory()
        body = json.dumps({"principles": ["prefer realistic stakes"] * 300}, indent=2) + "\n"
        write_text(self.path("a.json"), body)

        store.push(shared, "alice", self.path("a.json"))
        store.pull(shared, "alice", self.path("b.json"))

        self.assertEqual(read_text(self.path("b.json")), body)


if __name__ == "__main__":
    unittest.main()
