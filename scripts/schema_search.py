"""Bounded dev-only search: python3 -m scripts.schema_search --help."""
import argparse
import json
import re
from pathlib import Path

from autoresearch.taste.__main__ import backend, model_args
from autoresearch.taste.fidelity import run_fidelity
from autoresearch.taste.methods import create_method
from autoresearch.taste.prefdata import load_records


def run_search(records, manifest, configs, llm, output, dataset, seed=0, n_users=None,
               cache_dir=None, max_calls=100):
    if not isinstance(configs, list) or not 1 <= len(configs) <= 8:
        raise ValueError("schema search requires 1–8 explicit configurations")
    ids = set()
    for c in configs:
        if (not isinstance(c, dict) or c.get("method") not in ("m5", "m6", "m7") or
                not isinstance(c.get("id"), str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", c["id"]) or
                c["id"] in ids or not isinstance(c.get("config"), dict)):
            raise ValueError("each configuration needs a unique safe id, method m5/m6/m7, and config object")
        ids.add(c["id"])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for c in configs:
        factory = {c["method"]: lambda user, c=c: create_method(
            c["method"], llm, seed=seed, cache_dir=cache_dir, max_calls=max_calls, **c["config"])}
        report = run_fidelity(records, manifest, factory, output / c["id"], dataset,
                              users="dev", n_users=n_users, seed=seed,
                              run_config={"schema_config": c, "purpose": "development_only"})
        score = report["methods"][c["method"]]
        results.append({**c, "accuracy": score["accuracy"], "failures": score["failures"],
                        "usage": score["usage"]})
        # Preserve partial search evidence even when a later configuration fails.
        (output / "search.json").write_text(json.dumps({"partition": "dev", "status": "incomplete",
                                                        "selected_config_id": None, "trials": results}, indent=2))
    complete = len(results) == len(configs) and all(r["failures"] == 0 for r in results)
    selected = max(results, key=lambda r: r["accuracy"])["id"] if complete else None
    summary = {"partition": "dev", "status": "complete" if complete else "incomplete",
               "trials": results, "selected_config_id": selected,
               "note": "Selection requires every declared trial to finish without errors. "
                       "Development selection only; no final-test or transfer claim. Ties use first declared config."}
    (output / "search.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--configs", required=True, help="JSON list of {id,method,config}")
    p.add_argument("--records", default="runs/prefdata/arena.jsonl")
    p.add_argument("--manifest", default="data/prefdata/splits.json")
    p.add_argument("--dataset", choices=["arena", "prism"], required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-users", type=int)
    model_args(p)
    args = p.parse_args(argv)
    print(json.dumps(run_search(load_records(args.records), args.manifest,
                               json.loads(Path(args.configs).read_text()), backend(args), args.output,
                               args.dataset, args.seed, args.n_users, args.cache, args.max_calls), indent=2))


if __name__ == "__main__":
    main()
