import tempfile
import unittest

from autoresearch.taste import qa


def scripted(lines):
    it = iter(lines)
    return lambda prompt="": next(it)


class FillTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_quit_then_resume_keeps_answers_and_asks_only_the_rest(self):
        qa.fill(self.root, "Ada Lovelace", ask=scripted(["first line", "second line", ".", "skip", "quit"]),
                say=lambda *a: None)
        rows = qa.answers(self.root, "ada_lovelace")
        self.assertEqual([r["qid"] for r in rows], ["q01"])
        self.assertEqual(rows[0]["answer"], "first line\nsecond line")

        asked = []
        qa.fill(self.root, "Ada Lovelace", ask=scripted(["quit"]), say=asked.append)
        self.assertTrue(any("[2/24]" in s for s in asked))
        self.assertFalse(any("[1/24]" in s for s in asked))


class SplitTest(unittest.TestCase):
    def test_one_heldout_question_per_section(self):
        questions = qa.load_questions()
        out = qa.held_out(questions)
        self.assertEqual(len(questions), 24)
        self.assertEqual(len(out), 8)
        self.assertEqual(len({q["section"] for q in questions if q["id"] in out}), 8)


if __name__ == "__main__":
    unittest.main()
