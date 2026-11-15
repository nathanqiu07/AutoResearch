#!/usr/bin/env python3
"""Independent offline provenance fix retest using released synthetic data only.

Writes only beneath a new output directory. Never edits the audited snapshot.
No external backend is imported or constructed by the audit probes.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
BUILDER_CALLS = []


def counted_builder(documents, config, extractor):
    BUILDER_CALLS.append({"documents": copy.deepcopy(documents), "config": copy.deepcopy(config)})
    return {"content": {"prose": "Synthetic profile.", "source_ids": [d["document_id"] for d in documents]}}


def mutating_builder(documents, config, extractor):
    from autoresearch.taste.overnight.contracts import digest
    BUILDER_CALLS.append({"documents": copy.deepcopy(documents), "config_before": copy.deepcopy(config)})
    config["allowed_sources"] = []
    config["allowed_source_manifest_hash"] = digest([])
    config["researcher_id"] = "changed-by-builder"
    config["extractor_settings"]["audit_mutation"] = {"changed": True}
    return {"content": {"prose": documents[0]["content"], "source_ids": [documents[0]["document_id"]]}}


class RecordingOnly:
    label = "independent-offline-audit"
    model = "fixed-synthetic-response"
    base_url = ""

    def __init__(self):
        self.calls = []

    def complete(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, "settings": kwargs})
        return '{"probabilities":[0.25,0.75],"rationale":"Synthetic audit only"}'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--shared-contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prior-report", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root))
    from autoresearch.taste.overnight import contracts as c, registry as r
    from autoresearch.taste.overnight.consumer import predict_profile

    metadata = json.loads((root / "AUDIT_SOURCE.json").read_text())
    before = {name: sha(root / name) for name in metadata["files"]}
    fixture_path = root / "docs/overnight/gio-profile-20261115/infrastructure/fixture-v3.json"
    fixture = json.loads(fixture_path.read_text())
    (out / "fixture-input.json").write_bytes(fixture_path.read_bytes())
    (out / "shared-contract.md").write_bytes(args.shared_contract.read_bytes())
    observations = {}

    def record(name, expected, action, valid):
        try:
            value = action()
            observation = {"returned": True, "value": value}
        except Exception as exc:
            observation = {"returned": False, "exception": type(exc).__name__, "message": str(exc),
                           "failure_status": getattr(exc, "status", None), "failure_code": getattr(exc, "code", None)}
        observation["expected"] = expected
        observation["assessment"] = "verified" if valid(observation) else "failed"
        observations[name] = observation

    r.register_builder("audit-counted", counted_builder, prompt_version="audit-v1", prompt_sha256="a" * 64)
    base_config = copy.deepcopy(fixture["profile"]["config"])
    base_config["method_id"] = "audit-counted"
    docs = copy.deepcopy(fixture["documents"])

    def build_case(changed_docs, changes=None):
        start = len(BUILDER_CALLS)
        try:
            profile = c.build_profile(changed_docs, dict(base_config, **(changes or {})), RecordingOnly())
            return {"accepted": True, "builder_calls": len(BUILDER_CALLS) - start, "profile": profile.to_dict()}
        except Exception as exc:
            return {"accepted": False, "builder_calls": len(BUILDER_CALLS) - start,
                    "exception": type(exc).__name__, "message": str(exc)}

    rejected_before_builder = lambda o: o["returned"] and not o["value"]["accepted"] and o["value"]["builder_calls"] == 0
    accepted_once = lambda o: o["returned"] and o["value"]["accepted"] and o["value"]["builder_calls"] == 1
    record("approved_exact_source", "Accept released approved set exactly once", lambda: build_case(docs), accepted_once)
    variants = {"missing_source": [], "duplicate_source": docs + copy.deepcopy(docs)}
    extra = copy.deepcopy(docs[0]); extra["document_id"] = "synthetic-unapproved-extra"
    variants["extra_source"] = docs + [extra]
    changed = copy.deepcopy(docs); changed[0]["content"] += " Changed synthetic text."
    variants["changed_content_stale_hash"] = changed
    updated = copy.deepcopy(changed); updated[0]["content_sha256"] = c.sha256_text(updated[0]["content"])
    variants["changed_content_updated_hash_stale_allowlist"] = updated
    for name, changed_docs in variants.items():
        record(name, "Reject before builder", lambda d=changed_docs: build_case(d), rejected_before_builder)
    record("source_manifest_hash_mismatch", "Reject before builder",
           lambda: build_case(docs, {"allowed_source_manifest_hash": "0" * 64}), rejected_before_builder)
    peers = copy.deepcopy(docs); peers[0]["researcher_id"] = "synthetic-peer"
    for name, flag, predicate in [("peer_false", False, rejected_before_builder),
                                   ("peer_true", True, accepted_once),
                                   ("peer_string_false", "false", rejected_before_builder),
                                   ("peer_integer_one", 1, rejected_before_builder)]:
        record(name, "Boolean true alone grants explicit peer-bundle approval",
               lambda f=flag: build_case(peers, {"approved_peer_sources": f}), predicate)

    # Document order is irrelevant; the allowlist itself must be canonical.
    two = docs + [extra]
    two_sources = c.source_manifest(two)
    two_config = {"allowed_sources": two_sources, "allowed_source_manifest_hash": c.digest(two_sources)}
    record("reordered_documents", "Accept same source set in another delivery order",
           lambda: build_case(list(reversed(two)), two_config), accepted_once)
    record("unsorted_allowlist", "Reject noncanonical allowlist before builder",
           lambda: build_case(two, dict(two_config, allowed_sources=list(reversed(two_sources)))), rejected_before_builder)

    profile_body = copy.deepcopy(fixture["profile"])
    record("released_profile_hashes", "Accept original fixture content/profile hashes",
           lambda: c.ProfileArtifact.from_dict(profile_body).profile_id, lambda o: o["returned"])
    record("configuration_digest_at_build", "Build config_id equals digest(config)",
           lambda: profile_body["config_id"] == c.digest(profile_body["config"]), lambda o: o["returned"] and o["value"])

    def rehash(body):
        body.pop("profile_id", None)
        body["profile_id"] = c.digest(body)
        return body

    changed_content = copy.deepcopy(profile_body); changed_content["content"]["prose"] = "Changed synthetic claim."
    record("content_tamper_without_hashes", "Reject corrupted content",
           lambda: c.ProfileArtifact.from_dict(changed_content).profile_id, lambda o: not o["returned"])
    rehashed_outer_only = rehash(copy.deepcopy(changed_content))
    record("content_hash_stale_outer_rehashed", "Reject stale content hash even after outer hash recomputation",
           lambda: c.ProfileArtifact.from_dict(rehashed_outer_only).profile_id, lambda o: not o["returned"])
    config_tamper = copy.deepcopy(profile_body); config_tamper["config"]["replicate_id"] = 999
    record("config_tamper_without_outer_rehash", "Reject corrupted outer profile",
           lambda: c.ProfileArtifact.from_dict(config_tamper).profile_id, lambda o: not o["returned"])
    stale_config_id = rehash(copy.deepcopy(config_tamper))
    record("config_digest_stale_outer_rehashed", "Reject internally stale config_id independently of outer checksum",
           lambda: c.ProfileArtifact.from_dict(stale_config_id).to_dict(), lambda o: not o["returned"])
    inconsistent_source_hash = copy.deepcopy(profile_body)
    inconsistent_source_hash["allowed_source_manifest_hash"] = "0" * 64
    record("source_hash_disagrees_with_config", "Reject duplicated source hash inconsistent with config",
           lambda: c.ProfileArtifact.from_dict(rehash(inconsistent_source_hash)).to_dict(), lambda o: not o["returned"])

    # Builders must not be able to rewrite already-approved provenance by mutation.
    r.register_builder("audit-mutating", mutating_builder, prompt_version="audit-v1", prompt_sha256="b" * 64)
    record("builder_mutates_approved_provenance", "Reject mutation or retain original approved config/source/researcher",
           lambda: build_case(docs, {"method_id": "audit-mutating"}),
           lambda o: o["returned"] and (not o["value"]["accepted"] or
             (o["value"]["profile"]["allowed_source_manifest_hash"] == base_config["allowed_source_manifest_hash"]
              and o["value"]["profile"]["researcher_id"] == base_config["researcher_id"]
              and o["value"]["profile"]["config"] == dict(base_config, method_id="audit-mutating")
              and o["value"]["profile"]["extractor_settings"] == base_config["extractor_settings"])))

    # Verify the declared method/prompt/renderer equality guards; never use a live consumer.
    def accepted_pins():
        backend = RecordingOnly()
        prediction = predict_profile(c.ProfileArtifact.from_dict(profile_body), "Synthetic question", ["A", "B"],
                                     backend, fixture["prediction_config"])
        return {"choice": prediction.choice, "probabilities": prediction.probabilities,
                "calibrated": prediction.calibrated, "consumer_calls": len(backend.calls)}
    record("runtime_pins_match_fixture", "Accept current declared pins using one synthetic consumer call", accepted_pins,
           lambda o: o["returned"] and o["value"]["consumer_calls"] == 1 and o["value"]["choice"] == "b"
           and o["value"]["probabilities"] == [.25, .75] and o["value"]["calibrated"] is False)
    for key in ("method_implementation_hash", "renderer_implementation_hash", "profile_prompt_version", "consumer_prompt_version"):
        backend = RecordingOnly()
        cfg = dict(fixture["prediction_config"], **{key: "different"})
        def pin_case(cfg=cfg, backend=backend):
            try:
                predict_profile(c.ProfileArtifact.from_dict(profile_body), "Synthetic question", ["A", "B"], backend, cfg)
                return {"rejected": False, "consumer_calls": len(backend.calls)}
            except Exception as exc:
                return {"rejected": True, "consumer_calls": len(backend.calls), "exception": type(exc).__name__,
                        "status": getattr(exc, "status", None), "code": getattr(exc, "code", None)}
        record("runtime_pin:" + key, "Reject mismatch before consumer call", pin_case,
               lambda o: o["returned"] and o["value"]["rejected"] and o["value"]["consumer_calls"] == 0
               and o["value"]["status"] == "unavailable")

    current_builder = r.get_builder("audit-counted")
    record("registry_hash_matches_current_module", "Registration hash equals current builder module bytes",
           lambda: current_builder.implementation_hash == sha(Path(__file__)), lambda o: o["returned"] and o["value"])
    for field, changes in [("version", {"prompt_version": "changed"}), ("sha", {"prompt_sha256": "c" * 64})]:
        kwargs = dict(prompt_version="audit-v1", prompt_sha256="a" * 64, **{})
        kwargs.update(changes)
        record("duplicate_registration_prompt_" + field, "Reject changed prompt declaration for registered method",
               lambda kw=kwargs: r.register_builder("audit-counted", counted_builder, **kw).method_id,
               lambda o: not o["returned"] and o["exception"] == "ValueError")
    record("malformed_prompt_hash", "Reject non-SHA256 prompt metadata",
           lambda: r.register_builder("audit-bad-hash", counted_builder, prompt_version="audit-v1", prompt_sha256="bad").method_id,
           lambda o: not o["returned"] and o["exception"] == "ValueError")

    for key, value in {
        "frozen_import_assumption": "Registry implementation is unchanged; prior self-generated stale-import demonstration was not repeated. Loaded runtime source must remain frozen before import and execution.",
        "prompt_hash_matches_actual_extractor_request": "Prompt SHA is caller-declared metadata; registry validates format/duplicate identity, not correspondence to callable requests.",
        "transitive_builder_dependencies": "Only defining module bytes are hashed; a complete dependency fingerprint is not verified by this audit.",
        "evaluator_approval_authority": "Allowlist is validated against caller config, not an external evaluator signature or frozen job manifest; runner milestone is outside this contract audit.",
        "document_metadata_provenance": "Exact approved source matching covers document_id/content_sha256, not all extra metadata fields. Real metadata/attribution validity was not tested.",
    }.items():
        observations[key] = {"assessment": "unverified", "reason": value}

    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "tests.test_overnight_contracts"],
                           cwd=root, capture_output=True, text=True)
    (out / "existing-tests.stdout.txt").write_text(tests.stdout)
    (out / "existing-tests.stderr.txt").write_text(tests.stderr)
    after = {name: sha(root / name) for name in metadata["files"]}
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root), "source_commit": metadata["source_commit"],
        "implementation_commit": metadata["implementation_commit"],
        "fixture_sha256": sha(fixture_path),
        "expected_fixture_sha256": "cb6e8beecb6976e837be5d588471d0f5ac5c45cd4df02533b31bcabb640127e7",
        "shared_contract_sha256": sha(args.shared_contract),
        "audit_script_sha256": sha(Path(__file__)),
        "source_files_match_published_manifest": before == metadata["files"],
        "source_files_unchanged": before == after, "source_file_hashes": before,
        "argv": sys.argv, "cwd": str(Path.cwd()), "python": sys.version,
        "existing_tests": {"argv": [sys.executable, "-B", "-m", "unittest", "tests.test_overnight_contracts"],
                           "cwd": str(root), "exit_code": tests.returncode,
                           "stdout": "existing-tests.stdout.txt", "stderr": "existing-tests.stderr.txt"},
        "external_model_calls": 0, "observations": observations,
    }
    prior = json.loads(args.prior_report.read_text())
    (out / "prior_observations.json").write_bytes(args.prior_report.read_bytes())
    original_failed = ["builder_mutates_approved_provenance", "config_digest_stale_outer_rehashed",
                       "source_hash_disagrees_with_config", "peer_string_false", "peer_integer_one"]
    report["prior_report_sha256"] = sha(args.prior_report)
    report["prior_source_commit"] = prior["source_commit"]
    report["retested_original_failures"] = {name: {"before": prior["observations"][name]["assessment"],
                                                  "after": observations[name]["assessment"]}
                                           for name in original_failed}
    report["counts"] = {status: sum(v["assessment"] == status for v in observations.values())
                        for status in ("verified", "failed", "unverified")}
    (out / "observations.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(out), "counts": report["counts"],
                      "sources_unchanged": report["source_files_unchanged"], "existing_tests_exit": tests.returncode}, indent=2))
    return 0 if (report["source_files_unchanged"] and before == metadata["files"]
                 and tests.returncode == 0 and report["counts"]["failed"] == 0
                 and report["fixture_sha256"] == report["expected_fixture_sha256"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
