"""Real distractors for the time split: someone else's post-T work, topically close, never his."""
import contextlib
import io
import json
import os
import re
import tempfile
import unittest

from autoresearch.taste import real_distractors as rd
from autoresearch.taste import timesplit
from autoresearch.taste.researcher import Researcher
from autoresearch.taste.usermodel import Prediction

CUTOFF = "2025-04-01"
# The fields timesplit._pair_row writes; a real-distractor row must carry every one.
PAIR_FIELDS = {"pair_id", "decision_id", "split", "date", "source_doc", "url", "decision_point", "context",
               "a_text", "b_text", "chosen", "reason", "tag", "distractor_source", "author_position", "cutoff",
               "seed", "prompt_versions"}


def write_doc(root, name, url, title, date, authors, body):
    os.makedirs(os.path.join(root, "corpus"), exist_ok=True)
    with open(os.path.join(root, "corpus", name), "w") as f:
        f.write(f"---\nurl: {url}\ntitle: {title}\npublishedDate: {date}\nauthors: {json.dumps(authors)}\n"
                f"author_position: first\nkind: paper\n---\n# {title}\n{body}\n")


def make_researcher():
    root = os.path.join(tempfile.mkdtemp(), "jane_roe")
    os.makedirs(root)
    with open(os.path.join(root, "identity.json"), "w") as f:
        json.dump({"name": "Jane Roe", "banned": ["roe", "jane", "roelab"], "exclude_text": ["Roe"],
                   "exclude_domains": ["roelab.org"]}, f)
    me = ["Jane Roe", "A. Colleague"]
    write_doc(root, "research__probing_old.txt", "https://arxiv.org/abs/2401.00001", "Linear probes for evaluation awareness",
              "2024-02-01", me, "We train linear probes on residual activations to detect evaluation awareness in language models.")
    write_doc(root, "research__sandbag_old.txt", "https://arxiv.org/abs/2402.00002", "Sandbagging detection with noise injection",
              "2024-06-01", me, "Noise injection into weights reveals sandbagging models that hide capabilities on dangerous evaluations.")
    write_doc(root, "research__scheming_old.txt", "https://example.org/roe/scheming", "In-context scheming in frontier models",
              "2024-12-01", me, "Frontier models scheme in context when given goals that conflict with developers.")
    write_doc(root, "research__realism_new.txt", "https://arxiv.org/abs/2506.00003", "Realistic environments reduce evaluation awareness",
              "2025-06-10", me, "Realistic agentic environments with messy histories reduce evaluation awareness measured by probes.")
    write_doc(root, "research__cot_new.txt", "https://arxiv.org/abs/2507.00004", "Chain of thought monitoring of sabotage",
              "2025-07-15", me, "Monitoring chain of thought catches sabotage attempts in coding agents.")
    with open(os.path.join(root, "harvest_manifest.jsonl"), "w") as f:
        f.write(json.dumps({"url": "https://roe.blog/realism-mirror", "reason": "crosspost_of"}) + "\n")
    return Researcher("jane_roe", root)


def result(url, title, date, author=None, highlight=""):
    r = {"url": url, "title": title, "publishedDate": date + "T00:00:00.000Z", "highlights": [highlight]}
    if author:
        r["author"] = author
    return r


class FakeExa:
    """Serves fixed results per topic word in the query and records each search's filters."""

    def __init__(self, by_word):
        self.by_word, self.calls, self.cost = by_word, [], 0.0

    def search(self, query, **kw):
        self.calls.append(dict(kw, query=query))
        out = []
        for word, results in self.by_word.items():
            if word in query.lower():
                out += [r for r in results if kw["start_date"] <= r["publishedDate"][:10] <= kw["end_date"]]
        return out


REALISM = [
    # Good: someone else's, after T, close in topic.
    result("https://arxiv.org/abs/2506.11111", "Environment realism and evaluation awareness in agents", "2025-06-20",
           "Alex Other, Bo Second", "Messy realistic agentic environments change evaluation awareness measured with probes."),
    # His own work, by arXiv metadata, although Exa names someone else.
    result("https://arxiv.org/abs/2506.22222", "Evaluation awareness under realistic agentic histories", "2025-06-25",
           "Someone Else", "Realistic agentic environments reduce evaluation awareness probes."),
    # Dated before T by arXiv v1, although Exa's date is after.
    result("https://arxiv.org/abs/2503.33333", "Realism of agentic evaluation environments", "2025-05-01",
           "Carl Third", "Realistic agentic environments and evaluation awareness."),
    # No author evidence.
    result("https://blog.example.com/realism", "Notes on realistic environments for evaluation awareness", "2025-06-01",
           None, "Realistic agentic environments evaluation awareness probes."),
    # A near-duplicate title: the same work.
    result("https://mirror.example.com/realistic", "Realistic environments reduce evaluation awareness", "2025-06-11",
           "Dee Fourth", "Realistic agentic environments with messy histories reduce evaluation awareness measured by probes."),
    # One of his crossposts (harvest manifest).
    result("https://roe.blog/realism-mirror", "Realism mirror post about evaluation awareness", "2025-06-12",
           "Eve Fifth", "Realistic agentic environments evaluation awareness."),
    # Discusses him.
    result("https://arxiv.org/abs/2506.44444", "A reply on realistic environments and evaluation awareness", "2025-06-30",
           "Fay Sixth", "We revisit Roe's realistic environments for evaluation awareness."),
]
COT = [
    # Too far in topic for the band: an easy pick.
    result("https://arxiv.org/abs/2507.55555", "Protein folding with diffusion models", "2025-07-20",
           "Gus Seventh", "Diffusion models predict protein structures."),
]


