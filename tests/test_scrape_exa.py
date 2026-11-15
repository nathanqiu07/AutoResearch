"""WS B Track S harvest: only his own work is kept, each item once, with the best date."""
import glob
import json
import os
import tempfile
import unittest

from autoresearch.taste import scrape
from autoresearch.taste.timesplit import read_doc


class FakeExa:
    """Serves search, deep and contents from fixed pages, and records every call."""

    def __init__(self, pages):
        self.pages = {p["url"]: p for p in pages}
        self.searches, self.cost = [], 0.0

    def deep(self, query, output_schema, **kw):
        return {"output": {"content": {"items": []}}}

    def search(self, query, **kw):
        self.searches.append(kw)
        return [{"url": u, "title": p.get("title", "")} for u, p in self.pages.items()
                if (kw.get("start_date") or "") <= p.get("publishedDate", "")[:10] <= (kw.get("end_date") or "9")]

    def contents(self, urls, text_chars=4000, **kw):
        out = []
        for u in urls:
            p = self.pages.get(u) or next((p for k, p in self.pages.items()
                                           if scrape.canonical_url(k) == scrape.canonical_url(u)), None)
            if p and not kw.get("subpages"):
                out.append(dict(p, url=u))
        return out


def page(url, date, author, text="Some text.", title="A title"):
    return {"url": url, "publishedDate": date + "T00:00:00.000Z", "author": author, "text": text, "title": title}


def no_arxiv_meta(ids):
    return {}


class HarvestTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def harvest(self, pages, arxiv_meta=no_arxiv_meta, start="2025-01-01", end="2025-12-31"):
        self.exa = FakeExa(pages)
        return scrape.scrape_exa("Marius Hobbhahn", self.root, self.exa, start, end, arxiv_meta=arxiv_meta)

    def corpus(self):
        return sorted(glob.glob(os.path.join(self.root, "corpus", "*.txt")))

    def manifest(self):
        with open(os.path.join(self.root, "harvest_manifest.jsonl")) as f:
            return [json.loads(line) for line in f]

    def front_matter(self, path):
        with open(path) as f:
            head = f.read().split("\n---\n")[0]
        return dict(line.split(": ", 1) for line in head.splitlines()[1:])

    def test_arxiv_variants_collapse_to_one_document(self):
        self.harvest([page("https://arxiv.org/abs/2505.23836", "2025-05-28", "Marius Hobbhahn"),
                      page("https://arxiv.org/pdf/2505.23836v2", "2025-05-28", "Marius Hobbhahn"),
                      page("https://arxiv.org/html/2505.23836v1", "2025-05-28", "Marius Hobbhahn")])
        self.assertEqual(len(self.corpus()), 1)

    def test_lesswrong_and_alignment_forum_crosspost_is_one_document(self):
        self.harvest([page("https://www.lesswrong.com/posts/AbC123/evals-gap", "2025-03-01", "Marius Hobbhahn"),
                      page("https://www.alignmentforum.org/posts/AbC123/evals-gap", "2025-03-01", "Marius Hobbhahn")])
        self.assertEqual(len(self.corpus()), 1)

    def test_page_that_only_mentions_him_is_dropped(self):
        self.harvest([page("https://example.org/review", "2025-02-01", "Jane Doe",
                           text="A review of Marius Hobbhahn's paper.")])
        self.assertEqual(self.corpus(), [])
        self.assertEqual(self.manifest()[0]["reason"], "not_author")

    def test_result_without_author_or_byline_is_dropped_not_crashed(self):
        self.harvest([page("https://example.org/anon", "2025-02-01", None, text="No byline anywhere.")])
        self.assertEqual(self.manifest()[0]["reason"], "no_author_evidence")

    def test_mention_without_author_field_is_not_a_byline(self):
        self.harvest([page("https://example.org/news", "2025-02-01", None,
                           text="A recent paper by Hobbhahn and colleagues models scheming.")])
        self.assertEqual(self.manifest()[0]["reason"], "no_author_evidence")

    def test_semicolon_separated_authors_give_his_real_position(self):
        self.harvest([page("https://www.lesswrong.com/posts/Qq1/x", "2025-02-01", "Jane Doe; Marius Hobbhahn")])
        self.assertEqual(self.front_matter(self.corpus()[0])["author_position"], "last")

    def test_crosspost_under_the_same_title_is_one_document_with_the_earliest_date(self):
        self.harvest([page("https://arxiv.org/abs/2505.23836", "2025-05-28", "Marius Hobbhahn",
                           title="Large Language Models Often Know When They Are Being Evaluated"),
                      page("https://www.apolloresearch.ai/blog/eval-awareness", "2025-06-02", "Marius Hobbhahn",
                           title="Large language models often know when they are being evaluated")])
        files = self.corpus()
        self.assertEqual(len(files), 1)
        self.assertEqual(self.front_matter(files[0])["publishedDate"], "2025-05-28")

    def test_byline_in_text_counts_when_author_field_is_missing(self):
        self.harvest([page("https://www.apolloresearch.ai/blog/x", "2025-02-01", None,
                           text="By Marius Hobbhahn\n\nWe think evals need a science.")])
        self.assertEqual(len(self.corpus()), 1)

    def test_arxiv_v1_date_beats_exa_date(self):
        meta = {"2505.23836": {"authors": ["Joe Needham", "Marius Hobbhahn"], "published": "2025-05-28"}}
        self.harvest([page("https://arxiv.org/abs/2505.23836", "2025-06-10", "")], arxiv_meta=lambda ids: meta)
        fm = self.front_matter(self.corpus()[0])
        self.assertEqual(fm["publishedDate"], "2025-05-28")
        self.assertEqual(fm["date_source"], "arxiv_v1")
        self.assertEqual(fm["author_position"], "last")

    def test_undated_item_is_saved_without_publishedDate(self):
        p = page("https://www.lesswrong.com/posts/Zz9/undated", "", "Marius Hobbhahn")
        p["publishedDate"] = None
        self.exa = FakeExa([p])
        self.exa.search = lambda query, **kw: [{"url": p["url"]}]
        scrape.scrape_exa("Marius Hobbhahn", self.root, self.exa, "2025-01-01", "2025-12-31", arxiv_meta=no_arxiv_meta)
        date, _ = read_doc(self.corpus()[0])
        self.assertIsNone(date)

    def test_tweets_are_grouped_by_month_into_other_files(self):
        self.harvest([page(f"https://x.com/MariusHobbhahn/status/{i}", f"2025-04-0{i}", "MariusHobbhahn",
                           text=f"post {i}") for i in (1, 2, 3)])
        files = self.corpus()
        self.assertEqual(len(files), 1)
        self.assertTrue(os.path.basename(files[0]).startswith("other__"))
        self.assertEqual(self.front_matter(files[0])["publishedDate"], "2025-04-03")

    def test_listed_work_is_kept_with_the_listing_authors_and_date(self):
        known = {"https://www.lesswrong.com/posts/Zz1": {"authors": ["Dylan Bowman", "Marius Hobbhahn"],
                                                          "published": "2026-10-08", "title": "Embedded evals"}}
        self.exa = FakeExa([page("https://www.lesswrong.com/posts/Zz1/embedded-evals", "2026-10-09", "Dylan Bowman")])
        scrape.scrape_exa("Marius Hobbhahn", self.root, self.exa, "2025-01-01", "2026-12-31",
                          arxiv_meta=no_arxiv_meta, known=known)
        fm = self.front_matter(self.corpus()[0])
        self.assertEqual((fm["publishedDate"], fm["date_source"], fm["author_position"]),
                         ("2026-10-08", "listing", "last"))

    def test_listed_work_is_fetched_by_its_listed_url(self):
        listed_url = "http://www.blog.example/2022-08-14-post/"
        known = {listed_url: {"authors": ["Marius Hobbhahn"], "published": "2022-08-14", "title": "Post"}}
        self.exa = FakeExa([page(listed_url, "2022-08-14", None)])
        self.exa.contents = lambda urls, text_chars=4000, **kw: (
            [] if kw.get("subpages") else [self.exa.pages[u] for u in urls if u in self.exa.pages])
        scrape.scrape_exa("Marius Hobbhahn", self.root, self.exa, "2022-01-01", "2022-12-31",
                          arxiv_meta=no_arxiv_meta, known=known)
        self.assertEqual(len(self.corpus()), 1)
        self.assertEqual(self.front_matter(self.corpus()[0])["fetched_url"], listed_url)

    def test_index_pages_are_dropped(self):
        self.harvest([page("https://watcher.apolloresearch.ai/blog", "2025-09-02", "Marius Hobbhahn"),
                      page("https://greaterwrong.com/users/marius-hobbhahn", "2025-09-30", "Marius Hobbhahn")])
        self.assertEqual(self.corpus(), [])
        self.assertEqual({r["reason"] for r in self.manifest()}, {"index_page"})

    def test_search_windows_cover_the_whole_range(self):
        self.harvest([], start="2024-01-01", end="2024-12-31")
        windows = sorted({(s["start_date"], s["end_date"]) for s in self.exa.searches})
        self.assertEqual(windows, [("2024-01-01", "2024-03-31"), ("2024-04-01", "2024-06-30"),
                                   ("2024-07-01", "2024-09-30"), ("2024-10-01", "2024-12-31")])


if __name__ == "__main__":
    unittest.main()
