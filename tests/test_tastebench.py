"""WS B: Taste-Bench loader and paired-order scorer (wbopan/tastebench, protocol paired_order_v1)."""
import json
import os
import tempfile
import unittest

from autoresearch.llm import LLM
from autoresearch.research.advisor import TasteAdvisor
from autoresearch.taste import tastebench as tb
from autoresearch.taste.usermodel import Prediction


def question(qid, good, bad, answer_index, cell="detour_research", prefix="step 1\nstep 2"):
    method, domain = cell.split("_")
    return {"id": qid, "domain": domain, "method": method, "cell": cell, "source": "malt", "task_id": "t",
            "query": "Train the model.", "prefix_text": prefix, "prefix_text_short": prefix, "prefix_steps": 2,
            "choices": [good, bad] if answer_index == 0 else [bad, good],
            "answer": "AB"[answer_index], "answer_index": answer_index, "canary": "CANARY"}


QUESTIONS = [question("q1", "GOOD plan one", "weak plan one", 0),
             question("q2", "GOOD plan two", "weak plan two", 1, cell="parallel_research")]


class ScriptedLLM(LLM):
    name = "scripted"

    def __init__(self, answer):
        super().__init__()
        self.answer, self.prompts = answer, []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        return self.answer(prompt)


def picks_good(prompt):
    block_a = prompt[prompt.index("Option A:"):prompt.index("Option B:")]
    return "ANSWER: A" if "GOOD" in block_a else "ANSWER: B"


class TasteFan:
    """A user model that always prefers the GOOD step, sure of itself only on plan one."""

    def predict(self, context, options):
        index = next(i for i, o in enumerate(options) if "GOOD" in o)
        return Prediction("ab"[index], 0.9 if "plan one" in options[0] else 0.3)


class TasteBenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def run_base(self, answer, name="base.jsonl", questions=QUESTIONS):
        llm = ScriptedLLM(answer)
        records = tb.run(questions, tb.BaseDecider(llm), os.path.join(self.tmp, name))
        return records, llm

    def test_always_picking_the_same_position_scores_zero(self):
        records, _ = self.run_base(lambda p: "ANSWER: A")

        s = tb.summarize(records, QUESTIONS)["overall"]

        self.assertEqual(s["both_correct_rate"], 0.0)
        self.assertEqual(s["paired_outcomes"], {"CC": 0, "CW": 1, "WC": 1, "WW": 0})
        self.assertEqual(s["two_order_mean_accuracy"], 0.5)

    def test_picking_the_step_that_worked_in_both_orders_scores_one(self):
        records, _ = self.run_base(picks_good)

        self.assertEqual(tb.summarize(records, QUESTIONS)["overall"]["both_correct_rate"], 1.0)

    def test_an_answer_without_the_answer_line_counts_as_wrong(self):
        records, _ = self.run_base(lambda p: "I would go with A.")

        s = tb.summarize(records, QUESTIONS)["overall"]

        self.assertEqual(s["both_correct_rate"], 0.0)
        self.assertEqual(s["unparsed"], 4)

    def test_long_transcripts_keep_the_start_and_the_steps_nearest_the_fork(self):
        prefix = "\n".join(f"line {i:05d} " + "x" * 20 for i in range(12000))
        long_q = question("q1", "GOOD plan one", "weak plan one", 0, prefix=prefix)

        records, llm = self.run_base(picks_good, questions=[long_q])

        prompt = llm.prompts[0]
        self.assertIn("line 00000", prompt)
        self.assertIn(tb.OMISSION_MARKER, prompt)
        self.assertIn("line 11999", prompt)
        self.assertNotIn("line 01000", prompt)
        self.assertTrue(all(r["truncated"] for r in records))

    def test_a_rerun_asks_only_what_is_missing_or_failed(self):
        def fails_on_plan_two(prompt):
            if "plan two" in prompt:
                raise RuntimeError("HTTP 529")
            return picks_good(prompt)
        self.run_base(fails_on_plan_two)

        records, llm = self.run_base(picks_good)

        self.assertEqual(len(llm.prompts), 2)
        self.assertEqual(tb.summarize(records, QUESTIONS)["overall"]["both_correct_rate"], 1.0)

    def test_advisor_follows_confident_taste_and_otherwise_keeps_r0(self):
        base, _ = self.run_base(lambda p: "ANSWER: A")
        advisor = tb.AdvisorDecider(TasteAdvisor(TasteFan()), base)

        r1 = tb.run(QUESTIONS, advisor, os.path.join(self.tmp, "r1.jsonl"))

        self.assertEqual(tb.summarize(r1, QUESTIONS)["per_cell"]["detour_research"]["both_correct_rate"], 1.0)
        self.assertEqual(tb.summarize(r1, QUESTIONS)["per_cell"]["parallel_research"]["both_correct_rate"], 0.0)
        self.assertEqual(tb.summarize(r1, QUESTIONS, field="um_pred")["overall"]["both_correct_rate"], 1.0)
        self.assertEqual(tb.compare(r1, base, QUESTIONS)["diff"], 0.5)

    def test_a_question_whose_answer_letter_disagrees_with_its_index_is_rejected(self):
        bad = dict(QUESTIONS[0], answer="B")
        path = os.path.join(self.tmp, "research.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps(bad) + "\n")

        with self.assertRaisesRegex(ValueError, "q1"):
            tb.load_questions(path)


if __name__ == "__main__":
    unittest.main()
