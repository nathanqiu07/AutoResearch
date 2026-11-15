"""Replay the four PLAN §10 demo moments from a committed Git snapshot.

    python3 scripts/demo.py
    python3 scripts/demo.py --paths results/e5 results/pastdev_smoke --json
    python3 scripts/demo.py --trail        # adds a fifth moment: the Exa source-to-decision trail

This command reads Git objects only. It never imports model backends, launches
workers, writes memory, or makes network calls. Missing evidence is shown as
missing; --strict returns a failure unless every moment shown has evidence.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from typing import List
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout


def trail_moment(loaded, revision: str) -> dict:
    """Optional fifth moment: Exa source -> EVIDENCE -> veto/credence -> what ran
    instead (autoresearch/integrations/trail.py), from the committed records
    already loaded. Available only when a veto or fact-check credence update
    links back to a recorded Exa source."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from autoresearch.integrations.trail import Artifacts, build
    art = Artifacts()
    for name, records in loaded:
        art.add(name, records)
    data = build(art, source=revision)
    linked = [t for r in data["runs"] for t in r["vetoes"] + r["credence_updates"]
              if any(s.get("linked") for s in t.get("sources", []))]
    return {"title": "Exa + past.dev: from a source to the decision it changed", "available": bool(linked),
            "evidence": {"runs": len(data["runs"]), "vetoes": data["n_vetoes"],
                         "credence_updates": data["n_credence_updates"], "exa_ideas": data["n_source_trails"],
                         "linked_trails": linked[:3], "missing_fields": [m["field"] for m in data["missing_fields"]]},
            "message": f"{len(linked)} veto/credence trail(s) link to a recorded Exa source. Links the runs did not "
                       "record are listed as missing fields, not reconstructed."}