def arxiv_meta(ids):
    meta = {"2506.11111": {"authors": ["Alex Other", "Bo Second"], "published": "2025-06-20"},
            "2506.22222": {"authors": ["Jane Roe", "Someone Else"], "published": "2025-06-25"},
            "2503.33333": {"authors": ["Carl Third"], "published": "2025-03-01"},
            "2506.44444": {"authors": ["Fay Sixth"], "published": "2025-06-30"},
            "2507.55555": {"authors": ["Gus Seventh"], "published": "2025-07-20"}}
    return {i: meta[i] for i in ids if i in meta}


class RewriterLLM:
    """Stands in for the pair rewriter: two neutral one-sentence options of equal length."""
    label, name = "fake", "fake"

    def __init__(self):
        self.prompts = []

    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        self.prompts.append(prompt)
        return json.dumps({"context": "A team is choosing its next research project in this area.",
                           "option_1": "Run the first candidate study on model behaviour.",
                           "option_2": "Run the other candidate study on model behaviour."})


class RealDistractorTest(unittest.TestCase):
    def setUp(self):
        self.r = make_researcher()
        self.exa = FakeExa({"realistic": REALISM, "chain of thought": COT})

    def build(self, band=None):
        band = band or {"lo": 0.05, "hi": 0.8, "source": "test"}
        return rd.build_real_pairs(self.r, CUTOFF, self.exa, RewriterLLM(), band, arxiv_meta=arxiv_meta)

    def test_heldout_projects_are_his_post_cutoff_documents(self):
        docs = [p["doc"] for p in rd.heldout_projects(self.r, CUTOFF)]
        self.assertEqual(docs, ["research__realism_new.txt", "research__cot_new.txt"])

    def test_search_is_after_cutoff_and_excludes_his_domains(self):
        self.build()
        for call in self.exa.calls:
            self.assertGreaterEqual(call["start_date"], CUTOFF)
            self.assertEqual(call["exclude_domains"], ["roelab.org"])
            self.assertEqual(call["exclude_text"], ["Roe"])

    def test_only_someone_elses_close_post_cutoff_work_is_kept(self):
        pairs, audit, report = self.build()
        self.assertEqual(len(pairs), 1)
        p = pairs[0]
        self.assertEqual(p["distractor_url"], "https://arxiv.org/abs/2506.11111")
        self.assertEqual(p["distractor_authors"], ["Alex Other", "Bo Second"])
        self.assertEqual(p["distractor_date"], "2025-06-20")
        self.assertEqual(report["dropped"], {"researcher_is_author": 1, "before_cutoff": 1, "no_author_evidence": 1,
                                             "own_work": 1, "mentions_researcher": 1})
        status = {a["doc"]: a["status"] for a in audit}
        self.assertEqual(status["research__cot_new.txt"], "no_candidate_in_band")

    def test_pair_has_timesplit_format_and_is_held_out(self):
        pairs, _, _ = self.build()
        p = pairs[0]
        self.assertTrue(PAIR_FIELDS <= set(p), PAIR_FIELDS - set(p))
        self.assertEqual(p["split"], "heldout")
        self.assertEqual(p["distractor_source"], "real")
        self.assertEqual(p["cutoff"], CUTOFF)
        self.assertEqual(p["decision_point"], "D1")
        self.assertIn(rd.REAL_VERSION, p["prompt_versions"])
        taken = p["a_text"] if p["chosen"] == "a" else p["b_text"]
        self.assertIn(taken, ("Run the first candidate study on model behaviour.",
                              "Run the other candidate study on model behaviour."))
        self.assertEqual(timesplit.check_pair(p, [], timesplit.banned_pattern(self.r)), [])
        self.assertEqual(rd.check_leakage(pairs, self.r, CUTOFF), [])

    def test_the_rewriter_sees_his_project_and_the_distractor_but_not_which_was_taken(self):
        llm = RewriterLLM()
        rd.build_real_pairs(self.r, CUTOFF, self.exa, llm, {"lo": 0.05, "hi": 0.8}, arxiv_meta=arxiv_meta)
        prompt = llm.prompts[0]
        self.assertIn("Realistic environments reduce evaluation awareness", prompt)
        self.assertIn("Environment realism and evaluation awareness in agents", prompt)
        self.assertNotIn("Jane", prompt)

    def test_a_band_that_excludes_everything_yields_no_pairs(self):
        pairs, _, report = self.build({"lo": 0.95, "hi": 0.99})
        self.assertEqual(pairs, [])
        self.assertEqual(report["no_candidate_in_band"], 2)

    def test_leakage_check_catches_each_violation(self):
        pairs, _, _ = self.build()
        bad = [dict(pairs[0], split="history"), dict(pairs[0], distractor_date="2025-01-01"),
               dict(pairs[0], distractor_authors=["J. Roe"]), dict(pairs[0], distractor_authors=[]),
               dict(pairs[0], distractor_url="https://arxiv.org/abs/2506.00003")]
        problems = rd.check_leakage(bad, self.r, CUTOFF)
        for pattern in ("not a held-out", "before", "author is the researcher", "no verified authors", "his own"):
            self.assertTrue(any(re.search(pattern, x) for x in problems), pattern)

    def test_nothing_is_written_into_the_researcher_directory(self):
        before = sorted(os.listdir(self.r.root))
        self.build()
        self.assertEqual(sorted(os.listdir(self.r.root)), before)

    def test_choices_match_timesplit_choice_rows(self):
        pairs, _, _ = self.build()
        c = rd.to_choices(pairs, self.r)[0]
        self.assertEqual(c.user_id, timesplit.ANON_USER)
        self.assertEqual(c.source, "timesplit")
        self.assertEqual(c.example_id, pairs[0]["pair_id"])
        self.assertEqual(c.group_id, timesplit.digest([pairs[0]["url"]])[:12])

    def test_match_assigns_each_candidate_once(self):
        projects = [{"doc": "a", "title": "probes awareness", "summary": "probes for evaluation awareness"},
                    {"doc": "b", "title": "probes awareness study", "summary": "evaluation awareness probes study"}]
        cand = {"url": "u", "title": "steering vectors compared", "summary": "awareness probes against steering baselines"}
        out = rd.match(projects, {"a": [cand], "b": [cand]}, (0.0, 0.99))
        self.assertEqual(len(out), 1)


