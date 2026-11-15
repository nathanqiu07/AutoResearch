"""One leased immutable job, with explicit attempts and no automatic retries.

Callers must supply the coordinator's canonical lease_root across all clones.
This is cooperative enforcement on one filesystem, not a distributed scheduler
or an authorization service. Never infer authorization from an idle worker.
"""
import json
import math
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .contracts import (backend_identity, build_profile, canonical_json, digest,
                        ProfileArtifact, sha256_text, validate_documents)
from .consumer import ProfileFailure, predict_profile, prepare_payload


MUTABLE_FIELDS = {"job_id", "lease", "created_at", "updated_at"}
ITEM_FIELDS = {"item_id", "researcher_id", "context", "options", "option_order_id"}
REQUIRED = {"schema_version", "campaign_id", "stage", "kind", "contract_sha256",
            "config_hash", "source_manifest_hash", "items_hash", "profile_hash", "method_id",
            "extractor", "consumer", "personalization_cap", "option_order_schedule", "replicate_id",
            "code_sha", "allocation", "retry_policy", "parent_job_ids", "expected_outputs", "job_id"}


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed


def job_id(manifest):
    return digest({key: value for key, value in manifest.items() if key not in MUTABLE_FIELDS})


def cache_key(manifest, prompt, settings):
    return digest({"manifest": {k: v for k, v in manifest.items() if k not in MUTABLE_FIELDS},
                   "prompt": prompt, "settings": settings})


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return sha256_text(path.read_text(encoding="utf-8"))


def require_private_path(path, private_root):
    if private_root is None:
        raise ValueError("confirmation private root is required")
    resolved, root = Path(path).resolve(), Path(private_root).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError("confirmation output/cache must remain inside private root") from None
    return resolved


def _validate(manifest, lease, config, profile, items, documents):
    if REQUIRED - set(manifest):
        raise ValueError("job manifest is missing required fields")
    if manifest["schema_version"] != "overnight-job-v1" or manifest["stage"] not in ("offline", "dev", "confirmation"):
        raise ValueError("unsupported job schema or stage")
    if manifest["job_id"] != job_id(manifest):
        raise ValueError("semantic job hash mismatch")
    if not isinstance(lease, dict) or lease.get("job_id") != manifest["job_id"] or not lease.get("lease_id") or not lease.get("owner"):
        raise ValueError("coordinator execution lease required")
    try:
        expires = timestamp(lease["expires_at"])
        if expires <= utc_now():
            raise ValueError("execution lease expired")
    except (TypeError, KeyError):
        raise ValueError("execution lease requires UTC expiry") from None
    if manifest["stage"] != "offline" and (not manifest.get("deadline") or timestamp(manifest["deadline"]) <= utc_now()):
        raise ValueError("live job requires unexpired absolute campaign deadline")
    allocation = manifest["allocation"]
    if not isinstance(allocation, dict) or not allocation.get("authorization_source"):
        raise ValueError("explicit allocation and authorization source required")
    if allocation.get("cost_mode") not in ("offline", "unpriced_cli", "priced_api"):
        raise ValueError("allocation requires a supported cost_mode")
    for key in ("max_calls", "max_seconds", "max_usd"):
        value = allocation.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("allocation requires finite nonnegative limits")
    if not isinstance(allocation["max_calls"], int) or allocation["max_seconds"] <= 0:
        raise ValueError("allocation requires integer call limit and positive wall time")
    if manifest["retry_policy"] != {"max_attempts": 1, "retry_uncertain": False}:
        raise ValueError("runner permits one attempt and no uncertain retries")
    if digest(config) != manifest["config_hash"]:
        raise ValueError("config hash mismatch")
    if manifest["kind"] == "predict":
        if not isinstance(profile, ProfileArtifact) or profile.profile_id != manifest["profile_hash"]:
            raise ValueError("profile hash mismatch")
        if profile.allowed_source_manifest_hash != manifest["source_manifest_hash"]:
            raise ValueError("profile source hash mismatch")
        if profile.method_id != manifest["method_id"] or profile.personalization_cap != manifest["personalization_cap"]:
            raise ValueError("profile method/cap mismatch")
        if profile.extractor != manifest["extractor"] or profile.replicate_id != manifest["replicate_id"]:
            raise ValueError("profile extractor/replicate mismatch")
        if not isinstance(items, list) or digest(items) != manifest["items_hash"]:
            raise ValueError("decision items hash mismatch")
        seen = set()
        for item in items:
            if not isinstance(item, dict) or set(item) != ITEM_FIELDS:
                raise ValueError("decision input fields must be label-free allowlist")
            if not isinstance(item["item_id"], str) or not item["item_id"] or item["item_id"] in seen:
                raise ValueError("duplicate/invalid decision item ID")
            seen.add(item["item_id"])
            if item["researcher_id"] != profile.researcher_id:
                raise ValueError("item/profile researcher mismatch")
        schedule = [{"item_id": i["item_id"], "option_order_id": i["option_order_id"]} for i in items]
        if schedule != manifest["option_order_schedule"]:
            raise ValueError("option order schedule mismatch")
    elif manifest["kind"] == "build":
        if manifest.get("documents_hash") != digest(documents):
            raise ValueError("full approved document records hash mismatch")
        validate_documents(documents, config)
        if config["allowed_source_manifest_hash"] != manifest["source_manifest_hash"]:
            raise ValueError("build source hash mismatch")
        for field in ("method_id", "personalization_cap", "replicate_id", "code_sha"):
            if config[field] != manifest[field]:
                raise ValueError("build config/manifest mismatch: " + field)


