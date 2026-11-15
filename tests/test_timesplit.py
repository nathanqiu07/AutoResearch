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


class PairLLM(LLM):
    """Writes each pair from the decision and distractor it is shown; can be told to leak his name."""

    def __init__(self, name_in_context=False):
        super().__init__()
        self.name_in_context = name_in_context

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        did = prompt.split("Decision: ")[1].splitlines()[0]
        alt = prompt.split("Alternative: ")[1].splitlines()[0]
        context = "Marius Hobbhahn had to choose." if self.name_in_context else "A team had to choose a next step."
        return json.dumps({"context": context, "did": did, "alternative": alt})


class TimeSplitPairsTest(unittest.TestCase):
    NAMES = ["EARLY", "MIDDL"] + [f"LATE{k}" for k in range(8)]

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.root = os.path.join(self.base, "marius_test")
        os.makedirs(os.path.join(self.root, "extraction"))
        dates = ["2022-03-01", "2023-06-01"] + [f"2025-0{k + 1}-01" for k in range(8)]
        decisions, distractors = [], []
        for name, date in zip(self.NAMES, dates):
            write_url_doc(self.root, f"research__{name}.txt", date, f"https://ex.org/{name}", f"{name} paper")
            decisions.append(dict(decision("q" * 20, did=f"TAKEN_{name}"), doc=f"research__{name}.txt",
                                  url=f"https://ex.org/{name}", date=date, tag="exa_verified", decision_id=name))
            distractors.append({"decision_id": name, "text": f"OTHER_{name}", "source": "generated",
                                "evidence_url": None, "cutoff": "2024-01-01"})
        for fname, rows in ((timesplit.DECISIONS, decisions), (timesplit.DISTRACTORS, distractors)):
            with open(os.path.join(self.root, fname), "w") as f:
                f.writelines(json.dumps(r) + "\n" for r in rows)
        self.researcher = Researcher("marius_test", self.root)

    def build(self, llm=None, seed=0):
        return timesplit.write_pairs(self.researcher, llm or PairLLM(), "2024-01-01", seed=seed)

    def read_choices(self, name):
        with open(os.path.join(self.root, name)) as f:
            return [Choice(**json.loads(line)) for line in f]

    def chosen_text(self, c):
        return c.a_text if c.chosen == "a" else c.b_text

    def test_research_docs_before_cutoff_become_history_and_after_become_heldout(self):
        self.build()
        history = self.read_choices(timesplit.HISTORY)
        heldout = self.read_choices(timesplit.HELDOUT)
        self.assertEqual(sorted(self.chosen_text(c) for c in history), ["TAKEN_EARLY", "TAKEN_MIDDL"])
        self.assertEqual(sorted(self.chosen_text(c) for c in heldout), [f"TAKEN_LATE{k}" for k in range(8)])
        self.assertEqual({c.source for c in history + heldout}, {"timesplit"})

    def test_chosen_option_is_not_always_in_the_same_position(self):
        self.build()
        self.assertEqual({c.chosen for c in self.read_choices(timesplit.HELDOUT)}, {"a", "b"})

    def test_ab_order_is_seeded(self):
        self.build(seed=3)
        first = [c.chosen for c in self.read_choices(timesplit.HELDOUT)]
        os.remove(os.path.join(self.root, timesplit.PAIRS))
        self.build(seed=3)
        self.assertEqual([c.chosen for c in self.read_choices(timesplit.HELDOUT)], first)

    def test_choice_rows_carry_decision_point_reason_and_a_group_per_source(self):
        self.build()
        c = self.read_choices(timesplit.HISTORY)[0]
        self.assertEqual((c.decision_point, c.reason), ("D1", "cheap"))
        self.assertEqual(len({x.group_id for x in self.read_choices(timesplit.HELDOUT)}), 8)

    def test_choice_rows_never_name_him_in_any_field(self):
        self.build()
        rows = ""
        for name in (timesplit.HISTORY, timesplit.HELDOUT):
            with open(os.path.join(self.root, name)) as f:
                rows += f.read()
        self.assertNotIn("marius", rows.lower())
        self.assertNotIn("ex.org", rows)

    def test_distractors_chosen_for_another_cutoff_are_refused(self):
        with self.assertRaises(ValueError):
            timesplit.write_pairs(self.researcher, PairLLM(), "2023-01-01")

    def test_rerun_after_a_crash_keeps_pairs_already_written(self):
        class CrashingLLM(PairLLM):
            def __init__(self, crash_on):
                super().__init__()
                self.calls, self.crash_on = 0, crash_on

            def complete(self, prompt, **kw):
                self.calls += 1
                if self.calls == self.crash_on:
                    raise RuntimeError("cli died")
                return super().complete(prompt, **kw)

        with self.assertRaises(RuntimeError):
            self.build(CrashingLLM(crash_on=4))
        second = CrashingLLM(crash_on=None)
        report = self.build(second)
        self.assertEqual((report["pairs"], second.calls), (10, 7))

    def test_context_never_names_him(self):
        report = self.build(PairLLM(name_in_context=True))
        self.assertEqual((report["pairs"], report["failed_checks"]), (0, 10))

    def test_unequal_option_lengths_fail_the_check(self):
        pair = {"context": "A team had to choose.", "a_text": "x" * 15, "b_text": "y" * 10}
        self.assertTrue(timesplit.check_pair(pair, []))

    def test_context_naming_a_later_title_fails_the_check(self):
        pair = {"context": "After Frontier Models Scheme, a team had to choose.", "a_text": "x" * 10, "b_text": "y" * 10}
        self.assertTrue(timesplit.check_pair(pair, ["Frontier Models Scheme"]))
        self.assertEqual(timesplit.check_pair(pair, []), [])

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

    def test_arxiv_paper_is_summarized_from_its_full_text_page(self):
        write_url_doc(self.root, "research__c.txt", "2024-06-01", "https://arxiv.org/abs/2504.12170", "body c")
        self.exa.summaries["https://arxiv.org/html/2504.12170"] = json.dumps({"decisions": [self.DECISION]})
        timesplit.exa_extract(self.researcher, self.exa)
        row = next(r for r in self.rows() if r["doc"] == "research__c.txt")
        self.assertEqual((row["decisions"], row["url"]), ([self.DECISION], "https://arxiv.org/abs/2504.12170"))

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
        exa = SearchRecorder([{"url": "https://ex.org/his", "author": "Marius Hobbhahn", "title": "his",
                               "publishedDate": "2024-02-01"},
                              {"url": "https://ex.org/undated", "author": "Jane Doe", "title": "undated"},
                              {"url": "https://ex.org/other", "author": "Jane Doe", "title": "other",
                               "publishedDate": "2024-02-01"}])
        llm = DistractorLLM(future_index=None)
        out = timesplit.next_distractor(self.mid_decision(), self.researcher, llm, exa, self.CUTOFF)
        self.assertEqual(exa.calls[0]["exclude_text"], ["Hobbhahn"])
        self.assertEqual((out["source"], out["evidence_url"]), ("contemporaneous", "https://ex.org/other"))
        self.assertNotIn("his:", llm.prompts[-1])
        self.assertNotIn("undated:", llm.prompts[-1])

    def test_next_distractor_after_a_source_starts_at_the_following_one(self):
        out = timesplit.next_distractor(self.mid_decision(["NAMED_ALT"]), self.researcher, DistractorLLM(),
                                        None, self.CUTOFF, after="named")
        self.assertEqual(out["source"], "own_future_work")


if __name__ == "__main__":
    unittest.main()
