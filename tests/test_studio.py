"""Profile Studio: storage, questionnaire, trade-off items, sources and the HTTP API, offline."""
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

from autoresearch.llm import LLM, OfflineLLM
from autoresearch.research.advisor import ProfileUserModel, load_user_model
from autoresearch.studio import server, sources, store
from autoresearch.taste import agreement, tradeoffs
from autoresearch.taste.researcher import load_researcher


def _personal(root, name="Ada Example"):
    meta = store.create_profile(root, name, "personal")
    store.write_consent(root, meta["slug"], [True] * len(store.consent_state(root, meta["slug"])))
    return meta["slug"]



class FirstShown(LLM):
    def complete(self, prompt, system="", max_tokens=1024, temperature=0.7):
        return json.dumps({"choice": 1})


def gate_default_suite(root):
    """Item-gate votes that pass every pair of the default questionnaire, as the shared
    data/researchers/agreement.jsonl holds them (a judge picking the first option shown: 5 of 10)."""
    from autoresearch.research.measure import SCENARIOS
    pairs = tradeoffs.build_seed_pairs(tradeoffs.load_bank(), [SCENARIOS[n] for n in sorted(SCENARIOS)], 0)
    agreement.judge(root, pairs, FirstShown(), workers=1)

class StoreTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_create_validates_and_refuses_existing(self):
        meta = store.create_profile(self.root, "Ada Example", "public")
        self.assertEqual(meta["slug"], "ada_example")
        with self.assertRaises(store.StudioError):
            store.create_profile(self.root, "Ada Example", "public")
        with self.assertRaises(store.StudioError):
            store.create_profile(self.root, "x", "public", slug="../evil")
        with self.assertRaises(store.StudioError):
            store.create_profile(self.root, "x", "nonsense")

    def test_directories_not_made_in_studio_are_read_only(self):
        os.makedirs(os.path.join(self.root, "someone", "corpus"))
        with self.assertRaises(store.StudioError):
            store.add_doc(self.root, "someone", "research", "t", "text", "upload")
        listed = store.list_profiles(self.root)
        self.assertEqual([(p["slug"], p["editable"]) for p in listed], [("someone", False)])

    def test_add_doc_dedupes_by_url_and_by_title_keeping_fuller_text(self):
        slug = store.create_profile(self.root, "Ada Example", "public")["slug"]
        n1, c1 = store.add_doc(self.root, slug, "research", "A Paper", "short abstract", "arxiv",
                               url="https://arxiv.org/abs/2401.00001")
        n2, c2 = store.add_doc(self.root, slug, "research", "A Paper", "short abstract", "arxiv",
                               url="https://arxiv.org/abs/2401.00001")
        self.assertTrue(c1)
        self.assertEqual((n1, c2), (n2, False))     # same item: one file, reported as already present
        self.assertEqual(len(store.list_docs(self.root, slug)), 1)
        # the cross-post with the full text replaces the abstract and records where else it lives
        n3, c3 = store.add_doc(self.root, slug, "research", "A paper", "full post text " * 50, "lesswrong",
                               url="https://www.lesswrong.com/posts/abc")
        docs = store.list_docs(self.root, slug)
        self.assertTrue(c3)
        self.assertEqual([d["file"] for d in docs], [n3])
        self.assertIn("arxiv.org/abs/2401.00001", store.read_doc(self.root, slug, n3)["front_matter"]["also_at"])
        # a shorter copy found later is not written
        n4, c4 = store.add_doc(self.root, slug, "research", "A Paper", "tiny", "semantic_scholar", url="https://s2/x")
        self.assertEqual((n4, c4), (n3, False))

    def test_doc_names_are_validated(self):
        slug = store.create_profile(self.root, "Ada Example", "public")["slug"]
        for bad in ("../studio.json", "research__x.txt/../../a", "notes.txt"):
            with self.assertRaises((store.StudioError, KeyError)):
                store.read_doc(self.root, slug, bad)

    def test_questionnaire_answers_become_corpus_documents(self):
        slug = _personal(self.root)
        store.save_answers(self.root, slug, {"focus": "Realistic evals.", "hobbies": "Climbing."})
        files = {d["file"] for d in store.list_docs(self.root, slug)}
        self.assertEqual(files, {"research__studio_questionnaire.txt", "other__studio_questionnaire.txt"})
        store.save_answers(self.root, slug, {"hobbies": ""})
        files = {d["file"] for d in store.list_docs(self.root, slug)}
        self.assertEqual(files, {"research__studio_questionnaire.txt"})
        with self.assertRaises(store.StudioError):
            store.save_answers(self.root, slug, {"not_a_question": "x"})

    def test_concurrent_answers_are_all_kept(self):
        slug = _personal(self.root)
        ids = ["focus", "proud", "abandon", "disagree", "resources", "hobbies"]
        threads = [threading.Thread(target=store.save_answers, args=(self.root, slug, {q: f"answer {q}"}))
                   for q in ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(set(store.load_meta(self.root, slug)["questionnaire"]), set(ids))

    def test_tradeoff_items_need_consent_and_record_through_trackp(self):
        gate_default_suite(self.root)
        slug = store.create_profile(self.root, "Ada Example", "personal")["slug"]
        with self.assertRaises(store.StudioError):
            store.ensure_seed_pairs(self.root, slug)
        store.write_consent(self.root, slug, [True] * len(store.consent_state(self.root, slug)))
        self.assertTrue(store.consent_complete(self.root, slug))
        n = store.ensure_seed_pairs(self.root, slug)
        self.assertGreater(n, 0)
        self.assertEqual(store.ensure_seed_pairs(self.root, slug), n)   # re-running keeps the same set
        pend = store.pending_choices(self.root, slug)
        self.assertEqual(pend["n_pending"], n)
        self.assertTrue(all(it["question"] and it["group"] for it in pend["items"]))
        self.assertFalse(any(k.startswith("_") for k in pend["items"][0]))   # nothing hidden leaks to the page
        store.record_choice(self.root, slug, pend["items"][0]["id"], 2, "a reason")
        self.assertEqual(store.pending_choices(self.root, slug)["n_pending"], n - 1)
        with open(os.path.join(self.root, slug, "seed_choices.jsonl")) as f:
            row = json.loads(f.readline())
        self.assertEqual((row["user_id"], row["reason"], row["source"]), (slug, "a reason", "seed"))
        with self.assertRaises(store.StudioError):
            store.record_choice(self.root, slug, pend["items"][0]["id"], 1)
        # the studio never points the team's personal track at a new person
        self.assertFalse(os.path.exists(os.path.join(self.root, "tracks.json")))

    def test_build_writes_a_profile_the_loop_loads(self):
        slug = _personal(self.root)
        store.add_doc(self.root, slug, "research", "Statement",
                      "We use simple baselines, careful controls and realistic deployment data.", "upload")
        store.save_answers(self.root, slug, {"trust_own": "I check a control and a sanity check."})
        out = store.build_profile(self.root, slug, OfflineLLM(), max_docs=10, log=lambda m: None)
        self.assertEqual(out["build"]["docs_used"], 2)
        self.assertGreater(out["profile"]["weights"]["simplicity"], 0)
        researcher = load_researcher(slug, self.root)
        prof = researcher.cached_profile()
        self.assertEqual(prof.researcher, slug)
        um, source = load_user_model(researcher.root, prof)
        self.assertIsInstance(um, ProfileUserModel)
        self.assertIn("profile.json", source)

        edited = store.save_edited_profile(self.root, slug, ["prefer realism", " "], {"realism": 3})
        self.assertEqual(edited["principles"], ["prefer realism"])
        self.assertEqual(edited["weights"]["realism"], 1.0)
        self.assertIn("manual_edit", edited["sources"])
        self.assertTrue(store.load_meta(self.root, slug)["build"]["edited"])
        with self.assertRaises(store.StudioError):
            store.save_edited_profile(self.root, slug, [], {"charisma": 1})

    def test_principles_are_merged_and_the_raw_list_kept(self):
        many = [f"rule number {i}" for i in range(25)] + ["rule number 0"]
        self.assertEqual(store.consolidate_principles(many, OfflineLLM()), [f"rule number {i}" for i in range(10)])

        class Merger(LLM):
            def complete(self, prompt, **kw):
                self.budget.charge(1, 1)
                return '{"principles": ["merged a", "merged b", 7]}' if "Merge them" in prompt else "{}"
        self.assertEqual(store.consolidate_principles(many, Merger()), ["merged a", "merged b"])

        class Broken(LLM):
            def complete(self, prompt, **kw):
                return "no json here"
        self.assertEqual(len(store.consolidate_principles(many, Broken())), 10)

        slug = _personal(self.root)
        for i in range(4):
            store.add_doc(self.root, slug, "research", f"Doc {i}", "simple careful ablation " * 3, "upload")
        with mock.patch.object(store, "profile_from_texts", return_value=store.TasteProfile(slug, principles=many)):
            store.build_profile(self.root, slug, OfflineLLM(), log=lambda m: None)
        meta = store.load_meta(self.root, slug)
        self.assertEqual(len(load_researcher(slug, self.root).cached_profile().principles), 10)
        self.assertEqual((meta["build"]["principles_extracted"], len(meta["principles_raw"])), (26, 26))

    def test_select_docs_order(self):
        slug = store.create_profile(self.root, "Ada Example", "public")["slug"]
        store.add_doc(self.root, slug, "research", "Old", "x" * 10, "arxiv", url="u1", date="2019-01-01")
        store.add_doc(self.root, slug, "research", "New", "x" * 10, "arxiv", url="u2", date="2024-05-01")
        store.add_doc(self.root, slug, "research", "Mine", "x" * 10, "upload")
        store.add_doc(self.root, slug, "research", "Undated", "x" * 10, "rss", url="u3")
        self.assertEqual([d["title"] for d in store.select_docs(self.root, slug, 0)], ["Mine", "New", "Old", "Undated"])
        self.assertEqual(len(store.select_docs(self.root, slug, 2)), 2)


class SourcesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.slug = store.create_profile(self.root, "Ada Example", "public")["slug"]

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_gather_dedupes_arxiv_against_s2_and_survives_a_failing_source(self):
        s2 = [{"title": "Paper One", "abstract": "abs one", "date": "2023-01-01", "url": "https://arxiv.org/abs/1",
               "arxiv": "1", "authors": ["Ada Example"], "venue": "", "citations": 3},
              {"title": "No Abstract", "abstract": "", "date": "2022-01-01", "url": "u", "arxiv": "", "authors": []}]
        ax = [{"title": "Paper One", "abstract": "abs one", "date": "2023-01-01", "url": "https://arxiv.org/abs/1",
               "arxiv": "1", "authors": ["Ada Example"], "position": "first"},
              {"title": "Paper Two", "abstract": "abs two", "date": "2024-01-01", "url": "https://arxiv.org/abs/2",
               "arxiv": "2", "authors": ["Ada Example"], "position": "solo"}]
        logs = []
        with mock.patch.object(sources, "s2_papers", return_value=s2), \
                mock.patch.object(sources, "arxiv_papers", return_value=ax), \
                mock.patch.object(sources, "lesswrong_posts", side_effect=RuntimeError("HTTP 429")), \
                mock.patch.object(sources, "wikipedia_summary",
                                  return_value={"title": "Ada", "extract": "A researcher.", "url": "https://w/ada"}):
            rep = sources.gather(self.root, self.slug, {"s2_author_id": "123", "arxiv": True, "wikipedia": True,
                                                        "lesswrong_user": "ada"}, logs.append)
        self.assertEqual(rep["semantic_scholar"], {"added": 1, "duplicates": 0, "skipped": 1})
        self.assertEqual(rep["arxiv"]["added"], 1)
        self.assertIn("error", rep["lesswrong"])
        self.assertEqual(sorted(d["title"] for d in store.list_docs(self.root, self.slug)), ["Paper One", "Paper Two"])
        meta = store.load_meta(self.root, self.slug)
        self.assertEqual((meta["bio"], meta["bio_source"]), ("A researcher.", "https://w/ada"))

    def test_inputs_are_validated_before_any_request(self):
        with self.assertRaises(store.StudioError):
            sources.s2_papers("1; drop")
        with self.assertRaises(store.StudioError):
            sources.lesswrong_posts('x"){}')
        with self.assertRaises(store.StudioError):
            sources.fetch_page("file:///etc/passwd")

    def test_strip_html(self):
        text = sources.strip_html("<html><script>x()</script><p>Hello &amp; welcome</p><p>Second</p></html>")
        self.assertEqual(text, "Hello & welcome\nSecond")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        cls.httpd = server.serve(cls.root, port=0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        shutil.rmtree(cls.root)

    def call(self, method, path, body=None):
        req = urllib.request.Request(self.base + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_page_and_static(self):
        with urllib.request.urlopen(self.base + "/", timeout=10) as r:
            self.assertIn(b"Profile Studio", r.read())
        with urllib.request.urlopen(self.base + "/static/app.js", timeout=10) as r:
            self.assertEqual(r.headers["content-type"], "text/javascript")
        for bad in ("/static/../server.py", "/static/%2e%2e/server.py", "/nothing"):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(self.base + bad, timeout=10)
            self.assertEqual(cm.exception.code, 404)

    def test_personal_flow_over_http(self):
        gate_default_suite(self.root)
        self.assertEqual(self.call("GET", "/api/config")[0], 200)
        code, meta = self.call("POST", "/api/profiles", {"name": "Grace Example", "mode": "personal"})
        self.assertEqual(code, 200)
        slug = meta["slug"]
        self.assertEqual(self.call("POST", "/api/profiles", {"name": "Grace Example", "mode": "personal"})[0], 400)
        self.assertEqual(self.call("POST", f"/api/profiles/{slug}/choices/generate", {})[0], 400)  # no consent
        n = len(self.call("GET", f"/api/profiles/{slug}")[1]["consent"])
        self.call("POST", f"/api/profiles/{slug}/consent", {"ticked": [True] * n})
        code, gen = self.call("POST", f"/api/profiles/{slug}/choices/generate", {})
        self.assertEqual(code, 200)
        item = self.call("GET", f"/api/profiles/{slug}/choices/pending?limit=1")[1]["items"][0]
        self.assertEqual(self.call("POST", f"/api/profiles/{slug}/choices/record", {"id": item["id"], "choice": 1})[0], 200)
        code, doc = self.call("POST", f"/api/profiles/{slug}/docs",
                              {"kind": "research", "title": "Notes", "text": "careful ablation of a simple baseline"})
        self.assertEqual(code, 200)
        self.assertEqual(self.call("PATCH", f"/api/profiles/{slug}", {"mode": "public"})[0], 400)
        code, job = self.call("POST", f"/api/profiles/{slug}/build", {"backend": "offline", "max_docs": 5})
        self.assertEqual(code, 200)
        for _ in range(100):
            job = self.call("GET", f"/api/jobs/{job['id']}")[1]
            if job["status"] != "running":
                break
            threading.Event().wait(0.05)
        self.assertEqual(job["status"], "done", job.get("error"))
        state = self.call("GET", f"/api/profiles/{slug}")[1]
        self.assertEqual(state["choices"], {"pairs": gen["pairs"], "answered": 1})
        self.assertIsNotNone(state["profile"])
        self.assertEqual(self.call("DELETE", f"/api/profiles/{slug}/docs/{doc['file']}")[0], 200)
        self.assertEqual(self.call("GET", "/api/profiles/missing_one")[0], 404)
        self.assertEqual(self.call("POST", f"/api/profiles/{slug}/build", {"backend": "gpt-free"})[0], 400)


if __name__ == "__main__":
    unittest.main()
