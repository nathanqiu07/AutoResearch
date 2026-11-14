import importlib.util
import os
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "agentctl", os.path.join(os.path.dirname(__file__), "..", "scripts", "agentctl.py"))
agentctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agentctl)


class AgentCtlTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def ctl(self, name):
        with mock.patch.dict(os.environ, {"AGENT_NAME": name}):
            return agentctl.Ctl(self.root, use_git=False)

    def as_(self, name, fn, *a, **kw):
        with mock.patch.dict(os.environ, {"AGENT_NAME": name}):
            return fn(agentctl.Ctl(self.root, use_git=False), *a, **kw)

    def test_claim_exclusive_and_done(self):
        self.as_("alice", agentctl.Ctl.task_add, "t1", "Task one")
        self.as_("alice", agentctl.Ctl.claim, "t1")
        with self.assertRaises(SystemExit):
            self.as_("bob", agentctl.Ctl.claim, "t1")
        self.as_("alice", agentctl.Ctl.release, "t1", done=True, summary="did it")
        t = self.as_("bob", agentctl.Ctl.tasks)[0]
        self.assertEqual(t["status"], "done")
        self.assertEqual(t["summary"], "did it")

    def test_stale_claim_can_be_taken(self):
        self.as_("alice", agentctl.Ctl.task_add, "t2", "Task two")
        self.as_("alice", agentctl.Ctl.claim, "t2")
        old = agentctl.iso(agentctl.now() - agentctl.dt.timedelta(hours=3))
        c = agentctl.Ctl(self.root, use_git=False)
        rec = c._read_json("claims/t2.json"); rec["heartbeat"] = old; c._write_json("claims/t2.json", rec)
        self.as_("bob", agentctl.Ctl.claim, "t2")
        self.assertEqual(c._read_json("claims/t2.json")["agent"], "bob")

    def test_overlapping_locks(self):
        self.as_("alice", agentctl.Ctl.lock, ["autoresearch/loop.py"], "editing loop")
        with self.assertRaises(SystemExit):
            self.as_("bob", agentctl.Ctl.lock, ["autoresearch"], "refactor")
        self.as_("bob", agentctl.Ctl.lock, ["autoresearch/tasks"], "new task")
        self.as_("alice", agentctl.Ctl.unlock, ["autoresearch/loop.py"])
        self.as_("bob", agentctl.Ctl.lock, ["autoresearch/loop.py"])

    def test_messages_and_read_tracking(self):
        self.as_("alice", agentctl.Ctl.post, "hi", "body", to="bob")
        self.as_("alice", agentctl.Ctl.post, "all hands", "x")
        self.as_("alice", agentctl.Ctl.post, "for carol", "x", to="carol")
        bob = self.as_("bob", agentctl.Ctl.messages)
        self.assertEqual({m["subject"] for m in bob}, {"hi", "all hands"})
        self.as_("bob", agentctl.Ctl.mark_read, [m["id"] for m in bob])
        self.assertEqual(self.as_("bob", agentctl.Ctl.messages), [])
        self.assertEqual(self.as_("alice", agentctl.Ctl.messages), [])  # own messages excluded


if __name__ == "__main__":
    unittest.main()
