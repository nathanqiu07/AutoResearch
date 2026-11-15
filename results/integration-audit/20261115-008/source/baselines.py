"""Profile-study controls using the sole neutral-profile renderer.

Call register_baselines() once per worker process. Retrieval builds require a
label-free config['decision'] and consumer_identity. Reuse those profiles only
for that decision; predict_baseline checks the binding before the common consumer.
No builder here calls an LLM or fetches a source. Frozen summaries are reused,
not independently regenerated; semantic retrieval is explicitly unavailable.
"""
from . import retrieval
from .contracts import ProfileArtifact, canonical_json, digest, render_content, validate_documents


VERSION = "baseline-controls-v1"
METHODS = ("no_profile", "name_only", "raw_evidence", "lexical_retrieval",
           "semantic_retrieval", "memory_summary", "profile_retrieval")


def _result(content=None, status="complete", error=None, **usage):
    return {"content": content, "status": status, "error_code": error,
            "fit_usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                          "cost_usd": 0, "cost_status": "no_model_calls", **usage}}


def _frozen(config):
    body = config.get("frozen_profile")
    required = ("profile_id", "method_id", "researcher_id", "allowed_source_manifest_hash",
                "renderer_implementation_hash", "content_sha256")
    if (not isinstance(body, dict)
            or any(not isinstance(body.get(key), str) or not body[key] for key in required)
            or not isinstance(body.get("fit_usage"), dict)):
        return None, "missing_or_invalid_frozen_profile"
    try:
        profile = ProfileArtifact.from_dict(body)
    except (ValueError, TypeError, KeyError):
        return None, "missing_or_invalid_frozen_profile"
    if (profile.profile_id != config.get("expected_profile_id")
            or profile.researcher_id != config["researcher_id"]
            or profile.allowed_source_manifest_hash != config["allowed_source_manifest_hash"]):
        return None, "frozen_profile_identity_or_sources_mismatch"
    from .consumer import implementation_hash
    if profile.renderer_implementation_hash != implementation_hash():
        return None, "frozen_renderer_mismatch"
    if profile.status != "complete" or not render_content(profile.content):
        return None, "frozen_profile_not_complete"
    return profile, None


def build_baseline(documents, config, extractor):
    validate_documents(documents, config)
    method, cap = config["method_id"], config["personalization_cap"]
    if method == "no_profile":
        return _result()
    if method == "name_only":
        name = config.get("researcher_name")
        if not isinstance(name, str) or not name.strip():
            return _result(status="unavailable", error="researcher_name_required")
        return _result({"name": name})
    if method == "semantic_retrieval":
        return _result(status="unavailable", error="embedding_backend_not_configured")
    profile = None
    if method in {"memory_summary", "profile_retrieval"}:
        profile, error = _frozen(config)
        if error:
            return _result(status="unavailable", error=error)
        if method == "memory_summary":
            if profile.method_id != config.get("summary_method_id"):
                return _result(status="unavailable", error="frozen_summary_method_mismatch")
            if len(render_content(profile.content).encode("utf-8")) > cap:
                return _result(status="unavailable", error="frozen_summary_exceeds_cap")
            return _result(profile.content, reused_profile_id=profile.profile_id,
                           reused_content_sha256=profile.content_sha256,
                           original_fit_usage=profile.fit_usage)
    chunks = retrieval.chunk_documents(documents, config)
    usage = {"retrieval_implementation_hash": retrieval.implementation_hash(),
             "available_chunks": len(chunks)}
    if method in {"lexical_retrieval", "profile_retrieval"}:
        key = retrieval.retrieval_cache_key(documents, config, config.get("decision"),
                                            config.get("consumer_identity"))
        chunks = retrieval.rank_lexical(chunks, config["decision"])
        chunks = chunks[:retrieval.positive_int(config.get("top_k", 5), "top_k")]
        usage.update(retrieval_cache_key=key, decision_sha256=digest(config["decision"]))
    elif method != "raw_evidence":
        raise ValueError("unknown baseline method")
    if profile is None:
        content = retrieval.pack_passages(chunks, cap)
    else:
        allocation = retrieval.positive_int(config.get("profile_cap"), "profile_cap")
        if allocation >= cap or len(render_content(profile.content).encode("utf-8")) > allocation:
            return _result(status="unavailable", error="frozen_profile_exceeds_allocation")
        content = retrieval.pack_passages(chunks, cap, profile=profile.content, passage_cap=cap - allocation)
        usage.update(reused_profile_id=profile.profile_id, profile_cap=allocation,
                     passage_cap=cap - allocation, original_fit_usage=profile.fit_usage)
    if not content["passages"]:
        return _result(status="unavailable", error="no_approved_passage_fits", **usage)
    return _result(content, selected_passages=len(content["passages"]), **usage)


def registration_metadata():
    # Registry pins this module. Include the imported retrieval policy in its
    # prompt/policy digest too, so changed helper bytes yield a different arm.
    policy = {"version": VERSION, "retrieval_hash": retrieval.implementation_hash(),
              "query": "context_and_ordered_options_only", "cap": "utf8-bytes-upper-bound-v1"}
    return [{"method_id": method, "prompt_version": VERSION,
             "prompt_sha256": digest(dict(policy, method_id=method)),
             "allows_empty": method == "no_profile"} for method in METHODS]


def register_baselines():
    from .registry import register_builder
    return [register_builder(function=build_baseline, **metadata) for metadata in registration_metadata()]


def predict_baseline(profile, context, options, consumer, config):
    from .consumer import ProfileFailure, predict_profile
    if profile.method_id in {"lexical_retrieval", "profile_retrieval"}:
        decision = {"context": context, "options": list(options)}
        if canonical_json(profile.config.get("decision")) != retrieval.decision_query(decision):
            raise ProfileFailure("unavailable", "retrieved_profile_decision_mismatch")
    return predict_profile(profile, context, options, consumer, config)
