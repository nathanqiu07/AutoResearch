"""Write an exclusive synthetic control packet; no credentials/network needed."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from autoresearch.taste.overnight.baselines import predict_baseline, register_baselines
from autoresearch.taste.overnight.contracts import build_profile, digest, sha256_text, source_manifest
from autoresearch.taste.overnight.consumer import PROMPT_VERSION, ProfileFailure, implementation_hash, prepare_payload
from autoresearch.taste.overnight.registry import register_builder


class FixtureBackend:
    label, model = "offline-synthetic", "fixture-v1"

    def complete(self, prompt, **settings):
        return '{"probabilities":[0.4,0.6],"rationale":"Synthetic plumbing response; no accuracy claim."}'


def fixture_summary(documents, config, extractor):
    return {"content": {"prose": "Prefer replicated experiments when comparing explanations."},
            "fit_usage": {"calls": 0, "cost_status": "synthetic_fixture"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    register_baselines()
    register_builder("fixture_plain_summary", fixture_summary, prompt_version="fixture-v1", prompt_sha256="f" * 64)
    docs = [{"document_id": key, "researcher_id": "synthetic", "content": content,
             "content_sha256": sha256_text(content)} for key, content in
            [("fit-a", "I compare apples and oranges when choosing snacks."),
             ("fit-b", "When comparing explanations, I prefer replicated experiments and matched controls.")]]
    sources = source_manifest(docs)
    decision = {"context": "Choose the next experiment.", "options": ["Replicate a discriminating test.", "Collect unrelated examples."]}
    config = {"researcher_id": "synthetic", "allowed_sources": sources,
              "allowed_source_manifest_hash": digest(sources), "personalization_cap": 512,
              "replicate_id": 0, "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "extractor_settings": {}, "decision": decision,
              "consumer_identity": {"model": "fixture-v1"}, "researcher_name": "Synthetic Researcher",
              "chunk_chars": 1200, "top_k": 5, "summary_method_id": "fixture_plain_summary"}
    backend = FixtureBackend()
    summary = build_profile(docs, dict(config, method_id="fixture_plain_summary"), backend)
    records = []
    for method in ("no_profile", "name_only", "raw_evidence", "lexical_retrieval", "semantic_retrieval", "memory_summary", "profile_retrieval"):
        cfg = dict(config, method_id=method)
        if method in {"memory_summary", "profile_retrieval"}:
            cfg.update(frozen_profile=summary.to_dict(), expected_profile_id=summary.profile_id, profile_cap=128)
        profile = build_profile(docs, cfg, backend)
        consumer_config = {"method_implementation_hash": profile.method_implementation_hash,
                           "renderer_implementation_hash": implementation_hash(),
                           "profile_prompt_version": profile.prompt_version,
                           "consumer_prompt_version": PROMPT_VERSION,
                           "settings": {"temperature": 0.0, "max_tokens": 128}}
        result = {"method": method, "profile": profile.to_dict()}
        try:
            prepared = prepare_payload(profile, decision["context"], decision["options"], consumer_config)
            pred = predict_baseline(profile, decision["context"], decision["options"], backend, consumer_config)
            result.update(status="complete", payload=prepared["payload"], payload_sha256=prepared["payload_sha256"],
                          prediction=pred.__dict__)
        except ProfileFailure as exc:
            result.update(status=exc.status, error_code=exc.code)
        records.append(result)
    packet = {"mode": "offline_synthetic_fixture", "scientific_accuracy": "not_measured",
              "code_sha": config["code_sha"], "sources": docs, "records": records}
    with Path(args.output).open("x") as output:
        json.dump(packet, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    print(json.dumps({"methods": len(records), "statuses": {r["method"]: r["status"] for r in records},
                      "output_sha256": sha256_text(Path(args.output).read_text())}))


if __name__ == "__main__":
    main()
