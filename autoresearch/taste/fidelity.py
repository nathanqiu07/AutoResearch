"""Auditable preference evaluation; one explicit final comparison per checkout."""
from __future__ import annotations

import json
import random
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

from ..research.stats import bootstrap_ci, mean
from .prefdata import build_manifest
from .usermodel import digest

DEFAULT_FINAL_MARKER = Path(__file__).resolve().parents[2] / "results" / "fidelity" / "TEST_USED"


def select_users(manifest, dataset, partition, n_users=None, seed=0):
    if partition not in ("dev", "test"):
        raise ValueError("users must be dev or test")
    eligible = sorted(u for u, data in manifest["users"].items()
                      if data["dataset"] == dataset and data["partition"] == partition
                      and data["test"])
    random.Random(seed).shuffle(eligible)
    if n_users is not None:
        if n_users <= 0:
            raise ValueError("n_users must be positive")
        eligible = eligible[:n_users]
    return eligible


def _code_version():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=Path(__file__).resolve().parents[2], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_fidelity(records, manifest_path, factories, output_dir, dataset, users="dev",
                 n_users=None, seed=0, final=False, final_marker=DEFAULT_FINAL_MARKER,
                 run_config=None):
    records = list(records)
    manifest = json.loads(Path(manifest_path).read_text())
    if build_manifest(records, manifest["seed"]) != manifest:
        raise ValueError("records do not match the frozen split manifest")
    if not factories:
        raise ValueError("at least one method is required")
    if users == "test" and not final:
        raise ValueError("test users require explicit --final authorization")
    if final and users != "test":
        raise ValueError("--final requires test users")
    selected = select_users(manifest, dataset, users, n_users, seed)
    if not selected:
        raise ValueError("no eligible users with target choices")
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError("output directory exists; predictions must not be overwritten")
    registration = {"manifest_id": manifest["manifest_id"], "dataset": dataset,
                    "user_partition": users, "user_ids": selected, "seed": seed,
                    "methods": list(factories), "config": run_config or {},
                    "code_version": _code_version(), "started": time.time()}
    registration["run_id"] = digest(registration)
    if final:
        marker = Path(final_marker)
        marker.parent.mkdir(parents=True, exist_ok=True)
        # Reserve before any fitting or prediction. A crash cannot grant a second look.
        with marker.open("x") as f:
            json.dump(registration, f, indent=2)
    out.mkdir(parents=True)
    (out / "registration.json").write_text(json.dumps(registration, indent=2) + "\n")
    by_id = {r.choice.identity: r.choice for r in records}
    per_method = {m: {} for m in factories}
    usage = {m: {"calls": 0, "cache_hits": 0, "input_tokens": 0, "output_tokens": 0,
                 "cost_usd": 0.0, "cost_available": False} for m in factories}
    with (out / "predictions.jsonl").open("x") as log:
        for user in selected:
            split = manifest["users"][user]
            history, val, target = ([by_id[i] for i in split[s]] for s in ("history", "val", "test"))
            for method, factory in factories.items():
                started = time.monotonic()
                model, fit_error = None, None
                try:
                    model = factory(user)
                    model.fit(history, val)
                    artifact_path = out / "models" / (digest([user, method]) + ".json")
                    model.save(artifact_path)
                except Exception as exc:
                    fit_error = "%s: %s" % (type(exc).__name__, exc)
                cases = []
                for c in target:
                    record = {"user_id": user, "example_id": c.identity, "method": method,
                              "actual": c.chosen, "prediction": None, "correct": False,
                              "error": fit_error, "brier": None}
                    if fit_error is None:
                        try:
                            pred = model.predict(c.context, [c.a_text, c.b_text])
                            if len(pred.probabilities) != 2 or pred.choice not in ("a", "b"):
                                raise ValueError("fidelity requires a binary probability prediction")
                            record.update(prediction=asdict(pred), correct=pred.choice == c.chosen,
                                          brier=(pred.probabilities[0] - (c.chosen == "a")) ** 2)
                        except Exception as exc:
                            record["error"] = "%s: %s" % (type(exc).__name__, exc)
                    cases.append(record)
                    log.write(json.dumps(record, allow_nan=False) + "\n")
                    log.flush()
                valid_briers = [r["brier"] for r in cases if r["brier"] is not None]
                per_method[method][user] = {
                    "accuracy": mean([float(r["correct"]) for r in cases]),
                    "n": len(cases), "failures": sum(r["error"] is not None for r in cases),
                    "brier_valid_only": mean(valid_briers) if valid_briers else None,
                    "seconds": time.monotonic() - started}
                if model:
                    for key in usage[method]:
                        if key == "cost_available":
                            usage[method][key] = usage[method][key] or model.cost.get(key, False)
                        else:
                            usage[method][key] += model.cost.get(key, 0)
    summary = {}
    for method, people in per_method.items():
        accuracies = [r["accuracy"] for r in people.values()]
        briers = [r["brier_valid_only"] for r in people.values() if r["brier_valid_only"] is not None]
        summary[method] = {"accuracy": mean(accuracies),
                           "ci95": list(bootstrap_ci(accuracies, level=0.95, seed=seed)),
                           "n_users": len(people), "n_pairs": sum(r["n"] for r in people.values()),
                           "failures": sum(r["failures"] for r in people.values()),
                           "brier_valid_only": mean(briers) if briers else None,
                           "usage": usage[method], "per_user": people}
    paired = {}
    if "m1" in per_method:
        for method, people in per_method.items():
            differences = [people[u]["accuracy"] - per_method["m1"][u]["accuracy"] for u in selected]
            paired[method] = {"mean": mean(differences),
                              "ci95": list(bootstrap_ci(differences, level=0.95, seed=seed))}
    report = {**registration, "methods": summary, "differences_vs_m1": paired,
              "interpretation": "User-macro accuracy; failures count as wrong; Brier covers valid predictions only. "
                                "Bootstrap samples users. Small pilots do not establish research transfer.",
              "completed": time.time()}
    (out / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report
