import io
import json
import os
import random
import tempfile
import unittest
import unittest.mock

from autoresearch.integrations.living import (choices_from_memory, label_pending, labels, pending, write_disagree,
                                              write_label)
from autoresearch.integrations.shared_memory import LocalSharedMemory
from autoresearch.research.decisions import DecisionLog


class TestLivingUserModel(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.sh = LocalSharedMemory(os.path.join(self.d, "s.jsonl"))

    def test_label_roundtrip_to_choices(self):
        write_label(self.sh, "jane", 'Which "design" next?\nline two', "add tool logs", "strip meta", "b",
                    point="D1", reason="simpler")
        write_label(self.sh, "other", "ctx", "x", "y", "a")
        cs = choices_from_memory(self.sh, "jane")
        self.assertEqual(len(cs), 1)
        c = cs[0]
        self.assertEqual((c.user_id, c.a_text, c.b_text, c.chosen, c.decision_point, c.reason),
                         ("jane", "add tool logs", "strip meta", "b", "D1", "simpler"))
        self.assertEqual(c.context, "Which 'design' next? line two")
        with self.assertRaises(ValueError):
            write_label(self.sh, "jane", "c", "a", "b", "c")

    def test_relabel_latest_wins(self):
        k = write_label(self.sh, "jane", "ctx", "a1", "b1", "a")
        with open(self.sh.path) as f:
            recs = f.readlines()
        self.assertEqual(len(recs), 1)
        rec = json.loads(recs[0])
        rec["content"] = rec["content"].replace("chosen=a", "chosen=b").replace(" t=", " t=9")
        with open(self.sh.path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        ls = labels(self.sh, "jane")
        self.assertEqual([(f["key"], f["chosen"]) for f in ls], [(k, "b")])

    def test_decision_log_writes_disagree_and_label_clears_it(self):
        log = DecisionLog("run1", "R1-P", shared=self.sh, version="v")
        log.add(1, "D3", "accept or reject?", ["accept", "reject"], 1, user_model_choice=0, user_model_confidence=0.8)
        log.add(1, "D1", "agree", ["x", "y"], 0, user_model_choice=0, user_model_confidence=0.9)
        p = pending(self.sh, "jane")
        self.assertEqual(len(p), 1)
        self.assertEqual((p[0]["taste"], p[0]["action"], p[0]["point"]), ("accept", "reject", "D3"))
        answers = iter(["a"])
        n = label_pending(self.sh, "jane", ask=lambda _: next(answers), out=io.StringIO())
        self.assertEqual(n, 1)
        self.assertEqual(pending(self.sh, "jane"), [])
        self.assertEqual(len(pending(self.sh, "someone_else")), 1)
        cs = choices_from_memory(self.sh, "jane")
        self.assertEqual(len(cs), 1)
        self.assertEqual(cs[0].source, "disagreement")
        self.assertIn(cs[0].a_text, ("accept", "reject"))

    def test_many_labels_recalled(self):
        rng = random.Random(0)
        for k in range(60):
            write_label(self.sh, "jane", f"context {k}", f"opt a {k}", f"opt b {k}", rng.choice("ab"))
        for k in range(30):
            write_disagree(self.sh, "r", "R1", k, "D3", f"c{k}", ["p", "q"], 0, 1, 0.7)
        self.assertEqual(len(choices_from_memory(self.sh, "jane")), 60)
        self.assertEqual(len(pending(self.sh)), 30)


if __name__ == "__main__":
    unittest.main()


class TestPastDevSmokeScript(unittest.TestCase):
    def test_local_recall_is_complete(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
        import pastdev_smoke
        sh = LocalSharedMemory(os.path.join(tempfile.mkdtemp(), "s.jsonl"))
        res = pastdev_smoke.run(sh, 9, 0, "smoketest1")
        self.assertEqual((res["recall_by_kind"], res["recall_by_tag"], res["missing"]), (1.0, 1.0, []))
        with self.assertRaises(SystemExit):
            with unittest.mock.patch.dict(os.environ, {}, clear=True):
                pastdev_smoke.main(["--n", "1", "--wait", "0"])
