"""Source-backed evaluation and cooperative one-use confirmation custody.

No network/model calls. Raw source and target records remain evaluator-only.
All participants share an OS account; this is not a hostile-agent security boundary.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sqlite3
import time
import uuid
from pathlib import Path


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def write_immutable_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def review_document(record):
    reasons = []
    for key in ("document_id", "researcher_id", "canonical_url", "version_evidence", "author", "contribution"):
        if not record.get(key):
            reasons.append("missing_" + key)
    content = record.get("content")
    if not isinstance(content, str) or not content.strip():
        reasons.append("missing_content")
    elif record.get("content_sha256") != hashlib.sha256(content.encode("utf-8")).hexdigest():
        reasons.append("content_hash_mismatch")
    review = record.get("source_review", {})
    if (not isinstance(review, dict) or review.get("disposition") not in ("approved_atemporal", "approved_temporal")
            or not review.get("reviewer") or review.get("grouping_reviewed") is not True
            or not review.get("attribution_basis")):
        reasons.append("explicit_source_review_missing")
    elif review["disposition"] == "approved_temporal":
        version = record.get("version_evidence")
        if not isinstance(version, dict) or version.get("temporal_eligibility") != "verified":
            reasons.append("temporal_version_unverified")
    spans = record.get("permitted_spans", [])
    if not spans:
        reasons.append("attributed_span_missing")
    for span in spans:
        start, end = span.get("start"), span.get("end")
        if (type(start) is not int or type(end) is not int or not isinstance(content, str)
                or not 0 <= start < end <= len(content) or span.get("text") != content[start:end]
                or span.get("speaker") != record.get("researcher_id")):
            reasons.append("attributed_span_invalid")
    if record.get("fetch_status") != "complete":
        reasons.append("incomplete_fetch")
    if record.get("qa_status") in ("quarantined", "rejected"):
        reasons.append("collector_quarantine")
    return {"status": "quarantined" if reasons else "eligible", "reasons": reasons}


def _shingles(text):
    words = re.findall(r"\w+", text.casefold())
    return {tuple(words[i:i + 5]) for i in range(max(0, len(words) - 4))} if len(words) >= 20 else set()


def group_documents(documents):
    docs = list(documents)
    ids = [d["document_id"] for d in docs]
    if len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("document IDs must be unique nonempty strings")
    parent = {i: i for i in ids}

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        parent[root(a)] = root(b)

    seen = {}
    for d in docs:
        for key in ("canonical_url", "content_sha256", "document_group", "project_group", "duplicate_group"):
            value = d.get(key)
            if value:
                token = (key, str(value))
                if token in seen:
                    union(d["document_id"], seen[token])
                seen[token] = d["document_id"]
        for key in ("revision_ids", "crosspost_ids", "near_duplicate_ids"):
            for other in d.get(key, []):
                if other not in parent:
                    raise ValueError("source link points outside the reviewed inventory")
                union(d["document_id"], other)
    shingles = [_shingles(d.get("content", "")) for d in docs]
    for i, a in enumerate(shingles):
        for j in range(i):
            b = shingles[j]
            if a and b and len(a & b) / len(a | b) >= 0.8:
                union(ids[i], ids[j])
    components = {}
    for i in ids:
        components.setdefault(root(i), []).append(i)
    group_ids = {r: canonical_hash(sorted(members)) for r, members in components.items()}
    return {i: group_ids[root(i)] for i in ids}


def freeze_split(documents, split_by_document):
    docs = list(documents)
    groups = group_documents(docs)
    if set(groups) != set(split_by_document):
        raise ValueError("split must name exactly the source set")
    allowed = {"fit", "dev", "confirmation", "quarantine"}
    assigned = {}
    for d in docs:
        split = split_by_document[d["document_id"]]
        if split not in allowed:
            raise ValueError("unknown split")
        if review_document(d)["status"] != "eligible" and split != "quarantine":
            raise ValueError("quarantined document cannot enter an evaluation split")
        group = groups[d["document_id"]]
        if group in assigned and assigned[group] != split:
            raise ValueError("connected source group crosses splits")
        assigned[group] = split
    result = {"schema_version": "profile-split-v1", "document_groups": groups,
              "split_by_document": dict(split_by_document),
              "source_record_hashes": {d["document_id"]: canonical_hash(d) for d in docs},
              "source_manifest": sorted(({"document_id": d["document_id"], "content_sha256": d["content_sha256"]}
                                         for d in docs), key=lambda d: d["document_id"])}
    result["manifest_sha256"] = canonical_hash(result)
    return result


_RELEASE_FIELDS = ("document_id", "researcher_id", "content", "content_sha256", "observed_content_sha256",
                   "canonical_url", "author", "contribution", "published_at", "updated_at", "retrieved_at",
                   "version_evidence", "document_group", "project_group", "duplicate_group", "evidence_type",
                   "permitted_spans", "split_eligibility", "normalization_version", "source_review")


def approved_bundle(documents, manifest):
    docs = list(documents)
    if freeze_split(docs, manifest["split_by_document"]) != manifest:
        raise ValueError("sources do not match frozen split")
    fit = [{k: d[k] for k in _RELEASE_FIELDS if k in d} for d in docs
           if manifest["split_by_document"][d["document_id"]] == "fit"]
    for d in fit:
        version = d.get("version_evidence")
        if isinstance(version, dict):
            d["version_evidence"] = {k: version[k] for k in ("basis", "observed_revision", "parser_sha256",
                "normalization", "status", "temporal_eligibility", "review_basis") if k in version}
    fit.sort(key=lambda d: d["document_id"])
    source_manifest = [{"document_id": d["document_id"], "content_sha256": d["content_sha256"]} for d in fit]
    heldout = {}
    for split in ("dev", "confirmation", "quarantine"):
        ids = sorted(canonical_hash(["opaque-document-v1", d["document_id"], d["content_sha256"]]) for d in docs
                     if manifest["split_by_document"][d["document_id"]] == split)
        heldout[split] = {"ids": ids, "count": len(ids)}
    return {"schema_version": "approved-source-bundle-v1", "documents": fit,
            "source_manifest": source_manifest, "allowed_source_manifest_hash": canonical_hash(source_manifest),
            "heldout": heldout}


def prediction_input(item):
    result = {k: item[k] for k in ("item_id", "researcher_id", "context", "options", "option_order_id")}
    if not isinstance(result["options"], list) or len(result["options"]) < 2:
        raise ValueError("decision needs at least two options")
    if any(not isinstance(v, str) for v in result["options"]):
        raise ValueError("options must be strings")
    return result


def target_eligibility(target, document):
    reasons = []
    if target.get("tier") not in ("A", "B"):
        reasons.append("not_source_backed_tier")
    if review_document(document)["status"] != "eligible":
        reasons.append("source_quarantined")
    if target.get("document_id") != document.get("document_id"):
        reasons.append("source_mismatch")
    if target.get("speaker") != document.get("researcher_id") or target.get("attribution_verified") is not True:
        reasons.append("attribution_unverified")
    if target.get("evidence_review") != "accepted":
        reasons.append("source_review_missing")
    options = target.get("options", [])
    if len(options) < 2 or target.get("alternative_provenance") != ["source"] * len(options):
        reasons.append("alternatives_not_documented")
    if target.get("tier") == "B" and not target.get("constraints"):
        reasons.append("observed_choice_constraints_missing")
    index = target.get("chosen_index")
    if type(index) is not int or not 0 <= index < len(options):
        reasons.append("invalid_label")
    span = target.get("evidence_span", {})
    start, end = span.get("start"), span.get("end")
    content = document.get("content", "")
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(content)
            or span.get("text") != content[start:end]):
        reasons.append("source_span_mismatch")
    if type(start) is int and type(end) is int and not any(
            p.get("speaker") == target.get("speaker") and p.get("start", -1) <= start
            and p.get("end", -1) >= end for p in document.get("permitted_spans", [])):
        reasons.append("target_outside_attributed_span")
    return {"eligible": not reasons, "reasons": reasons}


def _summary(rows):
    n = len(rows)
    valid = [r["brier"] for r in rows if r["brier"] is not None]
    return {"n_items": n, "accuracy": sum(r["correct"] for r in rows) / n if n else None,
            "failures": sum(r["failure"] for r in rows), "n_groups": len({r["group_id"] for r in rows}),
            "probability_coverage": len(valid) / n if n else 0.0,
            "brier_valid_only": sum(valid) / len(valid) if valid else None}


def prepare_target_bundle(targets, documents, split_manifest, *, stage):
    """Validate private labels against reviewed bytes and frozen source split."""
    if stage not in ("dev", "confirmation"):
        raise ValueError("target stage must be dev or confirmation")
    documents = list(documents)
    if freeze_split(documents, split_manifest["split_by_document"]) != split_manifest:
        raise ValueError("target source split changed")
    by_id = {d["document_id"]: d for d in documents}
    checked = []
    seen = set()
    for original in targets:
        t = json.loads(json.dumps(original, allow_nan=False))
        if t["item_id"] in seen:
            raise ValueError("duplicate target item")
        seen.add(t["item_id"])
        document = by_id.get(t.get("document_id"))
        if (document is None or split_manifest["split_by_document"][t["document_id"]] != stage
                or t.get("group_id") != split_manifest["document_groups"][t["document_id"]]
                or t.get("researcher_id") != document["researcher_id"]):
            raise ValueError("target source/group/stage mismatch")
        if not target_eligibility(t, document)["eligible"]:
            raise ValueError("target lacks reviewed source-backed evidence")
        prediction_input(t)
        checked.append(t)
    checked.sort(key=lambda t: t["item_id"])
    inputs = [prediction_input(t) for t in checked]
    result = {"schema_version": "validated-target-bundle-v1", "stage": stage,
              "split_manifest_sha256": split_manifest["manifest_sha256"],
              "source_record_hashes": split_manifest["source_record_hashes"],
              "items": checked, "items_sha256": canonical_hash(inputs)}
    result["target_bundle_sha256"] = canonical_hash(result)
    return result


def score_predictions(bundle, predictions, *, expected_target_bundle_sha256, expected_job_id, expected_manifest_sha256):
    unsigned = {k: v for k, v in bundle.items() if k != "target_bundle_sha256"}
    if (bundle.get("schema_version") != "validated-target-bundle-v1"
            or bundle.get("target_bundle_sha256") != expected_target_bundle_sha256
            or canonical_hash(unsigned) != expected_target_bundle_sha256):
        raise ValueError("validated target bundle changed or not pinned")
    targets = bundle["items"]
    if canonical_hash([prediction_input(t) for t in targets]) != bundle["items_sha256"]:
        raise ValueError("frozen item schedule changed")
    expected = {t["item_id"]: t for t in targets}
    if len(expected) != len(targets):
        raise ValueError("duplicate target item")
    rows = {}
    for row in predictions:
        identity = row["item_id"]
        if identity in rows or identity not in expected:
            raise ValueError("duplicate or unexpected prediction item")
        rows[identity] = row
    outcomes = []
    for identity, t in expected.items():
        if t.get("tier") not in ("A", "B") or type(t.get("chosen_index")) is not int:
            raise ValueError("ineligible target tier or label")
        k = len(t["options"])
        if not 0 <= t["chosen_index"] < k:
            raise ValueError("target label out of range")
        row = rows.get(identity, {})
        pred = row.get("prediction") or {}
        if not isinstance(pred, dict):
            pred = {}
        choice = pred.get("choice")
        confidence = pred.get("confidence")
        probs = pred.get("probabilities", [])
        binding_valid = (row.get("item_sha256") == canonical_hash(prediction_input(t))
                         and row.get("items_sha256") == bundle["items_sha256"]
                         and row.get("job_id") == expected_job_id
                         and row.get("manifest_sha256") == expected_manifest_sha256)
        valid = (binding_valid and row.get("status") in ("complete", "ok") and isinstance(choice, str) and len(choice) == 1
                 and 0 <= ord(choice) - ord("a") < k and type(confidence) in (int, float)
                 and math.isfinite(confidence) and 0 <= confidence <= 1)
        pvalid = (isinstance(probs, list) and len(probs) == k
                  and all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in probs)
                  and math.isclose(sum(probs), 1, abs_tol=1e-6))
        if probs and not pvalid:
            valid = False
        index = ord(choice) - ord("a") if valid else None
        if valid and pvalid and not math.isclose(confidence, probs[index], abs_tol=1e-6):
            valid = False
        brier = (sum((p - (i == t["chosen_index"])) ** 2 for i, p in enumerate(probs)) / k
                 if valid and pvalid else None)
        outcomes.append({"item_id": identity, "researcher_id": t["researcher_id"], "group_id": t["group_id"],
                         "tier": t["tier"], "correct": bool(valid and index == t["chosen_index"]),
                         "failure": not valid, "brier": brier,
                         "schedule_hash": canonical_hash(prediction_input(t))})
    report = _summary(outcomes)
    report["target_bundle_sha256"] = expected_target_bundle_sha256
    report["job_id"] = expected_job_id
    report["manifest_sha256"] = expected_manifest_sha256
    for key in ("researcher_id", "tier"):
        report["by_researcher" if key == "researcher_id" else "by_tier"] = {
            value: _summary([r for r in outcomes if r[key] == value]) for value in sorted({r[key] for r in outcomes})}
    report["missing_item_ids"] = sorted(set(expected) - set(rows))
    report["per_item"] = outcomes  # private evaluator data; do not publish this field for confirmation
    return report


def paired_comparison(a, b, seed=0, samples=2000):
    aa = {r["item_id"]: r for r in a["per_item"]}
    bb = {r["item_id"]: r for r in b["per_item"]}
    if not aa or set(aa) != set(bb):
        raise ValueError("paired comparison requires identical nonempty item schedule")
    groups = {}
    for identity in aa:
        if any(aa[identity][k] != bb[identity][k] for k in ("group_id", "schedule_hash", "researcher_id", "tier")):
            raise ValueError("paired item metadata differs")
        groups.setdefault(aa[identity]["group_id"], []).append(int(aa[identity]["correct"]) - int(bb[identity]["correct"]))
    difference = sum(sum(v) for v in groups.values()) / len(aa)
    interval = None
    if len(groups) >= 2:
        rng, names = random.Random(seed), sorted(groups)
        values = []
        for _ in range(samples):
            draws = [groups[rng.choice(names)] for _ in names]
            values.append(sum(map(sum, draws)) / sum(map(len, draws)))
        values.sort()
        interval = [values[int(0.025 * samples)], values[min(samples - 1, int(0.975 * samples))]]
    return {"difference": difference, "ci95": interval, "n_groups": len(groups), "n_items": len(aa),
            "interpretation": "Descriptive group bootstrap; few groups do not support confirmatory claims."}


def feasibility_report(targets, split_group_counts):
    targets = list(targets)
    counts = {}
    for t in targets:
        if t.get("tier") not in ("A", "B"):
            raise ValueError("inferred targets are not fidelity evidence")
        key = t["researcher_id"] + ":" + t["tier"]
        entry = counts.setdefault(key, {"targets": 0, "groups": set()})
        entry["targets"] += 1
        entry["groups"].add(t["group_id"])
    for entry in counts.values():
        entry["groups"] = len(entry["groups"])
    researchers = sorted({t["researcher_id"] for t in targets})
    if split_group_counts and all(isinstance(v, dict) for v in split_group_counts.values()):
        per_groups = split_group_counts
    elif len(researchers) == 1:
        per_groups = {researchers[0]: split_group_counts}
    else:
        per_groups = {}  # aggregate counts cannot certify per-researcher readiness
    per_researcher = {}
    for researcher in sorted(set(researchers) | set(per_groups)):
        groups = per_groups.get(researcher, {})
        n_targets = sum(t["researcher_id"] == researcher for t in targets)
        ready = n_targets > 0 and groups.get("fit", 0) > 0 and groups.get("dev", 0) > 0
        per_researcher[researcher] = {"status": "dev_ready" if ready else "unmeasured",
                                     "n_targets": n_targets, "split_group_counts": groups}
    ready = bool(per_researcher) and all(r["status"] == "dev_ready" for r in per_researcher.values())
    confirmation = ready and all(r["split_group_counts"].get("confirmation", 0) > 0 for r in per_researcher.values())
    return {"status": "descriptive_pilot" if ready else "unmeasured", "counts": counts,
            "split_group_counts": split_group_counts, "per_researcher": per_researcher,
            "confirmation_feasible": confirmation,
            "reason": "Disjoint fit/dev support descriptive development only; confirmation is a separate gate." if ready
            else "No valid targets or per-researcher independent fit/dev evidence."}


def _connect(root):
    connection = sqlite3.connect(str(Path(root) / "ledger.sqlite3"), timeout=30, isolation_level=None)
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def initialize_store(store_root):
    root = Path(store_root).resolve()
    if any((p / ".git").exists() for p in [root] + list(root.parents)):
        raise ValueError("evaluator store must be outside Git checkouts")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)
    (root / "private").mkdir(mode=0o700, exist_ok=True)
    with _connect(root) as db:
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, receipt TEXT NOT NULL, manifest TEXT NOT NULL, authority TEXT NOT NULL, state TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS consumed (dataset TEXT, kind TEXT, identity TEXT, reservation TEXT NOT NULL, PRIMARY KEY(dataset,kind,identity))")
        db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, reservation TEXT NOT NULL, state TEXT NOT NULL, timestamp REAL NOT NULL)")
        db.execute("INSERT OR IGNORE INTO metadata VALUES ('store_id', ?)", (uuid.uuid4().hex,))
        store_id = db.execute("SELECT value FROM metadata WHERE key='store_id'").fetchone()[0]
    (root / "ledger.sqlite3").chmod(0o600)
    return {"store_id": store_id, "private_root": str((root / "private").resolve())}


def reserve_confirmation(store_root, manifest, authority):
    root = Path(store_root).resolve()
    meta = initialize_store(root)
    mh = canonical_hash(manifest)
    if authority.get("authorized") is not True or not authority.get("source") or authority.get("manifest_sha256") != mh:
        raise ValueError("concrete manifest authorization required")
    private = Path(manifest.get("private_root", "")).resolve()
    if private != root / "private":
        raise ValueError("private root must be the pinned evaluator directory without escape")
    dataset = manifest.get("canonical_dataset")
    jobs, identities = manifest.get("job_ids"), manifest.get("identities")
    if (not isinstance(dataset, str) or not dataset or not manifest.get("canonical_split")
            or not manifest.get("metrics") or not manifest.get("retry_policy")
            or not isinstance(jobs, list) or not jobs or len(jobs) != len(set(jobs))
            or not all(isinstance(j, str) and j for j in jobs) or not identities):
        raise ValueError("incomplete frozen confirmation manifest")
    keys = []
    for identity in identities:
        if identity.get("kind") not in ("target", "source_group", "user") or not isinstance(identity.get("id"), str) or not identity["id"]:
            raise ValueError("invalid underlying identity")
        keys.append((dataset, identity["kind"], identity["id"]))
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate underlying identity")
    receipt = {"schema_version": "confirmation-receipt-v1", "store_id": meta["store_id"],
               "reservation_id": uuid.uuid4().hex, "manifest_sha256": mh,
               "job_ids": sorted(jobs), "private_root": str(private)}
    receipt["receipt_sha256"] = canonical_hash(receipt)
    db = _connect(root)
    try:
        db.execute("BEGIN IMMEDIATE")
        for key in keys:
            if db.execute("SELECT 1 FROM consumed WHERE dataset=? AND kind=? AND identity=?", key).fetchone():
                raise ValueError("underlying identity already consumed")
        db.execute("INSERT INTO reservations VALUES (?,?,?,?,?)", (receipt["reservation_id"], json.dumps(receipt, sort_keys=True),
                   json.dumps(manifest, sort_keys=True), json.dumps(authority, sort_keys=True), "reserved"))
        db.executemany("INSERT INTO consumed VALUES (?,?,?,?)", [key + (receipt["reservation_id"],) for key in keys])
        db.execute("INSERT INTO events(reservation,state,timestamp) VALUES (?,?,?)", (receipt["reservation_id"], "reserved", time.time()))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return receipt


def validate_confirmation_receipt(store_root, receipt, *, job_id, manifest_sha256, private_root, expected_store_id):
    root = Path(store_root).resolve()
    if not (root / "ledger.sqlite3").is_file():
        raise ValueError("authoritative evaluator store unavailable")
    with _connect(root) as db:
        meta = db.execute("SELECT value FROM metadata WHERE key='store_id'").fetchone()
        row = db.execute("SELECT receipt,state FROM reservations WHERE id=?", (receipt.get("reservation_id"),)).fetchone()
    if not meta or meta[0] != expected_store_id or not row:
        raise ValueError("unknown store or reservation")
    saved = json.loads(row[0])
    unsigned = {k: v for k, v in saved.items() if k != "receipt_sha256"}
    if (receipt != saved or saved["receipt_sha256"] != canonical_hash(unsigned)
            or row[1] not in ("reserved", "exposed") or job_id not in saved["job_ids"]
            or manifest_sha256 != saved["manifest_sha256"] or expected_store_id != saved["store_id"]
            or Path(private_root).resolve() != root / "private" or saved["private_root"] != str(root / "private")):
        raise ValueError("confirmation receipt, job, state, manifest or root mismatch")
    return saved


def record_confirmation_event(store_root, reservation_id, state):
    if state not in ("exposed", "failed", "complete"):
        raise ValueError("invalid confirmation event")
    db = _connect(Path(store_root).resolve())
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT state FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        if not row or row[0] in ("failed", "complete"):
            raise ValueError("unknown or terminal reservation")
        db.execute("UPDATE reservations SET state=? WHERE id=?", (state, reservation_id))
        db.execute("INSERT INTO events(reservation,state,timestamp) VALUES (?,?,?)", (reservation_id, state, time.time()))
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
