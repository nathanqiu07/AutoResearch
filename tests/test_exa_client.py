"""ExaClient request bodies: new optional arguments reach Exa under the spec's names,
and calls written before them send the same body (so their cache keys still hit)."""
import unittest
from unittest import mock

from autoresearch.integrations import exa


class ExaClientBodyTest(unittest.TestCase):
    def setUp(self):
        self.sent = []

        def fake_post(url, body, headers, timeout=60):
            self.sent.append((url, body))
            return {"results": [], "output": {"content": {"items": []}}, "costDollars": {"total": 0.01}}

        patcher = mock.patch.object(exa, "post_json", fake_post)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = exa.ExaClient(api_key="test-key")

    def test_existing_search_call_sends_the_same_body_as_before(self):
        self.client.search("q", num_results=5)
        self.assertEqual(self.sent[0][1], {"query": "q", "type": "auto", "numResults": 5,
                                           "contents": {"highlights": {"query": "q", "maxCharacters": 800}}})

    def test_date_and_domain_filters_reach_the_body(self):
        self.client.search("q", start_date="2025-01-01", end_date="2025-03-31",
                           include_domains=["arxiv.org"], exclude_text=["Hobbhahn"])
        body = self.sent[0][1]
        self.assertEqual(body["startPublishedDate"], "2025-01-01T00:00:00Z")
        self.assertEqual(body["endPublishedDate"], "2025-03-31T00:00:00Z")
        self.assertEqual(body["includeDomains"], ["arxiv.org"])
        self.assertEqual(body["excludeText"], ["Hobbhahn"])

    def test_contents_sends_summary_schema_and_subpages_at_top_level(self):
        summary = {"query": "decisions", "schema": {"type": "object"}}
        self.client.contents(["https://example.org/p"], summary=summary, subpages=5,
                             subpage_target=["blog"], max_age_hours=0)
        url, body = self.sent[0]
        self.assertTrue(url.endswith("/contents"))
        self.assertEqual(body["urls"], ["https://example.org/p"])
        self.assertEqual(body["summary"], summary)
        self.assertEqual(body["subpages"], 5)
        self.assertEqual(body["subpageTarget"], ["blog"])
        self.assertEqual(body["maxAgeHours"], 0)

    def test_deep_search_sends_output_schema_and_type_deep(self):
        schema = {"type": "object", "properties": {"items": {"type": "array"}}}
        out = self.client.deep("all his work", schema, additional_queries=["his papers"],
                               include_domains=["arxiv.org"])
        body = self.sent[0][1]
        self.assertEqual(body["type"], "deep")
        self.assertEqual(body["outputSchema"], schema)
        self.assertEqual(body["additionalQueries"], ["his papers"])
        self.assertEqual(out["output"]["content"], {"items": []})

    def test_cost_is_summed_across_calls(self):
        self.client.search("a")
        self.client.contents(["https://example.org"])
        self.assertAlmostEqual(self.client.cost, 0.02)


class ExaClientCacheTest(unittest.TestCase):
    def test_response_with_a_failed_url_is_not_cached(self):
        import tempfile
        replies = [{"results": [], "statuses": [{"id": "u", "status": "error", "error": {"tag": "CRAWL_TIMEOUT"}}]},
                   {"results": [{"url": "u", "summary": "ok"}], "statuses": [{"id": "u", "status": "success"}]}]
        with mock.patch.object(exa, "post_json", lambda *a, **kw: replies.pop(0)):
            client = exa.ExaClient(api_key="k", cache_dir=tempfile.mkdtemp())
            client.contents(["u"])
            self.assertEqual(client.contents(["u"]), [{"url": "u", "summary": "ok"}])


if __name__ == "__main__":
    unittest.main()
