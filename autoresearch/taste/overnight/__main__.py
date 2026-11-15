"""Offline contract fixture. Live dispatch is only through an assigned manifest."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ...llm import LLM
from .contracts import build_profile, digest, sha256_text
from .consumer import PROMPT_VERSION, implementation_hash, predict_profile, prepare_payload
from .registry import register_builder


class FixtureBackend(LLM):
    name = "offline-fixture"
    model = "synthetic-v1"

    def complete(self, prompt, **kwargs):
        self.budget.charge(0, 0)
        return '{"probabilities":[0.25,0.75],"rationale":"Synthetic fixture only"}'


def fixture_builder(documents, config, extractor):
    return {"content": {"prose": "Prefer tests that distinguish hypotheses.",
                        "claims": [{"text": "Use matched controls", "source_ids": ["synthetic-fit-1"]}],
                        "conditions": [{"if": "uncertain", "then": "replicate"}]},
            "fit_usage": {"attempted_calls": 0, "cost_status": "offline"}}


def make_fixture():
    register_builder("synthetic-fixture", fixture_builder, prompt_version="synthetic-v1",
                     prompt_sha256=sha256_text("synthetic fixture; no extraction model"))
    content = "Synthetic author recommends matched controls."
    documents = [{"document_id": "synthetic-fit-1", "researcher_id": "synthetic",
                  "content": content, "content_sha256": sha256_text(content)}]
    allowed = [{"document_id": d["document_id"], "content_sha256": d["content_sha256"]} for d in documents]
    config = {"method_id": "synthetic-fixture", "researcher_id": "synthetic", "allowed_sources": allowed,
              "allowed_source_manifest_hash": digest(allowed), "personalization_cap": 2048,
              "replicate_id": 0, "code_sha": "offline-fixture-not-a-live-run", "extractor_settings": {}}
    backend = FixtureBackend()
    profile = build_profile(documents, config, backend)
    prediction_config = {"method_implementation_hash": profile.method_implementation_hash,
                         "renderer_implementation_hash": implementation_hash(),
                         "profile_prompt_version": profile.prompt_version,
                         "consumer_prompt_version": PROMPT_VERSION,
                         "settings": {"temperature": 0.0, "max_tokens": 128}}
    context, options = "Choose the next synthetic experiment.", ["Unmatched change", "Matched control"]
    prepared = prepare_payload(profile, context, options, prediction_config)
    prediction = predict_profile(profile, context, options, backend, prediction_config)
    return {"schema_version": "overnight-offline-fixture-v1", "status": "complete",
            "evidence_status": "plumbing_only_no_accuracy_evidence", "documents": documents,
            "profile": profile.to_dict(), "prediction_config": prediction_config,
            "prepared": prepared, "prediction": asdict(prediction)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fixture = sub.add_parser("fixture")
    fixture.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = make_fixture()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "complete", "artifact_sha256": sha256_text(args.output.read_text()),
                      "profile_id": result["profile"]["profile_id"]}))


if __name__ == "__main__":
    main()