class _CallGate:
    def __init__(self, backend, manifest, lease, declared_settings, trace_root, cache_root):
        self.backend, self.manifest = backend, manifest
        self.trace_root, self.cache_root = Path(trace_root), Path(cache_root) if cache_root else None
        self.allocation = manifest["allocation"]
        self.declared_settings = json.loads(canonical_json(declared_settings))
        self.started = time.monotonic()
        self.attempts, self.failures, self.cache_hits = 0, 0, 0
        self.trace_hashes = []
        self.halted = False
        self.deadline = timestamp(lease["expires_at"])
        if manifest.get("deadline"):
            self.deadline = min(self.deadline, timestamp(manifest["deadline"]))
        self._overnight_identity = backend_identity(backend)
        self.name = backend.name
        self.model = getattr(backend, "model", "")
        self.base_url = getattr(backend, "base_url", "")
        self.label, self.budget = backend.label, backend.budget

    def supported(self):
        mode = self.allocation.get("cost_mode")
        if self.manifest["stage"] == "offline":
            return mode == "offline" and self.name.startswith("offline")
        if mode == "unpriced_cli":
            return self.name in ("codex-cli", "claude-cli", "devin-cli") and hasattr(self.backend, "timeout")
        if mode == "priced_api":
            # A shared Budget alone cannot conservatively reserve dollars.
            return (self.name in ("openai-responses", "openai-responses-overnight") and hasattr(self.backend, "cost_summary") and
                    0 < self.backend.max_usd <= self.allocation["max_usd"] and hasattr(self.backend, "timeout"))
        return False

    def complete(self, prompt, **settings):
        if self.halted:
            raise ProfileFailure("unavailable", "lane_held_after_uncertain_attempt")
        absolute_remaining = (self.deadline - utc_now()).total_seconds()
        if absolute_remaining <= 0:
            raise ProfileFailure("unavailable", "deadline_or_lease_expired")
        remaining = min(absolute_remaining, self.allocation["max_seconds"] - (time.monotonic() - self.started))
        if remaining <= 0:
            raise ProfileFailure("unavailable", "allocation_exhausted")
        actual_settings = {key: value for key, value in settings.items() if key != "system"}
        if set(actual_settings) != {"temperature", "max_tokens"} or actual_settings != self.declared_settings:
            raise ProfileFailure("unavailable", "call_settings_differ_from_declared")
        key = cache_key(self.manifest, prompt, settings)
        cached_path = self.cache_root / (key + ".json") if self.cache_root else None
        if cached_path and cached_path.exists():
            cached = json.loads(cached_path.read_text(encoding="utf-8"))
            if cached.get("cache_key") != key or cached.get("response_sha256") != sha256_text(cached.get("response", "")):
                raise ProfileFailure("invalid", "cache_provenance_mismatch")
            self.cache_hits += 1
            return cached["response"]
        if self.attempts >= self.allocation["max_calls"] or remaining <= 0:
            raise ProfileFailure("unavailable", "allocation_exhausted")
        if self.manifest["stage"] != "offline" and getattr(self.backend, "timeout", remaining + 1) > remaining:
            raise ProfileFailure("unavailable", "backend_timeout_exceeds_remaining_allocation")
        self.attempts += 1
        trace = {"attempt": self.attempts, "cache_key": key, "prompt": prompt, "settings": settings,
                 "backend": self._overnight_identity, "status": "started"}
        self.trace_hashes.append(write_new(self.trace_root / ("%04d-started.json" % self.attempts), trace))
        try:
            response = self.backend.complete(prompt, **settings)
            if not isinstance(response, str) or len(response.encode("utf-8")) > 8_000_000:
                raise ValueError("invalid response transport")
        except Exception:
            self.failures += 1
            self.halted = True
            self.trace_hashes.append(write_new(self.trace_root / ("%04d-failed.json" % self.attempts),
                                               {"attempt": self.attempts, "status": "failed", "usage_status": "uncertain"}))
            raise ProfileFailure("unavailable", "backend_failed_usage_uncertain") from None
        completed = {"attempt": self.attempts, "status": "complete", "cache_key": key,
                     "response": response, "response_sha256": sha256_text(response)}
        self.trace_hashes.append(write_new(self.trace_root / ("%04d-complete.json" % self.attempts), completed))
        if cached_path:
            write_new(cached_path, completed)
        return response

    def usage(self):
        summary = self.budget.summary()
        cost = self.backend.cost_summary() if hasattr(self.backend, "cost_summary") else {}
        return {"attempted_calls": self.attempts, "uncertain_attempts": self.failures, "cache_hits": self.cache_hits,
                "input_tokens": summary.get("input_tokens"), "output_tokens": summary.get("output_tokens"),
                "reported_api_usd": cost.get("spent_usd") if self.allocation["cost_mode"] == "priced_api" else None,
                "reserved_api_usd": cost.get("reserved_usd") if self.allocation["cost_mode"] == "priced_api" else None,
                "budget_detail": cost,
                "cost_status": "offline" if self.manifest["stage"] == "offline" else
                    ("conservative_estimate" if self.allocation["cost_mode"] == "priced_api" else "unavailable"),
                "elapsed_seconds": time.monotonic() - self.started}


