#!/usr/bin/env python3
"""Execute exactly two assigned, hashed embedding packets; never select jobs.

The CLI verifies the dispatch, this script, and a clean native runtime before
loading that runtime's existing DollarLedger. Credentials must already be in the
child environment; this script never executes or prints a credentials file.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

URL = "https://api.openai.com/v1/embeddings"
MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
RATE = Decimal("0.02")
RATE_SOURCE = "https://developers.openai.com/api/docs/models/text-embedding-3-small"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("deadline requires timezone")
    return parsed


def write_new(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    return write_new(path, (canonical(value) + "\n").encode("utf-8"))


def price(tokens):
    return Decimal(tokens) * RATE / Decimal(1_000_000)


def outside_runtime(path, runtime_root):
    if runtime_root is None:
        return
    try:
        Path(path).resolve().relative_to(Path(runtime_root).resolve())
    except ValueError:
        return
    raise ValueError("output/claims must not mutate the frozen runtime")


def prepare(dispatch):
    if dispatch.get("schema_version") != "bounded-embedding-dispatch-v1":
        raise ValueError("unsupported dispatch schema")
    if (dispatch.get("model"), dispatch.get("dimensions"), dispatch.get("encoding_format")) != (MODEL, DIMENSIONS, "float"):
        raise ValueError("unapproved model/dimensions/encoding")
    if dispatch.get("script_sha256") != file_sha(__file__):
        raise ValueError("producer script hash mismatch")
    if Decimal(str(dispatch.get("rate_usd_per_million_input"))) != RATE or dispatch.get("rate_source") != RATE_SOURCE or not dispatch.get("rate_verified_at"):
        raise ValueError("verified explicit pricing required")
    if not dispatch.get("authorization_source"):
        raise ValueError("concrete authorization source required")
    if dispatch.get("max_calls") != 2 or isinstance(dispatch.get("max_calls"), bool):
        raise ValueError("exactly two assigned calls required")
    maximum = Decimal(str(dispatch.get("max_usd")))
    if not maximum.is_finite() or not Decimal(0) < maximum <= Decimal("0.01"):
        raise ValueError("producer allocation must be positive and at most 0.01 USD")
    for key, limit in (("max_seconds", 120), ("timeout_seconds", 60)):
        value = dispatch.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= limit:
            raise ValueError("invalid bounded time allocation")
    if stamp(dispatch["deadline"]) <= datetime.now(timezone.utc):
        raise ValueError("campaign deadline reached")
    requests = dispatch.get("requests")
    if not isinstance(requests, list) or len(requests) != 2:
        raise ValueError("exactly two assigned packets required")
    prepared, ids, destinations, claim_ids = [], set(), set(), set()
    for request in requests:
        if not isinstance(request, dict) or not isinstance(request.get("request_id"), str) or not request["request_id"] or request["request_id"] in ids:
            raise ValueError("unique request IDs required")
        ids.add(request["request_id"])
        raw = Path(request["packet_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != request["packet_sha256"]:
            raise ValueError("request packet hash mismatch")
        body = json.loads(raw)
        if set(body) != {"model", "dimensions", "encoding_format", "input"}:
            raise ValueError("request packet fields differ from approved schema")
        if (body["model"], body["dimensions"], body["encoding_format"]) != (MODEL, DIMENSIONS, "float"):
            raise ValueError("request model/dimensions/encoding mismatch")
        inputs = body["input"]
        if not isinstance(inputs, list) or not inputs or len(inputs) > 2048 or any(not isinstance(x, str) or not x or len(x.encode("utf-8")) > 8191 for x in inputs):
            raise ValueError("embedding inputs exceed conservative local bounds")
        if digest(inputs) != request["input_sha256"]:
            raise ValueError("request input hash mismatch")
        bound = len(raw) + 1024
        if bound > 100000:
            raise ValueError("request exceeds bounded producer size")
        claim_id = digest({"model": MODEL, "dimensions": DIMENSIONS, "encoding_format": "float", "input_sha256": request["input_sha256"]})
        if claim_id in claim_ids:
            raise ValueError("duplicate semantic embedding request")
        claim_ids.add(claim_id)
        for key in ("response_path", "receipt_path"):
            destination = Path(request[key]).resolve()
            if destination in destinations or destination.exists():
                raise FileExistsError("immutable output already exists or overlaps")
            destinations.add(destination)
            outside_runtime(destination, dispatch.get("runtime_root"))
        prepared.append({"request": request, "raw": raw, "count": len(inputs), "input_bound": bound,
                         "reservation_usd": price(bound), "claim_id": claim_id})
    for key in ("summary_path", "claims_root"):
        outside_runtime(dispatch[key], dispatch.get("runtime_root"))
    if Path(dispatch["summary_path"]).resolve() in destinations or Path(dispatch["summary_path"]).exists():
        raise FileExistsError("summary output already exists or overlaps")
    if sum(p["reservation_usd"] for p in prepared) > maximum:
        raise ValueError("two conservative reservations exceed producer allocation")
    return prepared


def read_usage(data):
    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    def valid(value):
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 1_000_000_000
    prompt = usage.get("prompt_tokens") if valid(usage.get("prompt_tokens")) else None
    total = usage.get("total_tokens") if valid(usage.get("total_tokens")) else None
    known = [value for value in (prompt, total) if value is not None]
    return {"prompt_tokens": prompt, "total_tokens": total, "known_input_tokens": max(known) if known else None,
            "complete": prompt is not None and total is not None and prompt == total}


def vectors(data, count, usage, bound):
    if not isinstance(data, dict) or data.get("model") != MODEL or not usage["complete"] or usage["known_input_tokens"] > bound:
        raise ValueError("invalid response identity or usage")
    values = data.get("data")
    if not isinstance(values, list) or len(values) != count:
        raise ValueError("embedding response coverage mismatch")
    result, seen = [], set()
    for row in values:
        if not isinstance(row, dict):
            raise ValueError("invalid embedding entry")
        index, embedding = row.get("index"), row.get("embedding")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < count or index in seen:
            raise ValueError("invalid embedding index")
        seen.add(index)
        if not isinstance(embedding, list) or len(embedding) != DIMENSIONS:
            raise ValueError("embedding dimension mismatch")
        for number in embedding:
            try:
                finite = not isinstance(number, bool) and isinstance(number, (int, float)) and math.isfinite(number)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("nonfinite embedding value")
        result.append({"index": index, "embedding": embedding})
    return sorted(result, key=lambda row: row["index"])


def produce(dispatch, ledger, transport=urllib.request.urlopen):
    """Bounded execution core; production CLI verifies runtime before calling."""
    dispatch = json.loads(canonical(dispatch))
    packets = prepare(dispatch)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("API credential is not configured in child environment")
    if stamp(dispatch["deadline"]) > ledger.deadline:
        raise ValueError("dispatch deadline exceeds shared ledger deadline")
    claim_root = Path(dispatch["claims_root"])
    for packet in packets:
        if (claim_root / (packet["claim_id"] + ".json")).exists():
            raise FileExistsError("semantic request already claimed; no automatic retry")
    for packet in packets:
        write_json(claim_root / (packet["claim_id"] + ".json"),
                   {"status": "claimed", "request_id": packet["request"]["request_id"], "input_sha256": packet["request"]["input_sha256"],
                    "packet_sha256": packet["request"]["packet_sha256"], "dispatch_sha256": digest(dispatch)})
    started = time.monotonic()
    result = {"schema_version": "bounded-embedding-result-v1", "status": "complete", "dispatch_sha256": digest(dispatch),
              "script_sha256": dispatch["script_sha256"], "runtime_commit": dispatch["runtime_commit"],
              "model": MODEL, "dimensions": DIMENSIONS, "attempted_calls": 0, "known_usage_usd": 0.0,
              "reserved_usd": 0.0, "requests": [{"request_id": p["request"]["request_id"], "status": "not_started"} for p in packets]}
    known_spent, local_hold = Decimal(0), Decimal(0)
    for index, packet in enumerate(packets):
        row, request = result["requests"][index], packet["request"]
        remaining = min(dispatch["max_seconds"] - (time.monotonic() - started),
                        (stamp(dispatch["deadline"]) - datetime.now(timezone.utc)).total_seconds())
        if remaining <= 0 or result["attempted_calls"] >= dispatch["max_calls"]:
            row.update(status="blocked", error_code="deadline_or_call_allocation_exhausted")
            result["status"] = "partial"
            break
        quote = packet["reservation_usd"]
        if known_spent + local_hold + quote > Decimal(str(dispatch["max_usd"])):
            row.update(status="blocked", error_code="local_allocation_exhausted")
            result["status"] = "partial"
            break
        try:
            reservation = ledger.reserve(quote, {"producer": "bounded-embeddings-v1", "request_id": request["request_id"],
                                                 "input_sha256": request["input_sha256"], "packet_sha256": request["packet_sha256"],
                                                 "runtime_commit": dispatch["runtime_commit"], "script_sha256": dispatch["script_sha256"]})
        except Exception:
            row.update(status="blocked", error_code="shared_ledger_rejected_admission")
            result["status"] = "partial"
            break
        local_hold += quote
        write_json(claim_root / (packet["claim_id"] + "-started.json"),
                   {"reservation_id": reservation, "request_id": request["request_id"], "input_bound": packet["input_bound"],
                    "reserved_usd": float(quote), "packet_sha256": request["packet_sha256"]})
        usage, raw_response, output, succeeded = read_usage({}), None, None, False
        result["attempted_calls"] += 1
        try:
            headers = {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}
            for name, header in (("OPENAI_ORG_ID", "OpenAI-Organization"), ("OPENAI_PROJECT_ID", "OpenAI-Project")):
                if os.environ.get(name):
                    headers[header] = os.environ[name]
            http_request = urllib.request.Request(URL, data=packet["raw"], headers=headers, method="POST")
            with transport(http_request, timeout=min(dispatch["timeout_seconds"], remaining)) as response:
                if getattr(response, "status", 200) != 200:
                    raise ValueError("unexpected response status")
                raw_response = response.read(16_000_001)
            if len(raw_response) > 16_000_000:
                raise ValueError("response too large")
            data = json.loads(raw_response)
            usage = read_usage(data)
            output = vectors(data, packet["count"], usage, packet["input_bound"])
            succeeded = True
        except Exception:
            row.update(status="uncertain", error_code="embedding_request_failed_or_invalid_no_retry")
        actual = price(usage["known_input_tokens"] or 0)
        settlement = ledger.finish(reservation, actual_usd=actual, succeeded=succeeded)
        known_spent += actual
        if settlement == "complete":
            local_hold -= quote
        else:
            succeeded = False
            row.update(status="uncertain", error_code="embedding_outcome_uncertain_no_retry")
        row.update(input_sha256=request["input_sha256"], packet_sha256=request["packet_sha256"], usage=usage,
                   known_usage_usd=float(actual), reserved_usd=0.0 if succeeded else float(quote),
                   response_sha256=hashlib.sha256(raw_response).hexdigest() if raw_response is not None else None)
        if succeeded:
            receipt = {"schema_version": "bounded-embedding-receipt-v1", "status": "complete", "request_id": request["request_id"],
                       "model": MODEL, "dimensions": DIMENSIONS, "encoding_format": "float", "count": packet["count"],
                       "input_sha256": request["input_sha256"], "packet_sha256": request["packet_sha256"],
                       "response_sha256": row["response_sha256"], "usage": usage, "known_usage_usd": float(actual),
                       "script_sha256": dispatch["script_sha256"], "runtime_commit": dispatch["runtime_commit"], "vectors": output}
            try:
                write_new(request["response_path"], raw_response)
                row.update(status="complete", receipt_path=request["receipt_path"],
                           receipt_sha256=write_json(request["receipt_path"], receipt), response_path=request["response_path"])
            except Exception:
                row.update(status="artifact_failed", error_code="valid_response_local_artifact_write_failed_no_retry")
        write_json(claim_root / (packet["claim_id"] + "-result.json"), row)
        if not succeeded or row["status"] == "artifact_failed":
            result["status"] = "partial"
            break
    result.update(known_usage_usd=float(known_spent), reserved_usd=float(local_hold),
                  elapsed_seconds=time.monotonic() - started, campaign_ledger=ledger.summary())
    write_json(dispatch["summary_path"], result)
    return result


def load_runtime(dispatch):
    root = Path(dispatch["runtime_root"]).resolve()
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()
    if Path(git("rev-parse", "--show-toplevel")).resolve() != root or git("rev-parse", "HEAD") != dispatch["runtime_commit"]:
        raise ValueError("native runtime commit mismatch")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("frozen runtime has tracked modifications")
    backend_path = root / "autoresearch/taste/overnight/backends.py"
    if file_sha(backend_path) != dispatch["runtime_backend_sha256"]:
        raise ValueError("runtime ledger implementation hash mismatch")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    importlib.invalidate_caches()
    module = importlib.import_module("autoresearch.taste.overnight.backends")
    if Path(module.__file__).resolve() != backend_path:
        raise ValueError("imported ledger does not belong to pinned runtime")
    policy = dispatch["ledger"]
    outside_runtime(policy["path"], root)
    if policy["max_inflight"] != 2:
        raise ValueError("shared concurrency must stay two")
    return module.DollarLedger(policy["path"], max_usd=policy["max_usd"], deadline=policy["deadline"], max_inflight=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispatch", type=Path, required=True)
    parser.add_argument("--expected-dispatch-sha256", required=True)
    args = parser.parse_args()
    try:
        if file_sha(args.dispatch) != args.expected_dispatch_sha256:
            raise ValueError("dispatch file hash mismatch")
        dispatch = json.loads(args.dispatch.read_text())
        prepare(dispatch)
        ledger = load_runtime(dispatch)
        result = produce(dispatch, ledger)
        print(canonical({"status": result["status"], "attempted_calls": result["attempted_calls"],
                         "known_usage_usd": result["known_usage_usd"], "reserved_usd": result["reserved_usd"],
                         "summary_path": dispatch["summary_path"], "summary_sha256": file_sha(dispatch["summary_path"])}))
        return 0 if result["status"] == "complete" else 2
    except Exception:
        # Do not print request bodies, provider errors, credentials or tracebacks.
        print(canonical({"status": "failed", "error_code": "preflight_or_local_execution_failed_no_automatic_retry"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
