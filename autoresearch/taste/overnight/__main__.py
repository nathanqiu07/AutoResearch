"""Offline contract fixture. Live dispatch is only through an assigned manifest."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ...llm import LLM
from .contracts import backend_identity, build_profile, digest, sha256_text, ProfileArtifact
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
    job_fixture = sub.add_parser("job-fixture")
    job_fixture.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = make_fixture()
    if args.command == "job-fixture":
        from .runner import job_id, run_job, public_handoff
        profile = ProfileArtifact.from_dict(result["profile"])
        backend = FixtureBackend()
        items = [{"item_id": "synthetic-dev-1", "researcher_id": "synthetic",
                  "context": result["prepared"]["payload"]["context"],
                  "options": result["prepared"]["payload"]["options"], "option_order_id": "ab"}]
        manifest = {"schema_version": "overnight-job-v1", "campaign_id": "offline-fixture",
                    "stage": "offline", "kind": "predict", "contract_sha256": "0b42ad9e75a5cc729978b1b000ff901646f91f8813e1abb2fb6415fb604cfd43",
                    "config_hash": digest(result["prediction_config"]), "source_manifest_hash": profile.allowed_source_manifest_hash,
                    "items_hash": digest(items), "profile_hash": profile.profile_id, "method_id": profile.method_id,
                    "extractor": profile.extractor, "consumer": backend_identity(backend),
                    "personalization_cap": profile.personalization_cap, "option_order_schedule": [{"item_id": "synthetic-dev-1", "option_order_id": "ab"}],
                    "replicate_id": 0, "code_sha": "offline-fixture-not-a-live-run",
                    "allocation": {"max_calls": 1, "max_seconds": 30, "max_usd": 0, "cost_mode": "offline", "authorization_source": "offline-fixture"},
                    "retry_policy": {"max_attempts": 1, "retry_uncertain": False}, "parent_job_ids": [], "expected_outputs": ["result.json", "traces"]}
        manifest["job_id"] = job_id(manifest)
        lease = {"job_id": manifest["job_id"], "lease_id": "offline-fixture", "owner": "offline-fixture", "expires_at": "2099-01-01T00:00:00+00:00"}
        completed = run_job(manifest, lease, output_root=args.output_root / "outputs", lease_root=args.output_root / "leases",
                            cache_root=args.output_root / "cache", profile=profile, items=items,
                            config=result["prediction_config"], consumer=backend)
        print(json.dumps(public_handoff(completed), indent=2))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "complete", "artifact_sha256": sha256_text(args.output.read_text()),
                      "profile_id": result["profile"]["profile_id"]}))


if __name__ == "__main__":
    main()
