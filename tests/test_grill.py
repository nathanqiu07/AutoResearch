"""WS B: the grill interviews the person about the current task and patches their user model."""
import contextlib
import io
import json
import os
import tempfile
import unittest

from autoresearch.llm import LLM
from autoresearch.research.decisions import DecisionLog
from autoresearch.taste import grill
from autoresearch.taste.methods import create_method
from autoresearch.taste.usermodel import TasteArtifacts, load_model

SLUG = "teammate"
REPLICATE = "Replicate the result on a second target model first."


class FakeLLM(LLM):
    """Writes questions when asked to, and predicts as a user model: it backs any option the
    person chose in a supplied past choice, otherwise leans 60/40 towards the first option."""
    name, model = "fake", "m"

    def __init__(self, generate=True):
        super().__init__()
        self.generate, self.payloads = generate, []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.budget.charge(10, 10)
        payload = json.loads(prompt.split("INPUT_JSON", 1)[1].split("\n", 1)[1])
        if "Predict which option" in prompt:
            self.payloads.append(payload)
            picked = {e["a_text"] if e["chosen"] == "a" else e["b_text"] for e in payload["past_choices"]}
            n = len(payload["options"])
            hits = [i for i, o in enumerate(payload["options"]) if o in picked]
            if hits:
                p = [0.05 / (n - 1)] * n
                p[hits[0]] = 0.95
            else:
                p = [0.6] + [0.4 / (n - 1)] * (n - 1)
            return json.dumps({"probabilities": p, "rationale": "fake"})
        if not self.generate:
            return "not json"
        if "answered" in payload:
            d = payload["answered"]
            return json.dumps({"questions": [
                {"point": "D2", "context": f"Follow-up to '{d['chosen']}': how many samples before you trust it?",
                 "options": ["20 per arm", "100 per arm"], "why": "evidence bar"},
                {"point": "D9", "context": "bad point", "options": ["x", "y"]},          # dropped
                {"point": "D1", "context": "one option only", "options": ["x"]}]})       # dropped
        return json.dumps({"questions": [
            {"point": "D3", "context": "A realism change cut P(eval) by 0.2 on one target. Accept it?",
             "options": ["Accept it now.", REPLICATE], "why": "replication bar"},
            {"point": "D6", "context": "What do you claim from a single-seed win?",
             "options": ["A preliminary signal.", "Nothing until replicated.", "A finding."]}]})


def save_model(root, method, llm, **artifacts):
    m = create_method(method, llm)
    m._artifacts = TasteArtifacts(**artifacts)
    path = os.path.join(root, SLUG, "usermodel.json")
    m.save(path)
    return path


class GrillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, SLUG))
        self.llm = FakeLLM()
        self.task = grill.resolve_task("eval_awareness")

    def tearDown(self):
        self.tmp.cleanup()

    def m5(self):
        return save_model(self.root, "m5", self.llm, principles=["Prefers grounded scenarios."],
                          metadata={"retrieval_pool": [], "retrieval_count": 3})

    def test_task_resolution(self):
        self.assertIn("not aware it is being evaluated", self.task["text"])
        free = grill.resolve_task(task_text="Write-up for the honeypot results")
        self.assertTrue(free["task"].startswith("write-up-for-the-honeypot-results-"))
        with self.assertRaises(ValueError):
            grill.resolve_task("no_such_task")

    def test_bank_questions_follow_the_task(self):
        qs = grill.bank_questions(grill.resolve_task(task_text="claims in the write-up, what to report"), 3)
        self.assertEqual(len(qs), 3)
        self.assertTrue(all(q["source"] == "bank" and len(q["options"]) == 2 for q in qs))
        self.assertTrue(all(q["context"].startswith("Current task: claims") for q in qs))

    def test_decision_questions_from_the_loop_log(self):
        log = DecisionLog("r1", "R1", root=os.path.join(self.root, "runs"), version="test")
        log.add(0, "D3", "Accept framing=neutral?", ["accept", "reject", "defer"], 0, evidence={"delta": 0.1})
        path = os.path.join(self.root, "runs", "r1", "decisions.jsonl")
        qs = grill.decision_questions(self.task, [path])
        self.assertEqual([(q["point"], q["options"], q["evidence"]) for q in qs],
                         [("D3", ["accept", "reject", "defer"], {"delta": 0.1})])

    def test_generated_questions_are_validated_and_ranked_by_uncertainty(self):
        self.m5()
        model = grill.load_user_model(self.root, SLUG, self.llm, warn=lambda *a: None)
        s = grill.Session(self.root, SLUG, self.task)
        s.add(grill.score(grill.llm_questions(self.llm, self.task, 4, warn=lambda *a: None), model))
        pending = s.pending()
        self.assertEqual([q["point"] for q in pending], ["D3", "D6"])      # equal confidence: queue order
        self.assertTrue(all(q["model_guess"] == 0 for q in pending))
        self.assertEqual(grill.public(pending[0])["recommended"], 1)
        self.assertEqual(grill.llm_questions(FakeLLM(generate=False), self.task, 2, warn=lambda *a: None), [])

    def test_interview_follows_a_disagreement_depth_first(self):
        self.m5()
        model = grill.load_user_model(self.root, SLUG, self.llm, warn=lambda *a: None)
        s = grill.Session(self.root, SLUG, self.task)
        s.add(grill.score(grill.llm_questions(self.llm, self.task, 4, warn=lambda *a: None), model))
        replies = iter(["p Never trust one target.", "2", "replication matters", "1", "", "q"])
        out = []
        asked = grill.interview(s, ask=lambda _: next(replies), say=out.append, model=model, llm=self.llm)
        self.assertEqual(asked, 2)
        answers = [a for a in s.answers() if a["kind"] == "choice"]
        self.assertEqual(answers[0]["agreed"], False)
        # the second question asked was the follow-up to the first answer, not the queued D6
        second = s.get(answers[1]["question_id"])
        self.assertEqual((second["point"], second["depth"], second["parent"]), ("D2", 1, answers[0]["question_id"]))
        self.assertEqual(s.status()["principles"], 1)
        self.assertTrue(any("guessed differently" in line for line in out))

    def test_apply_patches_retrieval_pool_and_is_idempotent_and_revertible(self):
        path = self.m5()
        with open(path) as f:
            original = f.read()
        s = grill.Session(self.root, SLUG, self.task)
        q = grill.llm_questions(self.llm, self.task, 2, warn=lambda *a: None)
        s.add(q)
        s.record(q[0]["id"], 2, "one target is an anecdote")
        s.principle("Always report the failed seeds.")
        info = grill.apply(self.root, SLUG)
        info2 = grill.apply(self.root, SLUG)
        self.assertEqual(info["patches"], info2["patches"])
        with open(path) as f:
            body = json.load(f)
        art = body["artifacts"]
        self.assertEqual(len(art["principles"]), 3)              # base + reason + stated principle
        self.assertIn("one target is an anecdote", art["principles"][1])
        self.assertTrue(art["principles"][2].startswith("While working on Create synthetic environments"))
        self.assertEqual(len(art["metadata"]["retrieval_pool"]), 1)
        self.assertEqual(art["exemplars"], [])
        # the loop's loader reads the patched model, and the patch now steers its prediction
        model = load_model(path, self.llm)
        p = model.predict(q[0]["context"], q[0]["options"])
        self.assertEqual(p.choice, "b")
        self.assertTrue(grill.revert(self.root, SLUG))
        with open(path) as f:
            self.assertEqual(json.load(f), json.loads(original))
        self.assertFalse(grill.revert(self.root, SLUG))

    def test_refit_becomes_the_new_base(self):
        self.m5()
        s = grill.Session(self.root, SLUG, self.task)
        q = grill.llm_questions(self.llm, self.task, 1, warn=lambda *a: None)
        s.add(q)
        s.record(q[0]["id"], 1)
        grill.apply(self.root, SLUG)
        save_model(self.root, "m5", self.llm, principles=["Refit principle."],
                   metadata={"retrieval_pool": [], "retrieval_count": 3})
        grill.apply(self.root, SLUG)
        with open(os.path.join(self.root, SLUG, grill.BASE)) as f:
            self.assertEqual(json.load(f)["artifacts"]["principles"], ["Refit principle."])
        # a base file that no longer matches the patched model is refused, not silently used
        with open(os.path.join(self.root, SLUG, grill.BASE), "a") as f:
            f.write(" ")
        with self.assertRaises(ValueError):
            grill.apply(self.root, SLUG)

    def test_methods_without_exemplar_pools_and_refusals(self):
        save_model(self.root, "m1", self.llm)
        s = grill.Session(self.root, SLUG, self.task)
        q = grill.llm_questions(self.llm, self.task, 2, warn=lambda *a: None)
        s.add(q)
        s.record(q[1]["id"], 3)                                    # 3 options -> 2 pairwise choices
        grill.apply(self.root, SLUG)
        with open(os.path.join(self.root, SLUG, "usermodel.json")) as f:
            art = json.load(f)["artifacts"]
        self.assertEqual(len(art["exemplars"]), 2)
        self.assertTrue(all(e["source"] == "grill" for e in art["exemplars"]))
        chosen = [e["a_text"] if e["chosen"] == "a" else e["b_text"] for e in art["exemplars"]]
        self.assertEqual(set(chosen), {"A finding."})
        save_model(self.root, "m4", self.llm)
        with self.assertRaises(ValueError):
            grill.apply(self.root, SLUG)

    def test_record_rejects_bad_choices_and_double_answers(self):
        s = grill.Session(self.root, SLUG, self.task)
        q = grill.llm_questions(self.llm, self.task, 1, warn=lambda *a: None)
        s.add(q)
        with self.assertRaises(ValueError):
            s.record(q[0]["id"], 3)
        s.record(q[0]["id"], 1)
        with self.assertRaises(ValueError):
            s.record(q[0]["id"], 2)
        self.assertIsNone(s.answers()[0]["agreed"])                 # no model, no guess

    def test_cli_agent_mode(self):
        def run(*argv):
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                code = grill.main(list(argv) + ["--root", self.root, "--researcher", SLUG])
            return code, out.getvalue()
        code, out = run("start", "--task", "eval_awareness", "--bank", "2")
        self.assertEqual(code, 0)
        pending = json.loads(out)["pending"]
        self.assertEqual(len(pending), 2)
        code, out = run("record", "--task", "eval_awareness", "--id", pending[0]["id"], "--choice", "1",
                        "--reason", "closer to how I work")
        self.assertEqual(json.loads(out)["recorded"], pending[0]["id"])
        code, out = run("next", "--task", "eval_awareness")
        self.assertEqual(json.loads(out)["id"], pending[1]["id"])
        code, out = run("record", "--task", "eval_awareness", "--id", pending[1]["id"], "--choice", "2")
        code, out = run("status", "--task", "eval_awareness")
        self.assertEqual(json.loads(out)["answered"], 2)
        code, out = run("add", "--task", "eval_awareness", "--point", "D4", "--parent", pending[0]["id"],
                        "--context", "Keep the narrow direction after two null results?",
                        "--option", "Keep it", "--option", "Drop it")
        added = json.loads(out)
        self.assertEqual((added["depth"], added["source"]), (1, "agent"))
        code, out = run("next", "--task", "eval_awareness")
        self.assertEqual(json.loads(out)["id"], added["id"])        # the follow-up comes first
        code, _ = run("add", "--task", "eval_awareness", "--point", "D4", "--context", "x", "--option", "same",
                      "--option", "same")
        self.assertEqual(code, 2)                                  # duplicate options are refused
        code, _ = run("apply")
        self.assertEqual(code, 2)                                  # no usermodel.json yet


if __name__ == "__main__":
    unittest.main()
