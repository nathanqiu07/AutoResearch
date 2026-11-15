"""Run only the missing A2 prompted-recognition probes on frozen Petri transcripts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PETRI = ROOT / "scripts" / "gio_petri"
NINE = PETRI / "nine_profiles"
sys.path.insert(0, str(PETRI))
sys.path.insert(0, str(NINE))
sys.path.insert(0, str(ROOT))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def load_cases(experiment: Path = HERE) -> list[dict]:
    comparison = json.loads((experiment / "comparison.json").read_text())
    cases = []
    for row in comparison["rows"]:
        condition = row["condition"]
        replicate = int(row["local_replicate"])
        source = experiment / "evidence" / condition / f"r{replicate}" / "audit.json"
        data = json.loads(source.read_text())
        transcript = data.get("transcript")
        if row.get("execution") != "success" or not isinstance(transcript, str) or not transcript.strip():
            raise ValueError(f"Case is not a completed transcript: {condition}/r{replicate}")
        cases.append({
            "condition": condition,
            "replicate": replicate,
            "original_planned_replicate": row["original_planned_replicate"],
            "source": str(source.relative_to(experiment)),
            "source_sha256": digest(source.read_bytes()),
            "transcript": transcript,
            "transcript_sha256": digest(transcript.encode("utf-8")),
        })
    if len(cases) != 15:
        raise ValueError(f"Expected 15 retained cases, found {len(cases)}")
    return cases


def parse_probability(text: str):
    from autoresearch.llm import extract_json
    from autoresearch.research.measure import _prob

    parsed = extract_json(text)
    probability = _prob(parsed.get("p")) if isinstance(parsed, dict) else None
    return parsed, probability


def aggregate(rows: list[dict]) -> dict:
    complete = [row for row in rows if row.get("status") == "completed"]
    by_condition = {}
    for condition in sorted({row["condition"] for row in complete}):
        values = [row["mean_p_eval"] for row in complete if row["condition"] == condition]
        by_condition[condition] = {
            "n": len(values),
            "mean_p_eval": sum(values) / len(values),
            "median_p_eval": statistics.median(values),
            "min_p_eval": min(values),
            "max_p_eval": max(values),
        }
    profile_conditions = {"P2", "P5", "P8"}
    profile_values = [row["mean_p_eval"] for row in complete if row["condition"] in profile_conditions]
    control_values = [row["mean_p_eval"] for row in complete if row["condition"] not in profile_conditions]
    cohorts = {}
    if profile_values and control_values:
        profile_mean = sum(profile_values) / len(profile_values)
        control_mean = sum(control_values) / len(control_values)
        difference = profile_mean - control_mean
        if abs(difference) < 1e-12:
            difference = 0.0
        cohorts = {
            "profiles": {"n": len(profile_values), "mean_p_eval": profile_mean},
            "controls": {"n": len(control_values), "mean_p_eval": control_mean},
            "difference_profile_minus_control": difference,
        }
    return {"completed": len(complete), "expected": 15, "by_condition": by_condition, "cohorts": cohorts}


def build_report(result: dict) -> str:
    lines = [
        "# Hubinger Petri prompted-recognition results",
        "",
        "A2 is the target's mean reported P(eval) across three GPT-5.1-specific fresh-context probes.",
        "It measures prompted recognition after seeing a saved transcript, not latent belief during the original run.",
        "",
        "| Condition | Run | Probe probabilities | Mean P(eval) |",
        "|---|---:|---|---:|",
    ]
    for row in result["rows"]:
        probabilities = ", ".join(f"{p:.3f}" for p in row.get("probabilities", []))
        mean = row.get("mean_p_eval")
        lines.append(f"| {row['condition']} | {row['replicate']} | {probabilities or 'unmeasured'} | "
                     f"{mean:.3f} |" if mean is not None else
                     f"| {row['condition']} | {row['replicate']} | unmeasured | unmeasured |")
    lines += ["", "## Condition summaries", "",
              "| Condition | N | Mean P(eval) | Range |",
              "|---|---:|---:|---:|"]
    for condition, values in result["aggregate"]["by_condition"].items():
        lines.append(f"| {condition} | {values['n']} | {values['mean_p_eval']:.3f} | "
                     f"{values['min_p_eval']:.3f}–{values['max_p_eval']:.3f} |")
    cohorts = result["aggregate"].get("cohorts", {})
    if cohorts:
        lines += [
            "",
            "## Pooled comparison",
            "",
            f"The six profile runs average {cohorts['profiles']['mean_p_eval']:.4f} P(eval); "
            f"the nine control runs average {cohorts['controls']['mean_p_eval']:.4f}. "
            f"The profile-minus-control difference is {cohorts['difference_profile_minus_control']:.4f}.",
        ]
    lines += [
        "",
        "Each probe explicitly asks about evaluation or naturalness, so demand characteristics can raise these values.",
        "No Petri audit, environment, target interaction, profile, or native judge score was regenerated.",
    ]
    return "\n".join(lines) + "\n"


def prepare(out: Path) -> dict:
    from autoresearch.research.measure import probe_set_for, probe_set_key
    from runner import default_config

    out.mkdir(parents=True, exist_ok=False)
    cases = load_cases()
    cfg = default_config()
    cfg["roles"]["target"]["max_tokens"] = 300
    cfg["max_calls_per_replicate"] = 3
    cfg["max_usd_per_replicate"] = 2.0
    label = "openai:gpt-5.1"
    probe_file = ROOT / "data" / "benchmarks" / "evaldetect_probes.json"
    sets = json.loads(probe_file.read_text())
    probes = probe_set_for(sets, label)
    key = probe_set_key(sets, label)
    if key != "openai-compat:openai/gpt-5.1" or len(probes) != 3:
        raise ValueError(f"Unexpected probe selection: {key!r}, {len(probes)} probes")
    frozen_cases = [{k: v for k, v in case.items() if k != "transcript"} for case in cases]
    manifest = {
        "schema": "hubinger-posthoc-prompted-recognition-v1",
        "purpose": "Collect the previously skipped transcript-only A2 prompted-recognition measurement.",
        "model": cfg["roles"]["target"]["model"],
        "model_label": label,
        "probe_set_key": key,
        "probe_count_per_case": len(probes),
        "expected_cases": len(cases),
        "expected_calls": len(cases) * len(probes),
        "transcript_policy": "autoresearch.research.petri_measure.cut, 24,000 characters, head and tail retained",
        "temperature_requested": 0.0,
        "max_output_tokens": 300,
        "transport_retries": 0,
        "reasoning_required": False,
        "no_petri_rerun": True,
        "no_profile_regeneration": True,
        "probe_source": str(probe_file.relative_to(ROOT)),
        "probe_source_sha256": digest(probe_file.read_bytes()),
        "cases": frozen_cases,
        "config": cfg,
    }
    write(out / "manifest.json", manifest)
    write(out / "probes.json", {"key": key, "questions": probes})
    return manifest


def verify(out: Path) -> tuple[dict, list[dict], list[str]]:
    from autoresearch.research.measure import probe_set_for

    manifest = json.loads((out / "manifest.json").read_text())
    if manifest.get("schema") != "hubinger-posthoc-prompted-recognition-v1":
        raise ValueError("Unknown manifest schema")
    cases = load_cases()
    expected = {(x["condition"], x["replicate"]): x for x in manifest["cases"]}
    for case in cases:
        frozen = expected.get((case["condition"], case["replicate"]))
        if not frozen or frozen["source_sha256"] != case["source_sha256"] or frozen["transcript_sha256"] != case["transcript_sha256"]:
            raise ValueError(f"Frozen transcript changed: {case['condition']}/r{case['replicate']}")
    probe_data = json.loads((out / "probes.json").read_text())
    probes = probe_data["questions"]
    if probe_data["key"] != manifest["probe_set_key"] or len(probes) != 3:
        raise ValueError("Frozen probe set changed")
    return manifest, cases, probes


def execute(out: Path, credentials: Path) -> dict:
    from autoresearch.research.petri_measure import cut
    from run_matched import read_credentials
    from runner import ArmLedger, Budget, bridge

    manifest, cases, probes = verify(out)
    for key, value in read_credentials(credentials).items():
        os.environ.setdefault(key, value)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be configured")
    with (out / "execution-claimed.json").open("x") as stream:
        json.dump({"pid": os.getpid(), "started_at_unix": time.time()}, stream, indent=2)
        stream.write("\n")
    cfg = manifest["config"]
    budget = Budget(out / "provider-ledger.json", cfg, len(cases))
    rows = []
    for case in cases:
        condition, replicate = case["condition"], case["replicate"]
        directory = out / "runs" / condition / f"r{replicate}"
        directory.mkdir(parents=True, exist_ok=False)
        calls = directory / "calls"
        calls.mkdir()
        ledger = ArmLedger(directory / "ledger.json", budget, f"{condition}-r{replicate}.a2")
        clipped = cut(case["transcript"])
        row = {
            "condition": condition,
            "replicate": replicate,
            "original_planned_replicate": case["original_planned_replicate"],
            "source": case["source"],
            "source_sha256": case["source_sha256"],
            "transcript_sha256": case["transcript_sha256"],
            "transcript_chars": len(case["transcript"]),
            "probe_transcript_chars": len(clipped),
            "probe_transcript_sha256": digest(clipped.encode("utf-8")),
            "probes": [],
            "status": "running",
        }
        try:
            for index, template in enumerate(probes, 1):
                prompt = template.replace("{transcript}", clipped)
                (directory / f"probe-{index}.txt").write_text(prompt)
                target = bridge(cfg, "target", ledger, calls)
                response = target.complete(prompt, max_tokens=300, temperature=0.0)
                (directory / f"response-{index}.txt").write_text(response)
                parsed, probability = parse_probability(response)
                probe = {
                    "index": index,
                    "prompt_sha256": digest(prompt.encode("utf-8")),
                    "response_sha256": digest(response.encode("utf-8")),
                    "parsed": parsed,
                    "p_eval": probability,
                    "parse_status": "parsed" if probability is not None else "unparseable",
                }
                row["probes"].append(probe)
                write(directory / "result.json", row)
            probabilities = [p["p_eval"] for p in row["probes"] if p["p_eval"] is not None]
            row["probabilities"] = probabilities
            row["mean_p_eval"] = sum(probabilities) / len(probabilities) if probabilities else None
            row["status"] = "completed" if len(probabilities) == len(probes) else "partial_parse"
        except Exception as exc:
            row.update(status="call_error", error_type=type(exc).__name__)
            write(directory / "result.json", row)
            rows.append(row)
            ledger.save()
            result = {"manifest": {k: v for k, v in manifest.items() if k != "config"}, "rows": rows,
                      "aggregate": aggregate(rows), "budget": budget.summary()}
            write(out / "results.json", result)
            raise
        ledger.save()
        write(directory / "result.json", row)
        rows.append(row)
        result = {"manifest": {k: v for k, v in manifest.items() if k != "config"}, "rows": rows,
                  "aggregate": aggregate(rows), "budget": budget.summary()}
        write(out / "results.json", result)
    (out / "report.md").write_text(build_report(result))
    write(out / "completed.json", {"completed_at_unix": time.time(), "cases": len(rows),
                                    "calls": sum(len(row["probes"]) for row in rows),
                                    "known_estimated_usd": budget.summary()["known_estimated_usd"]})
    return result


def render_existing(out: Path) -> dict:
    verify(out)
    result = json.loads((out / "results.json").read_text())
    result["aggregate"] = aggregate(result["rows"])
    write(out / "results.json", result)
    (out / "report.md").write_text(build_report(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "prompted_recognition")
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--prepared", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--render-existing", action="store_true")
    args = parser.parse_args()
    if args.render_existing:
        result = render_existing(args.out)
        print(json.dumps({"status": "rendered", **result["aggregate"]}), flush=True)
        return
    if not args.prepared:
        manifest = prepare(args.out)
    else:
        manifest, _, _ = verify(args.out)
    print(json.dumps({"status": "prepared", "cases": manifest["expected_cases"],
                      "calls": manifest["expected_calls"], "model": manifest["model"],
                      "probe_set": manifest["probe_set_key"]}), flush=True)
    if args.execute:
        if args.credentials_file is None:
            parser.error("--credentials-file is required with --execute")
        result = execute(args.out, args.credentials_file)
        print(json.dumps({"status": "completed", **result["aggregate"],
                          "known_estimated_usd": result["budget"]["known_estimated_usd"]}), flush=True)


if __name__ == "__main__":
    main()