def replay(ref: str = "HEAD", paths: List[str] = None, root: Path = ROOT, trail: bool = False) -> dict:
    """Resolve ref once, then inspect only committed results under paths.
    trail=True adds the source-to-decision trail as a fifth moment."""
    revision = git("rev-parse", "--verify", ref + "^{commit}", root=root).strip()
    paths = paths or ["results"]
    for path in paths:
        if Path(path).is_absolute() or ".." in Path(path).parts or Path(path).parts[:1] != ("results",):
            raise ValueError("demo paths must be repository-relative paths under results/")
    names = git("ls-tree", "-rz", "--name-only", revision, "--", *paths, root=root).split("\0")
    reports, cells, facts, recalls = [], [], Counter(), []
    reasoning, loaded = [], []
    for name in filter(None, names):
        if not name.endswith((".json", ".jsonl")):
            continue
        raw = git("show", f"{revision}:{name}", root=root)
        try:
            records = [json.loads(line) for line in raw.splitlines() if line.strip()] if name.endswith(".jsonl") else [json.loads(raw)]
        except ValueError:
            continue
        loaded.append((name, records))
        for record in records:
            if not isinstance(record, dict):
                continue
            if all(k in record for k in ("run_id", "baseline", "best")):
                reports.append((name, record))
            if "cell" in record and "ok" in record:
                cells.append((name, record))
            if "recall_any" in record and "n_written" in record:
                recalls.append({"path": name, **record})
            content = record.get("content", "")
            if isinstance(content, str):
                # Match fact kind as a token, including past.dev's author prefix.
                for kind in ("LABEL", "DISAGREE", "BID", "SETTLE"):
                    if kind in content.split():
                        facts[kind] += 1
            if record.get("reasoning"):
                reasoning.append({"path": name, "seed": record.get("seed"),
                                  "preview": str(record["reasoning"])[:500]})

    def provenance(name, rep):
        cfg = rep.get("config") or {}
        compute = rep.get("compute") or {}
        offline = compute.get("calls") == 0 and compute.get("input_tokens", 0) == 0
        return {"path": name, "run_id": rep["run_id"], "arm": rep.get("arm"),
                "seed": cfg.get("seed"), "samples": cfg.get("samples"),
                "code_version": rep.get("code_version", "unknown"),
                "backend": "offline simulator" if offline else "live or unspecified (see source report)",
                "baseline": rep["baseline"], "best": rep["best"],
                "validated": sum(f.get("status") == "validated" for f in rep.get("findings", [])),
                "cost_usd": compute.get("cost_usd"), "wall_seconds": compute.get("wall_seconds")}

    tools = [{**provenance(n, r), "tools": r["tools"], "scenario": r.get("scenario")}
             for n, r in reports if r.get("tools") in ("simulated", "sandbox")]
    tool_modes = {r["tools"] for r in tools}
    # Require matching scenarios, arm and seed for a meaningful tools comparison.
    pairs = {}
    for r in tools:
        key = (r["scenario"], r["arm"], r["seed"], r["code_version"])
        pairs.setdefault(key, set()).add(r["tools"])
    paired = sum(modes == {"simulated", "sandbox"} for modes in pairs.values())
    grid = [{"path": n, "cell": c["cell"], "ok": c["ok"],
             "code_version": c.get("code_version"), "seconds": c.get("seconds")}
            for n, c in cells]
    moments = [
        {"title": "Modal: real tools versus simulated tools", "available": paired > 0,
         "evidence": tools,
         "message": f"{paired} matched scenario/arm/seed/code pair(s); tool modes: {sorted(tool_modes)}. "
                    "Read A1, A2 and validity together; a lower awareness score alone is insufficient."},
        {"title": "Modal: visible target reasoning", "available": bool(reasoning),
         "evidence": reasoning[:3],
         "message": "Saved reasoning is replayed verbatim. Its presence does not establish raw chain of thought; "
                    "API summarized thinking and open-weight raw reasoning must be distinguished in the source."},
        {"title": "Modal: research grid and allocation", "available": bool(grid),
         "evidence": grid,
         "message": f"{sum(bool(c['ok']) for c in grid)}/{len(grid)} saved grid cells succeeded. "
                    "A saved local cell is a pipeline check; only a Modal execution record proves a remote run."},
        {"title": "past.dev: the living user model and market ledger",
         "available": facts["LABEL"] > 0 and facts["DISAGREE"] > 0,
         "evidence": {"fact_counts": dict(facts), "recall_checks": recalls},
         "message": "Labels and disagreements can rebuild a user model between runs. "
                    "Local JSONL recall is not a past.dev recall measurement; no refit improvement is implied."},
    ]
    if trail:
        moments.append(trail_moment(loaded, revision))
    return {"revision": revision, "paths": paths, "moments": moments,
            "runs": [provenance(n, r) for n, r in reports],
            "complete": all(m["available"] for m in moments),
            "caveat": "Replay only. Offline numbers and small live smokes are not scientific findings. "
                      "Missing sponsor evidence remains missing; this demo makes no live calls."}


def render(data: dict) -> str:
    lines = ["AutoResearch: committed-results demo", f"Snapshot: {data['revision']}", data["caveat"]]
    for k, moment in enumerate(data["moments"], 1):
        lines += ["", f"{k}. {moment['title']} [{'saved evidence' if moment['available'] else 'MISSING evidence'}]",
                  moment["message"], json.dumps(moment["evidence"], indent=2, ensure_ascii=False)]
    lines += ["", "Run provenance and scores:", json.dumps(data["runs"], indent=2, ensure_ascii=False)]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="HEAD", help="committed snapshot to replay")
    ap.add_argument("--paths", nargs="+", help="repository-relative evidence paths under results/")
    ap.add_argument("--json", action="store_true", help="machine-readable replay manifest")
    ap.add_argument("--strict", action="store_true", help="fail if any demo moment lacks evidence")
    ap.add_argument("--trail", action="store_true",
                    help="add the Exa source-to-decision trail as a fifth moment (counts toward --strict)")
    args = ap.parse_args(argv)
    try:
        data = replay(args.ref, args.paths, trail=args.trail)
    except (ValueError, subprocess.CalledProcessError) as exc:
        ap.error(str(exc))
    print(json.dumps(data, indent=2, ensure_ascii=False) if args.json else render(data))
    return 1 if args.strict and not data["complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
