"""Synthetic-only offline assembly tests; never invokes the producer or a model."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from autoresearch.taste.overnight.contracts import digest, source_manifest, sha256_text
from autoresearch.taste.overnight import retrieval

SCRIPT = Path(__file__).with_name("assemble_embeddings.py")


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture():
    docs = [{"document_id": "d1", "researcher_id": "synthetic", "content": "Approved evidence.",
             "content_sha256": sha256_text("Approved evidence.")}]
    manifest = source_manifest(docs)
    items = [{"item_id": "i1", "option_order_id": "o1", "researcher_id": "synthetic",
              "context": "First decision", "options": ["left", "right"]},
             {"item_id": "i2", "option_order_id": "o1", "researcher_id": "synthetic",
              "context": "Second decision", "options": ["up", "down"]}]
    release = {"schema_version": "released-development-v2", "researcher_id": "synthetic",
               "items": items, "items_sha256": digest(items), "sources": {
                   "documents": docs, "source_manifest": manifest,
                   "allowed_source_manifest_hash": digest(manifest)}}
    # Hand-ordered unique batch: first query, shared chunk, second query.
    decisions = [{"context": i["context"], "options": i["options"]} for i in items]
    queries = [json.dumps(d, sort_keys=True, separators=(",", ":")) for d in decisions]
    inputs = [queries[0], "Approved evidence.", queries[1]]
    settings = {"model": "text-embedding-3-small", "dimensions": 2, "encoding_format": "float"}
    request = dict(settings, input=inputs)
    mappings = [{"item_id": item["item_id"], "option_order_id": item["option_order_id"],
                 "decision_sha256": digest(decision), "response_indices": indices,
                 "ordered_logical_input_hashes": [sha256_text(inputs[j]) for j in indices]}
                for item, decision, indices in zip(items, decisions, [[0, 1], [2, 1]])]
    records = [{"index": j, "input_sha256": sha256_text(value), "utf8_bytes": len(value.encode()),
                "roles": ([{"kind": "approved_chunk", "chunk_index": 0}] if j == 1 else
                          [{"kind": "decision_query", "decision_sha256": digest(decisions[j // 2])}])}
               for j, value in enumerate(inputs)]
    batch = {"researcher_id": "synthetic", "release_sha256": sha(encoded(release)),
             "release_semantic_sha256": digest(release), "allowed_source_manifest_hash": digest(manifest),
             "items_sha256": digest(items), "staged_request_basename": "synthetic-request.json",
             "request_sha256": sha(encoded(request)), "settings_sha256": digest(settings),
             "ordered_input_sha256": digest(inputs), "n_inputs": 3,
             "input_text_utf8_bytes": sum(len(s.encode()) for s in inputs),
             "max_input_utf8_bytes": max(len(s.encode()) for s in inputs),
             "n_decision_bundles": 2, "input_records": records, "decision_mappings": mappings}
    proposal = {"schema_version": "embedding-production-proposal-v1",
                "retrieval_implementation_hash": retrieval.implementation_hash(),
                "candidate_settings": settings, "batches": [batch]}
    proposal["proposal_sha256"] = digest(proposal)
    # Response order differs from input order deliberately.
    vectors = [{"index": 2, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]},
               {"index": 1, "embedding": [1, 1]}]
    response = {"object": "list", "model": settings["model"], "data": vectors,
                "usage": {"prompt_tokens": 12, "total_tokens": 12}}
    receipt = {"schema_version": "bounded-embedding-receipt-v1", "status": "complete",
               "request_id": "producer-synthetic", **settings, "count": 3,
               "input_sha256": digest(inputs), "packet_sha256": sha(encoded(request)),
               "response_sha256": sha(encoded(response)), "usage": {"prompt_tokens": 12, "total_tokens": 12,
                   "known_input_tokens": 12, "complete": True}, "known_usage_usd": 0.00000024,
               "script_sha256": "a" * 64, "runtime_commit": "b" * 40,
               "vectors": copy.deepcopy(list(reversed(vectors)))}
    return {"proposal": proposal, "release": release, "request": request, "receipt": receipt, "response": response}


class AssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SCRIPT.exists():
            spec = importlib.util.spec_from_file_location("embedding_assembly", SCRIPT)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "offline assembler has not been implemented")
        self.values = fixture()

    def assemble(self, values=None, hashes=None):
        raw = {key: encoded(value) for key, value in (values or self.values).items()}
        return self.module.assemble(**{key + "_bytes": value for key, value in raw.items()},
                                    expected_hashes=hashes or {key: sha(value) for key, value in raw.items()})

    def repin(self):
        values = self.values
        batch = values["proposal"]["batches"][0]
        batch["release_sha256"] = sha(encoded(values["release"]))
        batch["release_semantic_sha256"] = digest(values["release"])
        batch["request_sha256"] = sha(encoded(values["request"]))
        values["receipt"]["response_sha256"] = sha(encoded(values["response"]))
        proposal = values["proposal"]
        proposal["proposal_sha256"] = digest({k: v for k, v in proposal.items() if k != "proposal_sha256"})

    def test_reordered_response_and_receipt_indices_map_each_decision(self):
        bundles, manifest = self.assemble()
        self.assertEqual([b["vectors"] for b in bundles], [[[1, 0], [1, 1]], [[0, 1], [1, 1]]])
        self.assertEqual([b["usage"]["response_indices"] for b in bundles], [[0, 1], [2, 1]])
        references = [b["usage"]["production_usage_reference"] for b in bundles]
        self.assertEqual(references[0], references[1])
        self.assertEqual(references[0]["receipt_sha256"], sha(encoded(self.values["receipt"])))
        self.assertTrue(all("known_usage_usd" not in b["usage"] for b in bundles))
        self.assertEqual(manifest["model_calls"], 0)
        self.assertNotIn("First decision", json.dumps(manifest))
        self.assertNotIn("Approved evidence", json.dumps(manifest))

    def test_duplicate_missing_or_out_of_range_response_indices_are_rejected(self):
        for indices in [[0, 0, 2], [0, 1], [0, 1, 3], [False, 1, 2]]:
            with self.subTest(indices=indices):
                self.values = fixture()
                self.values["response"]["data"] = [{"index": i, "embedding": [1, 1]} for i in indices]
                self.repin()
                with self.assertRaises(ValueError):
                    self.assemble()

    def test_receipt_vector_mismatch_is_rejected_even_with_matching_file_hashes(self):
        self.values["receipt"]["vectors"][0]["embedding"] = [9, 9]
        with self.assertRaises(ValueError):
            self.assemble()

    def test_wrong_source_query_or_index_mapping_is_rejected(self):
        for mutation in ["source", "query", "mapping"]:
            with self.subTest(mutation=mutation):
                self.values = fixture()
                if mutation == "source":
                    self.values["release"]["sources"]["documents"][0]["content"] = "Foreign text"
                elif mutation == "query":
                    items = self.values["release"]["items"]
                    items[0]["context"] = "Foreign decision"
                    self.values["release"]["items_sha256"] = digest(items)
                    self.values["proposal"]["batches"][0]["items_sha256"] = digest(items)
                else:
                    self.values["proposal"]["batches"][0]["decision_mappings"][0]["response_indices"] = [2, 1]
                self.repin()
                with self.assertRaises(ValueError):
                    self.assemble()

    def test_external_hash_and_stale_helper_are_rejected(self):
        hashes = {k: sha(encoded(v)) for k, v in self.values.items()}
        for key in hashes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.assemble(hashes=dict(hashes, **{key: "0" * 64}))
        self.values["proposal"]["retrieval_implementation_hash"] = "0" * 64
        self.repin()
        with self.assertRaises(ValueError):
            self.assemble()

    def test_incomplete_status_settings_and_usage_are_rejected(self):
        for changes in [{"status": "uncertain"}, {"dimensions": 3}, {"encoding_format": "base64"},
                        {"model": "different"}, {"usage": {"complete": False}}, {"count": 4}]:
            with self.subTest(changes=changes):
                self.values = fixture()
                self.values["receipt"].update(changes)
                with self.assertRaises(ValueError):
                    self.assemble()

    def test_receipt_requires_producer_implementation_provenance(self):
        for field in ["script_sha256", "runtime_commit"]:
            with self.subTest(field=field):
                self.values = fixture()
                self.values["receipt"].pop(field)
                with self.assertRaises(ValueError):
                    self.assemble()

    def test_receipt_indices_and_unmapped_extra_inputs_are_rejected(self):
        self.values["receipt"]["vectors"][0]["index"] = self.values["receipt"]["vectors"][1]["index"]
        with self.assertRaises(ValueError):
            self.assemble()
        self.values = fixture()
        self.values["proposal"]["batches"][0]["input_records"][0]["roles"] = []
        self.repin()
        with self.assertRaises(ValueError):
            self.assemble()

    def test_cli_writes_exclusive_bundles_and_hash_only_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            command = [sys.executable, str(SCRIPT)]
            for key, value in self.values.items():
                path = root / (key + ".json")
                raw = encoded(value)
                path.write_bytes(raw)
                command.extend(["--" + key, str(path), "--" + key + "-sha256", sha(raw)])
            output = root / "assembled"
            command.extend(["--output-dir", str(output)])
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(len(manifest["bundles"]), 2)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            for entry in manifest["bundles"]:
                self.assertEqual(sha((output / entry["file"]).read_bytes()), entry["file_sha256"])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})


if __name__ == "__main__":
    unittest.main()
