"""Package actual dev-run artifacts and exercise the team's existing adviser.

No fitting happens here. Exporting a bundle does not invoke a model unless the
caller explicitly supplies an LLM to verify the handoff. Final-user records are
refused unless the caller explicitly permits packaging an already completed run.
"""
import json
from dataclasses import asdict
from pathlib import Path

from .prefdata import load_records
from .usermodel import digest


def _read(path):
    return json.loads(Path(path).read_text())


def write_bundle(bundle, path):
    """Create a portable inspection bundle without replacing previous evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(bundle, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def _export_artifact(artifact_path, export_dir):
    source = _read(artifact_path)
    destination = Path(export_dir)
    destination.mkdir(parents=True, exist_ok=True)
    exported = destination / "usermodel.json"
    # Exclusive creation prevents an export from silently changing a researcher.
    with exported.open("x") as stream:
        json.dump(source, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return exported


def verify_interface(artifact_path, llm, context, options, export_dir=None):
    """Reload and consult through Task D's real loader and TasteAdvisor.

    This makes exactly one prediction call, in addition to any fitting/evaluation
    already recorded by the run. It is metered by the supplied backend's budget.
    Supplying export_dir first copies the artifact there, without overwriting it.
    Otherwise artifact_path must already be the exported usermodel.json.
    """
    from ..research.advisor import TasteAdvisor, load_user_model

    exported = _export_artifact(artifact_path, export_dir) if export_dir is not None else Path(artifact_path)
    if exported.name != "usermodel.json":
        raise ValueError("interface verification requires an exported usermodel.json")
    destination = exported.parent
    model, origin = load_user_model(str(destination), profile=None, llm=llm)
    before = llm.budget.summary()
    advisor = TasteAdvisor(model, source=origin)
    advice = advisor.consult(context, options)
    after = llm.budget.summary()
    principles = advisor.principles()
    return {"status": "verified" if advice.choice is not None and not advisor.errors else "failed",
            "interface": "research.advisor.load_user_model -> TasteAdvisor.consult / principles",
            "artifact": "usermodel.json", "method": model.method_id,
            "backend": model.backend_identity, "context": context, "options": options,
            "advice": asdict(advice), "principles": principles, "errors": advisor.errors,
            "usage": {k: after[k] - before[k] for k in
                      ("calls", "input_tokens", "output_tokens", "cost_usd")},
            "backend_budget": llm.cost_summary() if hasattr(llm, "cost_summary") else None,
            "confidence_status": model.artifacts().metadata.get("confidence_status", "unknown"),
            "limit": "This verifies the callable interface, not research improvement. "
                     "The adviser does not enforce the model's calibrated flag."}


def build_bundle(run_dir, records, manifest_path, llm=None, max_examples_per_method=1,
                 allow_final=False, export_dir=None, method=None, user_id=None):
    """Return a viewer bundle from saved run outputs and the matching dataset.

    Examples include full history and validation but only the requested small
    number of target cases per user/method. They are inspection data, never inputs
    for the fitted model. Pass export_dir to export without model calls. Pass llm
    explicitly to export and also verify one artifact through the team adviser.
    """
    if type(max_examples_per_method) is not int or max_examples_per_method < 1:
        raise ValueError("max_examples_per_method must be a positive integer")
    rows = load_records(records) if isinstance(records, (str, Path)) else list(records)
    root = Path(run_dir)
    registration = _read(root / "registration.json")
    report = _read(root / "report.json")
    manifest = _read(manifest_path)
    if registration.get("user_partition") != "dev" and not allow_final:
        raise ValueError("packaging final-user evidence requires explicit allow_final")
    if registration.get("manifest_id") != manifest.get("manifest_id"):
        raise ValueError("run and supplied split manifest differ")
    if report.get("run_id") != registration.get("run_id"):
        raise ValueError("report and registration belong to different runs")
    from .prefdata import build_manifest
    if build_manifest(rows, manifest["seed"], manifest.get("deduplication"), manifest.get("provenance")) != manifest:
        raise ValueError("records do not match the frozen split manifest")
    by_id = {r.choice.identity: r.choice for r in rows}
    predictions = [_read_line(line) for line in (root / "predictions.jsonl").read_text().splitlines() if line.strip()]
    examples, counts = [], {}
    for record in predictions:
        uid, mid = record["user_id"], record["method"]
        if uid not in registration["user_ids"] or mid not in registration["methods"]:
            raise ValueError("prediction is outside the registered user/method selection")
        split = manifest["users"][uid]
        if split["partition"] != registration["user_partition"]:
            raise ValueError("prediction user partition disagrees with registration")
        eid = record["example_id"]
        if eid not in split["test"] or by_id[eid].chosen != record["actual"]:
            raise ValueError("prediction target or observed label disagrees with dataset")
        key = (uid, mid)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > max_examples_per_method:
            continue
        artifact = Path("models") / (digest([uid, mid]) + ".json")
        stored = _read(root / artifact) if (root / artifact).exists() else None
        if stored is not None:
            metadata = stored["artifacts"]["metadata"]
            if metadata.get("user_id") != uid or stored["method"] != mid:
                raise ValueError("model artifact does not match the prediction")
        examples.append({"user_id": uid, "method": mid,
                         "history": [asdict(by_id[e]) for e in split["history"]],
                         "validation": [asdict(by_id[e]) for e in split["val"]],
                         "target": asdict(by_id[eid]), "prediction": record["prediction"],
                         "actual": record["actual"], "correct": record["correct"], "error": record["error"],
                         "artifacts": stored["artifacts"] if stored else None,
                         "model_path": str(artifact) if stored else None})
    mode = report.get("mode")
    if mode not in ("offline_fixture", "live"):
        raise ValueError("run report must identify offline_fixture or live mode")
    integration = {"status": "not_run", "note": "No additional prediction requested."}
    if llm is not None or export_dir is not None:
        choices = [e for e in examples if e["model_path"] and
                   (method is None or e["method"] == method) and
                   (user_id is None or e["user_id"] == user_id)]
        if not choices:
            raise ValueError("no saved model matches the requested export")
        priority = {"m3": 0, "m2": 1, "m1": 2, "m0": 3}
        selected = min(choices, key=lambda e: (priority.get(e["method"], 9), e["user_id"]))
        target = selected["target"]
        exported = _export_artifact(root / selected["model_path"], export_dir or root / "export")
        integration = {"status": "exported_not_verified", "artifact": "usermodel.json",
                       "method": selected["method"], "note": "No model call requested; runtime interface not checked.",
                       "selection_basis": "Requested or illustrative method; not selected as a benchmark winner."}
        if llm is not None:
            integration = verify_interface(exported, llm, target["context"],
                                           [target["a_text"], target["b_text"]])
        integration["user_id"] = selected["user_id"]
        integration["target_id"] = target["example_id"]
        integration["mode"] = mode
    return {"format": "taste-run-bundle-v1", "mode": mode,
            "interpretation": "Simulated plumbing only; not preference-accuracy evidence." if mode == "offline_fixture"
                              else "Recorded live predictions; a small run does not establish a winner or research transfer.",
            "registration": registration, "report": report, "examples": examples, "integration": integration}


def _read_line(line):
    return json.loads(line)
