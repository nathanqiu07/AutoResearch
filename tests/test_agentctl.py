import importlib.util
import os
import subprocess
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

    def test_brief_sees_pushed_message_without_touching_checkout(self):
        def git(*a, cwd=self.root):
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd,
                           check=True, capture_output=True)
        origin, a, b = (os.path.join(self.root, n) for n in ("origin.git", "a", "b"))
        git("init", "--bare", "-b", "main", origin)
        git("clone", origin, a)
        git("commit", "--allow-empty", "-m", "init", cwd=a)
        git("push", "-u", "origin", "main", cwd=a)
        git("clone", origin, b)
        with mock.patch.object(agentctl, "GIT_ROOT", a), \
                mock.patch.dict(os.environ, {"AGENT_NAME": "alice", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}):
            agentctl.Ctl(os.path.join(a, ".agents")).post("heads up", "loop.py signature changed", to="bob")
        with mock.patch.object(agentctl, "GIT_ROOT", b), mock.patch.dict(os.environ, {"AGENT_NAME": "bob"}):
            bob = agentctl.Ctl(os.path.join(b, ".agents"))
            self.assertEqual(bob.fetch(), 1)
            msgs = bob.messages(extra=bob.upstream_messages())
        self.assertEqual([m["subject"] for m in msgs], ["heads up"])
        self.assertFalse(os.path.exists(os.path.join(b, ".agents", "messages", msgs[0]["id"] + ".json")))


if __name__ == "__main__":
    unittest.main()