class BandTest(unittest.TestCase):
    def test_band_uses_only_pre_cutoff_documents(self):
        r = make_researcher()
        band = rd.fit_band(r, CUTOFF)
        self.assertEqual(band["n_docs"], 3)
        self.assertLess(band["lo"], band["hi"])
        self.assertLessEqual(band["hi"], rd.NEAR_DUP)

    def test_band_cli_writes_json(self):
        r = make_researcher()
        out = os.path.join(tempfile.mkdtemp(), "band.json")
        with contextlib.redirect_stdout(io.StringIO()):
            rd.main(["band", "--researcher", r.root, "--cutoff", CUTOFF, "--out", out])
        self.assertEqual(rd.load_band(out)["source"], "jane_roe")

    def test_load_band_rejects_an_empty_band(self):
        with self.assertRaises(ValueError):
            rd.load_band(None, lo=0.5, hi=0.4)
        self.assertEqual(rd.load_band(None)["source"], "default-untuned")


class FixedModel:
    """Always picks the option containing `word`."""

    def __init__(self, word):
        self.word = word

    def predict(self, context, options):
        i = 0 if self.word in options[0] else 1
        return Prediction("ab"[i], 0.9, probabilities=[0.9, 0.1] if i == 0 else [0.1, 0.9])


class CompareTest(unittest.TestCase):
    def test_real_vs_llm_accuracy_on_matched_documents(self):
        from autoresearch.taste.usermodel import Choice

        def c(eid, group, real, other, chosen="a"):
            a, b = (real, other) if chosen == "a" else (other, real)
            return Choice(user_id="subject", context="ctx", a_text=a, b_text=b, chosen=chosen, example_id=eid,
                          group_id=group)
        # The model finds his option among LLM distractors (it contains "his"), not among real ones.
        llm = [c("l1", "g1", "his plan", "invented plan"), c("l2", "g2", "his idea", "invented idea", "b")]
        real = [c("r1", "g1", "plan one", "plan two"), c("r2", "g3", "plan three", "plan four", "b")]
        out = rd.compare_accuracy(FixedModel("his"), llm, real)
        self.assertEqual(out["llm"]["accuracy"], 1.0)
        self.assertEqual(out["real"]["n_pairs"], 2)
        self.assertEqual(out["matched"]["n_docs"], 1)
        self.assertEqual(out["matched"]["real_minus_llm"], out["matched"]["real"] - out["matched"]["llm"])


if __name__ == "__main__":
    unittest.main()
