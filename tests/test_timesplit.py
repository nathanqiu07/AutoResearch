"""WS B Track S: no document dated at or after the cutoff T may enter the profile."""
import json
import os
import tempfile
import unittest

from autoresearch.llm import LLM
from autoresearch.taste import timesplit
from autoresearch.taste.researcher import Researcher
from autoresearch.taste.timesplit import profile_before
from autoresearch.taste.usermodel import Choice


class RecordingLLM(LLM):
    """Stands in for the extraction model and keeps every prompt it was shown."""

    def __init__(self):
        super().__init__()
        self.prompts = []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        return json.dumps({"principles": ["measure carefully"], "weights": {}})


def write_doc(root, name, published, body):
    os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
    header = f"---\npublishedDate: {published}\n---\n" if published else ""
    with open(os.path.join(root, "corpus", name), "w") as f:
        f.write(header + body)


class TimeSplitLeakageTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        write_doc(self.root, "research__early.txt", "2022-03-01T00:00:00.000Z", "EARLY_PAPER on baselines")
        write_doc(self.root, "other__early_post.txt", "2023-12-31", "EARLY_POST about cooking")
        write_doc(self.root, "research__on_cutoff.txt", "2024-01-01", "ON_CUTOFF_PAPER")
        write_doc(self.root, "research__late.txt", "2025-06-01T12:00:00Z", "LATE_PAPER on moonshots")
        write_doc(self.root, "research__undated.txt", None, "UNDATED_PAGE")
        self.researcher = Researcher("marius_test", self.root)

    def profile_prompts(self):
        llm = RecordingLLM()
        profile_before(self.researcher, "2024-01-01", llm)
        return "\n".join(llm.prompts)

    def test_documents_dated_before_cutoff_reach_the_profile(self):
        shown = self.profile_prompts()
        self.assertIn("EARLY_PAPER", shown)
        self.assertIn("EARLY_POST", shown)

    def test_no_document_dated_on_or_after_cutoff_reaches_the_profile(self):
        shown = self.profile_prompts()
        self.assertNotIn("LATE_PAPER", shown)
        self.assertNotIn("ON_CUTOFF_PAPER", shown)

    def test_undated_document_is_excluded_because_it_could_be_after_cutoff(self):
        self.assertNotIn("UNDATED_PAGE", self.profile_prompts())

    def test_front_matter_is_not_shown_to_the_model(self):
        self.assertNotIn("publishedDate", self.profile_prompts())


class FakeLLM(LLM):
    """Answers the two pair-building prompts from the document text: the direction is
    the text's first word, and each doc names "<word>_FOLLOWUP" as future work."""

    def __init__(self, same_distractor=False):
        super().__init__()
        self.prompts = []
        self.same_distractor = same_distractor

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        if prompt.startswith(timesplit.EXTRACT_PROMPT):
            word = prompt[len(timesplit.EXTRACT_PROMPT):].split()[0]
            return json.dumps({"topic": "evals", "direction": word + "_DIRECTION",
                               "future_work": [word + "_FOLLOWUP"]})
        target = prompt.split("Direction actually taken: ")[1].splitlines()[0]
        distractor = target if self.same_distractor else "GENERATED_ALTERNATIVE"
        return json.dumps({"distractor": distractor})


