#!/usr/bin/env python3
"""Read explicit full-chain evidence references and render a local HTML snapshot.

No model calls, network, recursive artifact discovery, or source mutations.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path
import re

SCHEMA = "gio-recovery-viewer-v1"
DEFAULTS = (("generic", "Generic guidance"), ("raw", "Raw source context"),
            ("rich", "Rich sourced profile"), ("compact", "Compact principles"))
STAGES = (("sources", "Source data"), ("profile", "Exact user model"),
          ("auditor_context", "Model-facing auditor context"),
          ("environment", "Generated environment files"),
          ("target_trace", "Target trace"), ("state_changes", "State changes"))
AXES = (("validity", "Environment validity"), ("taste", "Taste adherence"),
        ("behavior", "Target behavior"))
COSTS = (("known_usd", "Known estimate"), ("uncertain_usd", "Uncertain bound"),
         ("reserved_usd", "Reservations"))
MAX_FILE_BYTES = 8 * 1024 * 1024
SECRET = re.compile(r"sk-(?:or-v1-|proj-)[A-Za-z0-9_-]{20,}")
HEX = re.compile(r"[a-f0-9]{64}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fail_constant(value):
    raise ValueError("Nonfinite JSON number: " + value)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key: " + key)
        value[key] = item
    return value


def read_json(raw):
    return json.loads(raw, parse_constant=fail_constant, object_pairs_hook=unique_object)


def plain(value, default=""):
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError("Expected text")
    return SECRET.sub("[REDACTED_CREDENTIAL_LIKE_STRING]", value)


def refs(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Artifact references must be a list")
    return value


class Reader:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Artifact root must be a directory")
        self.cache = {}

    def read(self, ref):
        if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
            raise ValueError("Artifact reference requires a text path")
        name = ref["path"]
        expected = ref.get("sha256")
        if expected is not None and (not isinstance(expected, str) or not HEX.fullmatch(expected)):
            raise ValueError("Expected artifact hash must be lowercase SHA-256")
        record = {"path": plain(name), "label": plain(ref.get("label"), name),
                  "expected_sha256": expected, "sha256": None, "bytes": None,
                  "status": "error", "pin_status": "unpinned", "error": None,
                  "text": None, "redactions": 0}
        relative = Path(name)
        if not name or relative.is_absolute() or ".." in relative.parts:
            return dict(record, error="path_outside_artifact_root")
        path = self.root
        for part in relative.parts:
            path = path / part
            if path.is_symlink():
                return dict(record, error="symlink_not_allowed")
        try:
            path.resolve().relative_to(self.root)
            if not path.exists():
                return dict(record, error="file_missing")
            if not path.is_file():
                return dict(record, error="not_a_regular_file")
            if name not in self.cache:
                if path.stat().st_size > MAX_FILE_BYTES:
                    return dict(record, error="file_exceeds_8_mib_no_truncation")
                with path.open("rb") as handle:
                    raw = handle.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES:
                    return dict(record, error="file_exceeds_8_mib_no_truncation")
                self.cache[name] = raw
            raw = self.cache[name]
            record.update(sha256=sha(raw), bytes=len(raw))
            if expected is not None and expected != record["sha256"]:
                return dict(record, error="hash_mismatch", pin_status="mismatch")
            text = raw.decode("utf-8")
            text, count = SECRET.subn("[REDACTED_CREDENTIAL_LIKE_STRING]", text)
            return dict(record, status="available", text=text, redactions=count,
                        pin_status="verified" if expected else "unpinned")
        except UnicodeDecodeError:
            return dict(record, error="not_utf8_text")
        except (OSError, ValueError) as exc:
            return dict(record, error="read_failed_" + type(exc).__name__)

    def many(self, value):
        return [self.read(ref) for ref in refs(value)]


def collect_index(index_path, artifact_root):
    raw = Path(index_path).read_bytes()
    index = read_json(raw)
    if not isinstance(index, dict) or index.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported viewer index schema")
    if index.get("artifact_kind") not in ("offline_fixture", "recorded_run"):
        raise ValueError("Explicit offline_fixture or recorded_run artifact_kind required")
    if index.get("snapshot_status") not in ("partial", "terminal"):
        raise ValueError("snapshot_status must be partial or terminal")
    reader = Reader(artifact_root)
    supplied = index.get("conditions")
    if not isinstance(supplied, list):
        raise ValueError("conditions must be a list")
    by_id = {}
    for row in supplied:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("Condition requires nonempty text ID")
        if row["id"] in by_id:
            raise ValueError("Duplicate condition ID")
        by_id[row["id"]] = row
    order = list(DEFAULTS) + [(key, key) for key in by_id if key not in dict(DEFAULTS)]
    conditions = []
    for key, label in order:
        row = by_id.get(key, {})
        stages, reviews, costs = row.get("stages", {}), row.get("reviews", {}), row.get("costs", {})
        if not all(isinstance(value, dict) for value in (stages, reviews, costs)):
            raise ValueError("stages, reviews and costs must be objects")
        condition = {"id": plain(key), "label": plain(row.get("label"), label),
                     "status": plain(row.get("status"), "not_supplied" if key not in by_id else "unmeasured"),
                     "error": plain(row.get("error")) or None,
                     "summary": plain(row.get("summary")),
                     "stages": {name: reader.many(stages.get(name)) for name, _ in STAGES},
                     "reviews": {}, "costs": {}}
        for axis, _ in AXES:
            review = reviews.get(axis, {})
            if not isinstance(review, dict):
                raise ValueError("Review must be an object")
            condition["reviews"][axis] = {"status": plain(review.get("status"), "unmeasured"),
                                          "summary": plain(review.get("summary")),
                                          "records": reader.many(review.get("records"))}
        for field, _ in COSTS:
            value = costs.get(field)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError("Cost must be a finite nonnegative number or null")
            condition["costs"][field] = value
        condition["costs"]["records"] = reader.many(costs.get("records"))
        conditions.append(condition)
    limits = index.get("limitations", [])
    if not isinstance(limits, list):
        raise ValueError("limitations must be a list")
    return {"schema_version": SCHEMA, "artifact_kind": index["artifact_kind"],
            "run_id": plain(index.get("run_id")),
            "title": plain(index.get("title"), "A user model through the whole Petri run"),
            "scenario": plain(index.get("scenario"), "Scenario not supplied"),
            "snapshot_status": index["snapshot_status"], "index_sha256": sha(raw),
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "limitations": [plain(value) for value in limits], "conditions": conditions,
            "provenance": reader.many(index.get("provenance"))}


def h(value):
    return escape(str(value), quote=True)


def shown(value):
    return (value or "unmeasured").replace("_", " ").capitalize()


def money(value):
    return "Unmeasured" if value is None else "$" + format(value, ".6f")


def coverage(records):
    if not records:
        return "Not supplied"
    available = sum(row["status"] == "available" for row in records)
    text = f"{available}/{len(records)} files available"
    if available < len(records):
        text += " · evidence error"
    return text


def artifact_html(records):
    if not records:
        return '<p class="missing">Not supplied. This stage has no attached evidence.</p>'
    body = []
    for row in records:
        label = h(row["label"])
        meta = '<p class="meta">' + h(row["path"]) + '<br>Pin: <strong>' + h(shown(row["pin_status"])) + '</strong>'
        if row["sha256"]:
            meta += '<br>SHA-256: <code>' + h(row["sha256"]) + '</code>'
        meta += '</p>'
        if row["status"] != "available":
            body.append('<div class="artifact-error"><strong>' + label + '</strong><p>' + h(row["error"]) + '</p>' + meta + '</div>')
            continue
        note = ('<p class="warning">Credential-like text redacted (' + str(row["redactions"]) + '). The hash identifies original bytes.</p>') if row["redactions"] else ''
        body.append('<details><summary>' + label + ' <span class="meta">· ' + str(row["bytes"]) + ' bytes</span></summary>'
                    + meta + note + '<pre>' + h(row["text"]) + '</pre></details>')
    return ''.join(body)


CSS = '''
:root{--paper:#f3ebdd;--sub:#e8e3d6;--ink:#151411;--muted:#5e584e;--line:#b9b2a4;--red:#b91d12}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif}
header,main,footer{max-width:1500px;margin:auto;padding:26px 38px}header{border-top:10px solid var(--red)}h1{font-size:clamp(32px,4vw,54px);line-height:1.06;letter-spacing:-.035em;max-width:1000px;margin:14px 0 20px}h2{font-size:27px;line-height:1.15;margin:0 0 14px}h3{font-size:18px;margin:0 0 8px}p{max-width:90ch}a{color:var(--red);text-underline-offset:3px}.eyebrow,.meta{font:12px/1.55 ui-monospace,SFMono-Regular,monospace;overflow-wrap:anywhere}.eyebrow{text-transform:uppercase;letter-spacing:.08em}.meta{color:var(--muted)}
.banner{border-left:6px solid var(--red);padding:14px 18px;background:var(--sub);margin:18px 0}.banner strong{display:block}.warning,.artifact-error{color:var(--red)}nav{display:flex;flex-wrap:wrap;gap:8px 24px;border-block:1px solid var(--line);padding:14px 0}nav a{font-size:14px}.chain{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border-block:2px solid var(--ink);margin:26px 0}.chain a{padding:13px 12px;border-right:1px solid var(--line);color:var(--ink);font-size:14px;text-decoration:none}.chain b{display:block;color:var(--red);font:23px/1.4 ui-monospace,monospace}.tablewrap{overflow:auto;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid var(--line);min-width:165px;overflow-wrap:anywhere}th{background:var(--sub);font-size:13px}th:first-child,td:first-child{min-width:190px}.status{font-weight:700}section{border-top:2px solid var(--ink);padding-top:26px;margin-top:36px;scroll-margin-top:18px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0}.condition{border-right:1px solid var(--line);padding:16px;min-width:0}.condition:first-child{padding-left:0}.condition:last-child{border-right:0;padding-right:0}.condition-head{border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:10px}.missing{color:var(--muted);font-size:14px}.artifact-error{padding:12px 0;border-top:1px solid var(--line)}details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:600;overflow-wrap:anywhere}summary:focus-visible,a:focus-visible{outline:3px solid var(--red);outline-offset:3px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--sub);padding:14px;max-height:550px;overflow:auto;font:12px/1.5 ui-monospace,SFMono-Regular,monospace}code{overflow-wrap:anywhere}footer{border-top:2px solid var(--ink);font-size:13px;margin-top:35px}.section-note{color:var(--muted);font-size:14px}.review-summary{font-size:14px}.badge{font:13px ui-monospace,monospace;text-transform:uppercase;letter-spacing:.05em}.overview-note{font-size:14px}
@media(max-width:1050px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.condition:nth-child(odd){padding-left:0}.condition:nth-child(even){border-right:0}.chain{grid-template-columns:repeat(3,minmax(0,1fr))}.chain a{border-bottom:1px solid var(--line)}}
@media(max-width:620px){header,main,footer{padding:22px 18px}.grid{grid-template-columns:1fr}.condition{padding:16px 0;border-right:0;border-bottom:1px solid var(--line)}.chain{grid-template-columns:repeat(2,minmax(0,1fr))}h2{font-size:24px}pre{font-size:12px}.tablewrap{margin-inline:0}th,td{padding:10px}}
@media print{details{display:block}pre{max-height:none;overflow:visible}.grid{display:block}header,main,footer{max-width:none;padding:12px}section{break-before:auto}.condition{break-inside:avoid}}
'''


def render_html(data):
    arms = data["conditions"]
    fixture = data["artifact_kind"] == "offline_fixture"
    banner = ('OFFLINE FIXTURE — Not a live model result' if fixture else 'RECORDED ARTIFACTS — owner-supplied run index')
    state = 'Partial snapshot — unfinished and missing conditions remain visible.' if data["snapshot_status"] == "partial" else 'Terminal snapshot as declared by the run owner; attached files provide the evidence.'
    body = ['<header><div class="eyebrow">AutoResearch / full-chain evidence</div><h1>' + h(data["title"]) + '</h1>',
            '<p class="banner"><strong>' + h(banner) + '</strong>' + h(state) + '</p>',
            '<p><strong>Scenario:</strong> ' + h(data["scenario"]) + '</p>',
            '<p>Follow the source data through the user model, auditor, environment and target. Execution, validity, taste and behavior are separate results. Missing measurements are not zero.</p>',
            '<nav aria-label="Evidence sections"><a href="#comparison">Compare every condition</a><a href="#reviews">Read separate reviews</a><a href="#costs">Costs &amp; provenance</a></nav>',
            '<div class="chain">' + ''.join('<a href="#stage-' + key + '"><b>0' + str(i + 1) + '</b>' + h(label) + '</a>' for i, (key, label) in enumerate(STAGES)) + '</div></header><main>',
            '<section id="comparison"><h2>Every condition, one chain</h2><div class="tablewrap"><table><thead><tr><th scope="col">Evidence or outcome</th>'
            + ''.join('<th scope="col">' + h(a["label"]) + '</th>' for a in arms) + '</tr></thead><tbody>',
            '<tr><th scope="row">Owner-reported execution</th>' + ''.join('<td><span class="status">' + h(shown(a["status"])) + '</span>' + ('<p class="warning">' + h(a["error"]) + '</p>' if a["error"] else '') + ('<p>' + h(a["summary"]) + '</p>' if a["summary"] else '') + '</td>' for a in arms) + '</tr>']
    for key, label in STAGES:
        body.append('<tr><th scope="row"><a href="#stage-' + key + '">' + h(label) + '</a></th>' + ''.join('<td>' + h(coverage(a["stages"][key])) + '</td>' for a in arms) + '</tr>')
    for axis, label in AXES:
        body.append('<tr><th scope="row">' + h(label) + '</th>' + ''.join('<td>' + h(shown(a["reviews"][axis]["status"])) + '</td>' for a in arms) + '</tr>')
    body.append('</tbody></table></div><p class="overview-note">File presence and matching hashes establish retained bytes, not scientific validity. There is no combined winner score. An unpinned artifact is labeled rather than treated as verified.</p></section>')
    notes = {"sources": "Allowed source text and provenance. No pointers inside these files are opened automatically.",
             "profile": "The complete supplied model artifact. Beliefs, preferences and unknown values retain their recorded meaning.",
             "auditor_context": "Exact supplied model-facing context. Review records must separately establish delivery and target/judge isolation.",
             "environment": "Initial generated files and world snapshots. Inspect the actual task, not only a summary score.",
             "target_trace": "Recorded target messages, tool calls and outcomes. Returned reasoning is not proof of internal causes.",
             "state_changes": "Supplied before/after records and changes. Absent change records do not mean nothing changed."}
    for key, label in STAGES:
        body.append('<section id="stage-' + key + '"><h2>' + h(label) + '</h2><p class="section-note">' + h(notes[key]) + '</p><div class="grid">')
        for arm in arms:
            body.append('<article class="condition"><h3 class="condition-head">' + h(arm["label"]) + '</h3>' + artifact_html(arm["stages"][key]) + '</article>')
        body.append('</div></section>')
    body.append('<section id="reviews"><h2>Three separate judgments</h2><p>Statuses and summaries below come from the supplied reviews. The viewer does not grade the experiment or certify profile benefit.</p>')
    for axis, label in AXES:
        body.append('<h3>' + h(label) + '</h3><div class="grid">')
        for arm in arms:
            review = arm["reviews"][axis]
            body.append('<article class="condition"><h3>' + h(arm["label"]) + '</h3><p class="status">' + h(shown(review["status"])) + '</p><p class="review-summary">' + h(review["summary"]) + '</p>' + artifact_html(review["records"]) + '</article>')
        body.append('</div>')
    body.append('</section><section id="costs"><h2>Costs, uncertainty and provenance</h2><p>Known estimates, uncertain bounds and reservations are different quantities. They are not provider bills; this page does not sum possibly overlapping ledgers.</p><div class="tablewrap"><table><tr><th>Condition</th>' + ''.join('<th>' + h(label) + '</th>' for _, label in COSTS) + '</tr>')
    for arm in arms:
        body.append('<tr><th>' + h(arm["label"]) + '</th>' + ''.join('<td>' + money(arm["costs"][key]) + '</td>' for key, _ in COSTS) + '</tr>')
    body.append('</table></div><div class="grid">')
    for arm in arms:
        body.append('<article class="condition"><h3>' + h(arm["label"]) + '</h3>' + artifact_html(arm["costs"]["records"]) + '</article>')
    body.append('</div><h3>Run and model settings</h3>' + artifact_html(data["provenance"]))
    if data["limitations"]:
        body.append('<h3>Recorded limits</h3><ul>' + ''.join('<li>' + h(item) + '</li>' for item in data["limitations"]) + '</ul>')
    body.append('</section></main><footer><p>Run: ' + h(data["run_id"]) + ' · Rendered: ' + h(data["rendered_at"]) + '</p><p class="meta">Index SHA-256: ' + h(data["index_sha256"]) + '</p><p>Self-contained local snapshot. Source files were read only. Credential-like strings, if found, are labeled and redacted. Full source text may still be private; review before sharing.</p></footer>')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>' + h(data["title"]) + '</title><style>' + CSS + '</style></head><body>' + ''.join(body) + '</body></html>'


def write_report(data, out):
    out = Path(out)
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    files = {"index.html": render_html(data), "snapshot.json": json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"}
    for name, text in files.items():
        fd = os.open(out / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
    receipt = {"schema_version": SCHEMA, "artifact_kind": data["artifact_kind"],
               "run_id": data["run_id"], "snapshot_status": data["snapshot_status"],
               "input_index_sha256": data["index_sha256"], "model_calls": 0,
               "files": {name: sha((out / name).read_bytes()) for name in files}}
    fd = os.open(out / "render-receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    receipt = write_report(collect_index(args.index, args.artifact_root), args.out)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