def run_job(manifest, lease, *, output_root, lease_root, config, profile=None, items=None,
            documents=None, consumer=None, extractor=None, cache_root=None, private_root=None,
            confirmation_receipt=None):
    """Execute one assigned build/predict job; return full result only to caller.

    Confirmation callers must be the evaluator. The full returned object is
    private too; shared notifications must use public_handoff(result).
    """
    manifest = json.loads(canonical_json(manifest))
    lease = json.loads(canonical_json(lease))
    config = json.loads(canonical_json(config))
    items = json.loads(canonical_json(items))
    documents = json.loads(canonical_json(documents))
    confirmation_receipt = json.loads(canonical_json(confirmation_receipt))
    if isinstance(profile, ProfileArtifact):
        profile = ProfileArtifact.from_dict(profile.to_dict())
    _validate(manifest, lease, config, profile, items, documents)
    backend = extractor if manifest["kind"] == "build" else consumer
    expected_backend = manifest["extractor"] if manifest["kind"] == "build" else manifest["consumer"]
    if backend is None or backend_identity(backend) != expected_backend:
        raise ValueError("executed backend identity differs from manifest")
    out = Path(output_root) / manifest["job_id"]
    if manifest["stage"] == "confirmation":
        require_private_path(out, private_root)
        require_private_path(lease_root, private_root)
        if cache_root is not None:
            require_private_path(cache_root, private_root)
        if not confirmation_receipt or not manifest.get("confirmation_store_id"):
            raise ValueError("confirmation private evaluator receipt required")
        from .evaluation import validate_confirmation_receipt
        validate_confirmation_receipt(private_root, confirmation_receipt, job_id=manifest["job_id"],
                                      manifest_sha256=manifest["confirmation_manifest_sha256"],
                                      private_root=private_root, expected_store_id=manifest["confirmation_store_id"])
    claim = Path(lease_root) / (manifest["job_id"] + ".json")
    write_new(claim, {"manifest": manifest, "lease": lease, "status": "claimed"})
    out.mkdir(parents=True, exist_ok=False)
    write_new(out / "manifest.json", manifest)
    if confirmation_receipt is not None:
        write_new(out / "confirmation-receipt.json", confirmation_receipt)
    declared_settings = config.get("extractor_settings") if manifest["kind"] == "build" else config.get("settings")
    gate = _CallGate(backend, manifest, lease, declared_settings, out / "traces", cache_root)
    result = {"schema_version": "overnight-result-v1", "job_id": manifest["job_id"], "stage": manifest["stage"],
              "status": "complete", "manifest_hash": digest(manifest), "code_sha": manifest["code_sha"],
              "config_hash": manifest["config_hash"], "source_manifest_hash": manifest["source_manifest_hash"],
              "profile_hash": manifest["profile_hash"], "actual_backend": backend_identity(backend),
              "counts": {"attempted": 0, "complete": 0, "error": 0}, "predictions": [], "missing_arms": []}
    if not gate.supported() or manifest["kind"] not in ("build", "predict"):
        result.update(status="unavailable", error_code="unsupported_backend_or_job_kind")
    elif manifest["kind"] == "build":
        result["counts"]["attempted"] = 1
        try:
            built = build_profile(documents, config, gate)
            result["profile_hash"] = built.profile_id
            result["profile"] = built.to_dict()
            result["status"] = built.status
            result["counts"]["complete" if built.status == "complete" else "error"] = 1
            write_new(out / "profile.json", built.to_dict())
        except Exception as exc:
            result.update(status="unavailable", error_code=getattr(exc, "code", "build_failed"))
            result["counts"]["error"] = 1
    else:
        for item in items:
            row = {"item_id": item["item_id"], "status": "complete", "prediction": None,
                   "item_sha256": digest(item), "items_sha256": manifest["items_hash"],
                   "job_id": manifest["job_id"], "manifest_sha256": digest(manifest),
                   "error_code": None, "confidence_status": "uncalibrated", "actual_consumer": backend_identity(backend)}
            result["counts"]["attempted"] += 1
            try:
                prepared = prepare_payload(profile, item["context"], item["options"], config)
                row.update({key: prepared[key] for key in ("rendered_profile_sha256", "payload_sha256")})
                before_hits = gate.cache_hits
                row["prediction"] = asdict(predict_profile(profile, item["context"], item["options"], gate, config))
                row["cache_provenance"] = {"hit": gate.cache_hits > before_hits,
                                           "key": cache_key(manifest, prepared["prompt"], dict(config["settings"], system=prepared["system"]))}
                result["counts"]["complete"] += 1
            except ProfileFailure as exc:
                row.update(status=exc.status, error_code=exc.code)
                result["counts"]["error"] += 1
            result["predictions"].append(row)
        if result["counts"]["error"]:
            result["status"] = "partial"
    result["usage"] = gate.usage()
    result["trace_hashes"] = gate.trace_hashes
    write_new(out / "result.json", result)
    return result


def public_handoff(result):
    """Only non-answer-bearing progress fields, including for confirmation."""
    fields = ("schema_version", "job_id", "stage", "status", "manifest_hash", "code_sha",
              "config_hash", "source_manifest_hash", "profile_hash", "counts", "usage", "trace_hashes")
    return {key: result[key] for key in fields if key in result}