class TimeSplitPairsTest(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.root = os.path.join(self.base, "marius_test")
        write_doc(self.root, "research__early.txt", "2022-03-01", "EARLY paper")
        write_doc(self.root, "research__middle.txt", "2023-06-01", "MIDDLE paper")
        write_doc(self.root, "other__early_post.txt", "2022-05-01", "COOKING post")
        write_doc(self.root, "research__undated.txt", None, "UNDATED page")
        for k in range(8):
            write_doc(self.root, f"research__late{k}.txt", f"2025-0{k + 1}-01", f"LATE{k} paper")
        self.researcher = Researcher("marius_test", self.root)

    def build(self, llm=None):
        llm = llm or FakeLLM()
        report = timesplit.build_pairs(self.researcher, "2024-01-01", llm)
        return llm, report

    def read_choices(self, name):
        with open(os.path.join(self.root, name)) as f:
            return [Choice(**json.loads(line)) for line in f]

    def chosen_text(self, c):
        return c.a_text if c.chosen == "a" else c.b_text

    def test_research_docs_before_cutoff_become_history_and_after_become_heldout(self):
        self.build()
        history = self.read_choices(timesplit.HISTORY)
        heldout = self.read_choices(timesplit.HELDOUT)
        self.assertEqual(sorted(self.chosen_text(c) for c in history), ["EARLY_DIRECTION", "MIDDLE_DIRECTION"])
        self.assertEqual(sorted(self.chosen_text(c) for c in heldout), [f"LATE{k}_DIRECTION" for k in range(8)])
        self.assertEqual({c.source for c in history + heldout}, {"timesplit"})

    def test_chosen_option_is_not_always_in_the_same_position(self):
        self.build()
        self.assertEqual({c.chosen for c in self.read_choices(timesplit.HELDOUT)}, {"a", "b"})

    def test_history_pairs_are_built_without_any_text_from_after_cutoff(self):
        llm, _ = self.build()
        early_pair_prompts = [p for p in llm.prompts
                              if "Direction actually taken: EARLY_DIRECTION" in p
                              or "Direction actually taken: MIDDLE_DIRECTION" in p]
        self.assertEqual(len(early_pair_prompts), 2)
        self.assertNotIn("LATE", "\n".join(early_pair_prompts))
        history = "\n".join(self.chosen_text(c) for c in self.read_choices(timesplit.HISTORY))
        self.assertNotIn("LATE", history)

    def test_distractor_candidates_come_only_from_earlier_documents(self):
        llm, _ = self.build()
        middle_prompt = next(p for p in llm.prompts if "Direction actually taken: MIDDLE_DIRECTION" in p)
        self.assertIn("EARLY_FOLLOWUP", middle_prompt)
        self.assertNotIn("MIDDLE_FOLLOWUP", middle_prompt)

    def test_pair_whose_distractor_repeats_the_real_direction_is_dropped(self):
        _, report = self.build(FakeLLM(same_distractor=True))
        self.assertEqual(report["pairs"], 0)
        self.assertEqual(report["skipped"], 10)

    def test_build_refuses_to_overwrite_existing_pairs(self):
        self.build()
        with self.assertRaises(FileExistsError):
            self.build()

    def test_pair_rejected_in_review_leaves_the_heldout_file(self):
        self.build()
        answers = iter(["n", "y"])
        timesplit.review(self.researcher, ask=lambda _: next(answers), say=lambda _: None, limit=2)
        heldout = self.read_choices(timesplit.HELDOUT)
        self.assertEqual(len(heldout), 7)


class FakeSummaryExa:
    """Answers contents(summary=...) with a fixed summary per URL and counts calls."""

    def __init__(self, summaries):
        self.summaries, self.calls, self.cost = summaries, 0, 0.0

    def contents(self, urls, text_chars=4000, **kw):
        self.calls += 1
        return [{"url": u, "id": "req-" + u[-1], "summary": self.summaries[u]} for u in urls]


def write_url_doc(root, name, published, url, body):
    os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
    with open(os.path.join(root, "corpus", name), "w") as f:
        f.write(f"---\nurl: {url}\npublishedDate: {published}\n---\n{body}")


class ExaExtractTest(unittest.TestCase):
    def setUp(self):
        self.DECISION = {"point": "D1", "problem": "p", "did": "ran a baseline", "alternatives_named": [],
                         "stated_reason": "r", "quote": "we first ran a baseline"}
        self.root = tempfile.mkdtemp()
        write_url_doc(self.root, "research__a.txt", "2024-02-01", "https://ex.org/a", "we first ran a baseline")
        write_url_doc(self.root, "research__b.txt", "2024-05-01", "https://ex.org/b", "body b")
        self.researcher = Researcher("marius_test", self.root)
        self.exa = FakeSummaryExa({
            "https://ex.org/a": json.dumps({"decisions": [self.DECISION], "future_work": []}),
            "https://ex.org/b": "not json"})

    def rows(self):
        with open(os.path.join(self.root, timesplit.EXA_EXTRACT)) as f:
            return [json.loads(line) for line in f]

    def test_one_row_per_document_with_a_url(self):
        timesplit.exa_extract(self.researcher, self.exa)
        rows = {r["doc"]: r for r in self.rows()}
        self.assertEqual(set(rows), {"research__a.txt", "research__b.txt"})
        self.assertEqual(rows["research__a.txt"]["decisions"], [self.DECISION])

    def test_unparseable_summary_is_kept_with_exa_error(self):
        timesplit.exa_extract(self.researcher, self.exa)
        row = next(r for r in self.rows() if r["doc"] == "research__b.txt")
        self.assertEqual(row["decisions"], [])
        self.assertTrue(row["exa_error"])

    def test_rerun_skips_documents_already_extracted(self):
        timesplit.exa_extract(self.researcher, self.exa)
        calls = self.exa.calls
        report = timesplit.exa_extract(self.researcher, self.exa)
        self.assertEqual(self.exa.calls, calls)
        self.assertEqual(report["skipped_existing"], 2)
        self.assertEqual(len(self.rows()), 2)


class ScriptedLLM(LLM):
    """Answers the check prompt with reply(decisions, excerpt) -> dict, and counts calls."""

    def __init__(self, reply):
        super().__init__()
        self.reply, self.calls = reply, 0

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.calls += 1
        head, excerpt = prompt.split(timesplit.EXCERPT_MARK, 1)
        decisions = json.loads(head.split(timesplit.DECISIONS_MARK, 1)[1])
        return json.dumps(self.reply(decisions, excerpt))


def decision(quote, did="ran a baseline first"):
    return {"point": "D1", "problem": "which experiment", "did": did, "alternatives_named": [],
            "stated_reason": "cheap", "quote": quote}


class CheckTest(unittest.TestCase):
    TEXT = "Intro. We first ran a simple baseline before anything else. Then we wrote it up carefully."

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.researcher = Researcher("marius_test", self.root)

    def setup_doc(self, text, exa_decisions, exa_error=None):
        write_url_doc(self.root, "research__a.txt", "2024-02-01", "https://ex.org/a", text)
        os.makedirs(os.path.join(self.root, "extraction"), exist_ok=True)
        with open(os.path.join(self.root, timesplit.EXA_EXTRACT), "w") as f:
            f.write(json.dumps({"doc": "research__a.txt", "url": "https://ex.org/a", "decisions": exa_decisions,
                                "future_work": [], "exa_error": exa_error, "request_id": "r"}) + "\n")

    def check(self, reply, **kw):
        llm = ScriptedLLM(reply)
        report = timesplit.check_decisions(self.researcher, llm, **kw)
        return llm, report

    def kept(self):
        with open(os.path.join(self.root, timesplit.DECISIONS)) as f:
            return [json.loads(line) for line in f]

    def rejected(self):
        with open(os.path.join(self.root, timesplit.REJECTED)) as f:
            return [json.loads(line) for line in f]

    def test_kept_decision_with_real_quote_is_exa_verified(self):
        self.setup_doc(self.TEXT, [decision("We first ran a simple baseline")])
        self.check(lambda ds, ex: {"verdicts": [{"index": 0, "action": "keep"}], "missed": []})
        [row] = self.kept()
        self.assertEqual(row["tag"], "exa_verified")
        self.assertEqual(row["date"], "2024-02-01")

    def test_corrected_decision_is_exa_corrected_and_uses_claudes_fields(self):
        self.setup_doc(self.TEXT, [decision("We first ran a simple baseline", did="wrong summary")])
        fixed = decision("We first ran a simple baseline", did="ran a simple baseline first")
        self.check(lambda ds, ex: {"verdicts": [{"index": 0, "action": "correct", "decision": fixed}], "missed": []})
        [row] = self.kept()
        self.assertEqual((row["tag"], row["did"]), ("exa_corrected", "ran a simple baseline first"))

    def test_decision_whose_quote_is_not_in_the_text_is_rejected(self):
        self.setup_doc(self.TEXT, [decision("We trained a giant model from scratch")])
        self.check(lambda ds, ex: {"verdicts": [{"index": 0, "action": "keep"}], "missed": []})
        self.assertEqual(self.kept(), [])
        self.assertEqual(self.rejected()[0]["reason"], "quote_not_found")

    def test_missed_decision_is_added_as_claude_fallback(self):
        self.setup_doc(self.TEXT, [])
        self.check(lambda ds, ex: {"verdicts": [], "missed": [decision("Then we wrote it up carefully")]})
        self.assertEqual([r["tag"] for r in self.kept()], ["claude_fallback"])

    def test_document_where_exa_failed_is_fully_claude_fallback(self):
        self.setup_doc(self.TEXT, [], exa_error="summary is not JSON")
        self.check(lambda ds, ex: {"verdicts": [], "missed": [decision("We first ran a simple baseline")]})
        self.assertEqual([r["tag"] for r in self.kept()], ["claude_fallback"])

    def test_pdf_quote_with_ligature_curly_quotes_and_hyphen_break_matches(self):
        self.assertTrue(timesplit.quote_in_text("we first ran a baseline model", "so we \ufb01rst ran a base-\nline model"))
        self.assertTrue(timesplit.quote_in_text('"realistic" environments matter',
                                                "\u201crealistic\u201d   environments\nmatter a lot"))

    def test_decision_past_the_first_chunk_is_found(self):
        quote = "we abandoned the probe approach entirely"
        text = "x" * 250 + " " + quote + " " + "y" * 60
        self.setup_doc(text, [], exa_error="summary is not JSON")
        self.check(lambda ds, ex: {"verdicts": [], "missed": [decision(quote)] if quote in ex else []},
                   chunk_chars=100, overlap=50)
        [row] = self.kept()
        self.assertEqual(row["quote"], quote)

    def test_rerun_skips_checked_documents(self):
        self.setup_doc(self.TEXT, [decision("We first ran a simple baseline")])
        def reply(ds, ex):
            return {"verdicts": [{"index": 0, "action": "keep"}], "missed": []}
        self.check(reply)
        llm, _ = self.check(reply)
        self.assertEqual(llm.calls, 0)
        self.assertEqual(len(self.kept()), 1)


class DistractorLLM(LLM):
    """Answers the three distractor prompts; records every prompt."""

    def __init__(self, future_index=0):
        super().__init__()
        self.prompts, self.future_index = [], future_index

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        if prompt.startswith(timesplit.FUTURE_PROMPT):
            return json.dumps({"index": self.future_index})
        if prompt.startswith(timesplit.CONTEMP_PROMPT):
            return json.dumps({"index": 0, "alternative": "OTHER_GROUP_ALTERNATIVE"})
        return json.dumps({"alternative": "GENERATED_ALTERNATIVE"})


class SearchRecorder:
    def __init__(self, results):
        self.results, self.calls = results, []

    def search(self, query, **kw):
        self.calls.append(kw)
        return self.results


class DistractorTest(unittest.TestCase):
    CUTOFF = "2024-06-01"

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.researcher = Researcher("marius_test", self.root)
        write_url_doc(self.root, "research__early.txt", "2023-01-01", "https://ex.org/early", "early")
        write_url_doc(self.root, "research__mid.txt", "2024-03-01", "https://ex.org/mid", "mid")
        write_url_doc(self.root, "research__late.txt", "2025-01-01", "https://ex.org/late", "late")
        os.makedirs(os.path.join(self.root, "extraction"), exist_ok=True)
        with open(os.path.join(self.root, timesplit.EXA_EXTRACT), "w") as f:
            f.writelines(json.dumps({"doc": doc, "url": "u", "decisions": [], "exa_error": None,
                                     "future_work": [{"idea": idea, "quote": "q"}]}) + "\n"
                         for doc, idea in (("research__early.txt", "EARLY_IDEA"), ("research__late.txt", "LATE_IDEA")))
        with open(os.path.join(self.root, timesplit.DECISIONS), "w") as f:
            f.write(json.dumps(dict(decision("q" * 20, did="LATE_WORK"), doc="research__late.txt",
                                    url="https://ex.org/late", date="2025-01-01", tag="exa_verified",
                                    decision_id="late1")) + "\n")

    def mid_decision(self, alternatives=()):
        return dict(decision("q" * 20, did="MID_WORK"), alternatives_named=list(alternatives),
                    doc="research__mid.txt", url="https://ex.org/mid", date="2024-03-01", decision_id="mid1")

    def test_named_alternative_is_used_first(self):
        out = timesplit.next_distractor(self.mid_decision(["NAMED_ALT"]), self.researcher, DistractorLLM(),
                                        None, self.CUTOFF)
        self.assertEqual((out["text"], out["source"]), ("NAMED_ALT", "named"))

    def test_own_future_work_is_used_when_not_pursued(self):
        out = timesplit.next_distractor(self.mid_decision(), self.researcher, DistractorLLM(), None, self.CUTOFF)
        self.assertEqual((out["text"], out["source"]), ("EARLY_IDEA", "own_future_work"))

    def test_own_future_work_is_skipped_when_he_pursued_it_later(self):
        out = timesplit.next_distractor(self.mid_decision(), self.researcher, DistractorLLM(future_index=None),
                                        None, self.CUTOFF)
        self.assertEqual(out["source"], "generated")

    def test_history_decision_never_sees_material_from_after_cutoff(self):
        llm, exa = DistractorLLM(future_index=None), SearchRecorder([])
        timesplit.next_distractor(self.mid_decision(), self.researcher, llm, exa, self.CUTOFF)
        self.assertNotIn("LATE", "\n".join(llm.prompts))
        self.assertLess(exa.calls[0]["end_date"], self.CUTOFF)

    def test_contemporaneous_search_excludes_his_own_work(self):
        exa = SearchRecorder([{"url": "https://ex.org/his", "author": "Marius Hobbhahn", "title": "his"},
                              {"url": "https://ex.org/other", "author": "Jane Doe", "title": "other"}])
        llm = DistractorLLM(future_index=None)
        out = timesplit.next_distractor(self.mid_decision(), self.researcher, llm, exa, self.CUTOFF)
        self.assertEqual(exa.calls[0]["exclude_text"], ["Hobbhahn"])
        self.assertEqual((out["source"], out["evidence_url"]), ("contemporaneous", "https://ex.org/other"))
        self.assertNotIn("ex.org/his", llm.prompts[-1])

    def test_next_distractor_after_a_source_starts_at_the_following_one(self):
        out = timesplit.next_distractor(self.mid_decision(["NAMED_ALT"]), self.researcher, DistractorLLM(),
                                        None, self.CUTOFF, after="named")
        self.assertEqual(out["source"], "own_future_work")


if __name__ == "__main__":
    unittest.main()
