"""WS A CLI, independent of the concurrently edited research-loop CLI."""
import argparse
import json
from pathlib import Path

from ..llm import Budget, get_llm
from .backends import CodexLLM, OpenAILLM
from .fidelity import run_fidelity, select_users
from .methods import create_method
from .prefdata import build_manifest, download_dataset, drop_exact_repeats, load_records, save_records, write_manifest
from .usermodel import load_model


def backend(args):
    budget = Budget(max_calls=args.max_calls, max_seconds=args.max_seconds)
    if args.backend == "codex-cli":
        return CodexLLM(args.model, budget=budget)
    if args.model == "default":
        raise ValueError("API/Claude backends require an explicit --model")
    if args.backend == "openai":
        return OpenAILLM(args.model, budget=budget, max_usd=args.max_usd)
    return get_llm(args.backend, args.model, budget)


def model_args(parser):
    parser.add_argument("--backend", choices=["codex-cli", "openai", "anthropic", "openai-compat", "claude-cli"],
                        default="codex-cli")
    parser.add_argument("--model", default="default")
    parser.add_argument("--max-calls", type=int, default=100)
    parser.add_argument("--max-seconds", type=float, default=300)
    parser.add_argument("--max-usd", type=float, default=1.0,
                        help="conservative request-reservation cap for the direct OpenAI backend only")
    parser.add_argument("--cache", default="runs/taste-cache")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="download public preferences and freeze upstream splits")
    prepare.add_argument("--datasets", nargs="+", choices=["prism"], default=["prism"])
    prepare.add_argument("--raw-cache", default="runs/prefdata/raw")
    prepare.add_argument("--output", default="runs/prefdata/prism.jsonl")
    prepare.add_argument("--manifest", default="data/prefdata/prism-splits.json")
    prepare.add_argument("--seed", type=int, default=0)
    fidelity = commands.add_parser("fidelity", help="compare methods on a fixed user partition")
    fidelity.add_argument("--records", default="runs/prefdata/prism.jsonl")
    fidelity.add_argument("--manifest", default="data/prefdata/prism-splits.json")
    fidelity.add_argument("--dataset", choices=["prism"], default="prism")
    fidelity.add_argument("--methods", nargs="+", choices=["m%d" % i for i in range(8)], default=["m0", "m1"])
    fidelity.add_argument("--users", choices=["dev", "test"], default="dev")
    fidelity.add_argument("--n-users", type=int)
    fidelity.add_argument("--seed", type=int, default=0)
    fidelity.add_argument("--final", action="store_true")
    fidelity.add_argument("--dry-run", action="store_true")
    fidelity.add_argument("--output", default="runs/fidelity/dev")
    fidelity.add_argument("--config", default="{}", help="JSON config shared by requested methods")
    model_args(fidelity)
    predict = commands.add_parser("predict", help="use a saved model without fitting again")
    predict.add_argument("--artifact", required=True)
    predict.add_argument("--context", required=True)
    predict.add_argument("--options", nargs="+", required=True)
    model_args(predict)
    label = commands.add_parser("label", help="label logged decisions in the order of an active_queries queue")
    label.add_argument("--researcher", required=True)
    label.add_argument("--queue", required=True, help="queue JSONL from `active_queries queue`")
    label.add_argument("--root", default=None, help="researchers root (default: data/researchers)")
    label.add_argument("--limit", type=int)
    label.add_argument("--memory", default="runs/research_memory",
                       help="local shared-memory dir for LABEL/DISAGREE facts when PAST_API_KEY is unset")
    args = parser.parse_args(argv)
    if args.command == "label":
        import os
        from ..integrations.shared_memory import get_shared_memory
        from .active_queries import label_from_queue
        from .researcher import DEFAULT_ROOT
        shared = get_shared_memory(os.path.join(args.memory, "shared.jsonl"))
        print(json.dumps(label_from_queue(args.root or DEFAULT_ROOT, args.researcher, args.queue, shared,
                                          limit=args.limit)))
        return
    if args.command == "prepare":
        if len(set(args.datasets)) != len(args.datasets):
            raise ValueError("duplicate dataset selection")
        records = [r for dataset in args.datasets for r in download_dataset(dataset, args.raw_cache, args.seed)]
        records, removed = drop_exact_repeats(records)
        manifest = build_manifest(records, args.seed)
        if Path(args.output).exists() and build_manifest(load_records(args.output), args.seed) != manifest:
            raise ValueError("existing normalized records differ; use a new snapshot path")
        write_manifest(args.manifest, manifest)
        if removed:
            removal = Path(args.manifest)
            write_manifest(removal.with_name(removal.stem + "-removed.json"),
                           {"manifest_id": manifest["manifest_id"], "removed": removed})
        if not Path(args.output).exists():
            save_records(args.output, records)
        print(json.dumps({"n_examples": len(records), "n_removed_repeats": len(removed),
                          "n_users": len(manifest["users"]),
                          "manifest_id": manifest["manifest_id"]}))
    elif args.command == "fidelity":
        records = load_records(args.records)
        manifest = json.loads(Path(args.manifest).read_text())
        if build_manifest(records, manifest["seed"]) != manifest:
            raise ValueError("records do not match manifest")
        if len(set(args.methods)) != len(args.methods):
            raise ValueError("duplicate method selection")
        selected = select_users(manifest, args.dataset, args.users, args.n_users, args.seed)
        if args.dry_run:
            print(json.dumps({"dataset": args.dataset, "partition": args.users, "methods": args.methods,
                              "n_users": len(selected), "n_predictions": len(args.methods) *
                              sum(len(manifest["users"][u]["test"]) for u in selected),
                              "note": "Prediction count excludes method fitting/search calls. No model calls made."}))
            return
        if args.final and args.model == "default":
            raise ValueError("final comparison requires a pinned --model")
        config = json.loads(args.config)
        if not isinstance(config, dict):
            raise ValueError("--config must be a JSON object")
        llm = backend(args)
        factories = {method: (lambda user, method=method: create_method(
            method, llm, seed=args.seed, cache_dir=args.cache, max_calls=args.max_calls, **config))
            for method in args.methods}
        report = run_fidelity(records, args.manifest, factories, args.output, args.dataset,
                              args.users, args.n_users, args.seed, args.final,
                              run_config={"backend": args.backend, "model": args.model, "method_config": config,
                                          "max_calls": args.max_calls, "max_seconds": args.max_seconds,
                                          "max_usd": args.max_usd if args.backend == "openai" else None})
        print(json.dumps({"report": str(Path(args.output) / "report.json"),
                          "backend_budgets": report["backend_budgets"],
                          "methods": {m: {k: v for k, v in result.items() if k != "per_user"}
                                      for m, result in report["methods"].items()}}, indent=2))
    else:
        from dataclasses import asdict
        model = load_model(args.artifact, backend(args), cache_dir=args.cache, max_calls=args.max_calls)
        print(json.dumps(asdict(model.predict(args.context, args.options)), indent=2))


if __name__ == "__main__":
    main()
