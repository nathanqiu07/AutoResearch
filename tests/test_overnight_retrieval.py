import math
import unittest

from autoresearch.taste.overnight.contracts import canonical_json, digest, sha256_text, source_manifest


def documents():
    return [{"document_id": key, "researcher_id": "fixture", "content": text,
             "content_sha256": sha256_text(text)} for key, text in
            [("d2", "Compare controlled experiments and replication."),
             ("d1", "Bananas apples oranges. Bananas apples oranges.")]]


def config(docs):
    sources = source_manifest(docs)
    return {"researcher_id": "fixture", "allowed_sources": sources,
            "allowed_source_manifest_hash": digest(sources), "chunk_chars": 80, "top_k": 5}


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        from autoresearch.taste.overnight import retrieval
        self.r = retrieval
        self.docs = documents()
        self.cfg = config(self.docs)
        self.decision = {"context": "Choose a controlled experiment", "options": ["replication", "exploration"]}

    def test_unapproved_or_changed_sources_are_rejected_before_indexing(self):
        with self.assertRaisesRegex(ValueError, "source set"):
            self.r.chunk_documents(self.docs[:1], self.cfg)
        self.docs[0]["content"] = "altered"
        with self.assertRaisesRegex(ValueError, "hash"):
            self.r.chunk_documents(self.docs, self.cfg)

    def test_lexical_relevance_and_ties_ignore_input_document_order(self):
        chunks = self.r.chunk_documents(self.docs, self.cfg)
        ranked = self.r.rank_lexical(chunks, self.decision)
        self.assertEqual(ranked[0]["document_id"], "d2")
        reverse = self.r.chunk_documents(list(reversed(self.docs)), self.cfg)
        self.assertEqual(ranked, self.r.rank_lexical(reverse, self.decision))
        zero = {"context": "zzz", "options": ["yyy", "xxx"]}
        self.assertEqual(self.r.rank_lexical(chunks, zero)[0]["document_id"], "d1")

    def test_chunks_are_exact_spans_and_duplicate_text_is_indexed_once(self):
        text = "alpha beta gamma delta"
        docs = [{"document_id": key, "researcher_id": "fixture", "content": text,
                 "content_sha256": sha256_text(text)} for key in ["b", "a"]]
        chunks = self.r.chunk_documents(docs, dict(config(docs), chunk_chars=8))
        self.assertEqual({p["document_id"] for p in chunks}, {"a"})
        for part in chunks:
            self.assertEqual(part["text"], text[part["start"]:part["end"]])
            self.assertTrue(part["text"])

    def test_chunks_and_embedding_inputs_exclude_unpermitted_text_and_gaps(self):
        text = "private αβ allowed hidden second safe private"
        spans = [{"start": text.index(value), "end": text.index(value) + len(value)}
                 for value in ["αβ allowed", "second safe"]]
        docs = [{"document_id": "restricted", "researcher_id": "fixture", "content": text,
                 "content_sha256": sha256_text(text), "permitted_spans": list(reversed(spans))}]
        cfg = dict(config(docs), chunk_chars=100)
        chunks = self.r.chunk_documents(docs, cfg)
        self.assertEqual([part["text"] for part in chunks], ["αβ allowed", "second safe"])
        for part in chunks:
            self.assertEqual(part["text"], text[part["start"]:part["end"]])
            self.assertTrue(any(span["start"] <= part["start"] < part["end"] <= span["end"] for span in spans))
        self.assertEqual(self.r.embedding_inputs(docs, cfg, self.decision)[1:], ["αβ allowed", "second safe"])

    def test_explicit_empty_or_malformed_permissions_never_allow_full_document(self):
        self.docs[0]["permitted_spans"] = []
        self.assertEqual({c["document_id"] for c in self.r.chunk_documents(self.docs, self.cfg)}, {"d1"})
        for spans in [None, "all", {}, [None], [{"start": True, "end": 3}],
                      [{"start": 0, "end": False}], [{"start": 0.0, "end": 3}],
                      [{"start": -1, "end": 3}], [{"start": 3, "end": 3}],
                      [{"start": 0, "end": 1000}]]:
            with self.subTest(spans=spans), self.assertRaisesRegex(ValueError, "permitted"):
                self.docs[0]["permitted_spans"] = spans
                self.r.chunk_documents(self.docs, self.cfg)

    def test_permission_clipping_preserves_grid_and_deduplicates_identical_ranges(self):
        text = " abcd efgh ijkl "
        docs = [{"document_id": "d", "researcher_id": "fixture", "content": text,
                 "content_sha256": sha256_text(text)}]
        cfg = dict(config(docs), chunk_chars=5)
        original = self.r.chunk_documents(docs, cfg)
        docs[0]["permitted_spans"] = [{"start": 1, "end": len(text) - 1}] * 2
        self.assertEqual(self.r.chunk_documents(docs, cfg), original)

    def test_overlapping_permissions_do_not_duplicate_or_merge_across_ranges(self):
        text = "abcdefghijklmnop"
        docs = [{"document_id": "d", "researcher_id": "fixture", "content": text,
                 "content_sha256": sha256_text(text),
                 "permitted_spans": [{"start": 4, "end": 12}, {"start": 0, "end": 8}, {"start": 0, "end": 4}]}]
        chunks = self.r.chunk_documents(docs, config(docs))
        self.assertEqual([(c["start"], c["end"]) for c in chunks], [(0, 8), (8, 12)])

    def test_permission_identity_changes_even_when_trimmed_chunks_do_not(self):
        text = " allowed "
        docs = [{"document_id": "d", "researcher_id": "fixture", "content": text,
                 "content_sha256": sha256_text(text)}]
        cfg = config(docs)
        key = self.r.retrieval_cache_key(docs, cfg, self.decision, {"model": "fixture"})
        original = self.r.chunk_documents(docs, cfg)
        bundle = self.r.make_embedding_bundle(docs, cfg, self.decision, model="fixture-embedding",
                                              vectors=[[1, 0], [1, 0]], usage={"mode": "offline_fixture"})
        docs[0]["permitted_spans"] = [{"start": 1, "end": 8}]
        self.assertEqual(self.r.chunk_documents(docs, cfg), original)
        self.assertNotEqual(key, self.r.retrieval_cache_key(docs, cfg, self.decision, {"model": "fixture"}))
        with self.assertRaisesRegex(ValueError, "embedding"):
            self.r.rank_semantic(docs, dict(cfg, embedding_model="fixture-embedding", embedding_dimensions=2,
                                            embedding_bundle_sha256=bundle["bundle_sha256"]), self.decision, bundle)

    def test_packing_counts_json_and_unicode_and_retains_exact_prefix(self):
        text = "é中🙂" * 90
        chunk = {"document_id": "d", "start": 3, "end": 3 + len(text), "text": text}
        packed = self.r.pack_passages([chunk], 170)
        self.assertLessEqual(len(canonical_json(packed).encode()), 170)
        part = packed["passages"][0]
        self.assertEqual(part["text"], text[:part["end"] - 3])
        self.assertLess(part["end"], chunk["end"])
        self.assertEqual(self.r.pack_passages([chunk], 10), {"passages": []})

    def test_cache_identity_covers_options_model_sources_and_parameters(self):
        make = self.r.retrieval_cache_key
        base = make(self.docs, self.cfg, self.decision, {"model": "one"})
        variants = [
            make(self.docs, self.cfg, dict(self.decision, options=["exploration", "replication"]), {"model": "one"}),
            make(self.docs, self.cfg, self.decision, {"model": "two"}),
            make(self.docs, dict(self.cfg, chunk_chars=30), self.decision, {"model": "one"}),
            make(self.docs[:1], config(self.docs[:1]), self.decision, {"model": "one"})]
        self.assertTrue(all(value != base for value in variants))

    def test_labels_and_invalid_parameters_cannot_enter_query(self):
        with self.assertRaisesRegex(ValueError, "decision"):
            self.r.rank_lexical([], dict(self.decision, chosen="a"))
        for value in [0, -1, True, 1.5]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.r.chunk_documents(self.docs, dict(self.cfg, chunk_chars=value))

    def test_hybrid_packing_preserves_profile_and_both_budgets(self):
        chunks = self.r.chunk_documents(self.docs, self.cfg)
        profile = {"prose": "Prefer replication", "conditions": ["when uncertainty is high"]}
        result = self.r.pack_passages(chunks, 240, profile=profile, passage_cap=140)
        self.assertEqual(result["profile"], profile)
        self.assertLessEqual(len(canonical_json(result).encode()), 240)
        self.assertLessEqual(len(canonical_json({"passages": result["passages"]}).encode()), 140)

    def test_semantic_bundle_ranks_vectors_and_binds_exact_inputs(self):
        chunks = self.r.chunk_documents(self.docs, self.cfg)
        bundle = self.r.make_embedding_bundle(self.docs, self.cfg, self.decision,
                                              model="fixture-embedding", vectors=[[1, 0], [0, 1], [1, 0]],
                                              usage={"mode": "offline_fixture", "calls": 0})
        cfg = dict(self.cfg, embedding_model="fixture-embedding", embedding_dimensions=2,
                   embedding_bundle_sha256=bundle["bundle_sha256"])
        ranked = self.r.rank_semantic(self.docs, cfg, self.decision, bundle)
        self.assertEqual(ranked[0]["document_id"], "d2")
        self.assertEqual(ranked[1]["document_id"], "d1")
        for changed in [dict(self.decision, context="changed"),
                        dict(self.decision, options=list(reversed(self.decision["options"])) )]:
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "embedding"):
                self.r.rank_semantic(self.docs, cfg, changed, bundle)
        tampered = dict(bundle, vectors=[[1, 0], [1, 0], [0, 1]])
        with self.assertRaisesRegex(ValueError, "embedding"):
            self.r.rank_semantic(self.docs, cfg, self.decision, tampered)
        with self.assertRaisesRegex(ValueError, "embedding"):
            self.r.rank_semantic(self.docs, dict(cfg, embedding_model="different"), self.decision, bundle)

    def test_semantic_rejects_bad_vectors_without_silent_lexical_fallback(self):
        for vectors in [[[0, 0], [1, 0], [0, 1]], [[1, 0], [1], [0, 1]],
                        [[1, 0], [True, 0], [0, 1]], [[1, 0], [float("nan"), 0], [0, 1]],
                        [[1, 0], [10**1000, 0], [0, 1]],
                        [[1, 0], [1, 0]]]:
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                self.r.make_embedding_bundle(self.docs, self.cfg, self.decision,
                                              model="fixture-embedding", vectors=vectors,
                                              usage={"mode": "offline_fixture", "calls": 0})

    def test_semantic_ranking_preserves_direction_at_subnormal_scale(self):
        # d1 is exactly aligned with the query. d2 must remain second even
        # when its magnitude makes a raw L2 norm round at subnormal precision.
        for scale in [1.0, math.ulp(0.0), 1e300]:
            with self.subTest(scale=scale):
                bundle = self.r.make_embedding_bundle(
                    self.docs, self.cfg, self.decision, model="fixture-embedding",
                    vectors=[[1, 1], [1, 1], [scale, 2 * scale]],
                    usage={"mode": "offline_fixture", "calls": 0})
                cfg = dict(self.cfg, embedding_model="fixture-embedding", embedding_dimensions=2,
                           embedding_bundle_sha256=bundle["bundle_sha256"])
                ranked = self.r.rank_semantic(self.docs, cfg, self.decision, bundle)
                self.assertEqual([chunk["document_id"] for chunk in ranked], ["d1", "d2"])


if __name__ == "__main__":
    unittest.main()
