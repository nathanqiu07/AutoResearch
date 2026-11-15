"""Modal: run the research system as a parallel swarm and ablation grid.

Setup (once):
    pip install modal && modal setup
    modal secret create autoresearch-keys ANTHROPIC_API_KEY=... EXA_API_KEY=... PAST_API_KEY=...
    (any key may be omitted: no ANTHROPIC -> offline simulator, no EXA -> no web
     scout, no PAST -> shared memory falls back to a modal.Dict)

Run:
    modal run modal_app.py --mode swarm --task eval_awareness --rounds 3 --workers 8
    modal run modal_app.py --mode grid --seeds 8
    modal run modal_app.py --mode research-grid --prereg results/prereg/E5.json --llm anthropic \
        --out results/e5 [--arms market uniform] [--seeds 0] [--max-cells 1] [--dry-run]

research-grid runs `autoresearch research` over a pre-registration's arms x seeds
(autoresearch/grid.py), one container per cell, and writes each cell's outputs to
<out>/<cell>/ with CODE_VERSION. The code version is pinned when the image is built
(AUTORESEARCH_CODE_VERSION), so every cell of a run uses the same code (AGENTS.md
rule 4). A paid grid needs the user's approval (AGENTS.md rule 5) and --yes; it
refuses uncommitted changes under autoresearch/ unless --allow-dirty.
"""
import json
import os
import subprocess

import modal


def _code_version() -> str:
    """Pinned version: the env var inside a container, `git describe` where the image is built."""
    if os.environ.get("AUTORESEARCH_CODE_VERSION"):
        return os.environ["AUTORESEARCH_CODE_VERSION"]
    try:
        out = subprocess.run(["git", "describe", "--always", "--dirty", "--abbrev=12"], capture_output=True,
                             text=True, timeout=10, cwd=os.path.dirname(os.path.abspath(__file__)))
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


CODE_VERSION = _code_version()

app = modal.App("autoresearch")
image = (modal.Image.debian_slim(python_version="3.11")
         .add_local_dir("data", "/root/data")
         .add_local_python_source("autoresearch"))
grid_image = (modal.Image.debian_slim(python_version="3.11")
              .env({"AUTORESEARCH_CODE_VERSION": CODE_VERSION})
              .add_local_dir("data", "/root/data")
              .add_local_python_source("autoresearch"))
secrets = [modal.Secret.from_name("autoresearch-keys")]
shared_dict = modal.Dict.from_name("autoresearch-shared-memory", create_if_missing=True)


class ModalDictMemory:
    """Shared memory over a modal.Dict: every parallel container sees the same
    store. Used only when past.dev is not configured."""
    backend = "modal.Dict"

    def __init__(self, d, namespace):
        self.d, self.ns, self.log = d, namespace, []

    def write(self, agent, content, label="", metadata=None):
        import uuid
        self.d[f"{self.ns}:{uuid.uuid4().hex}"] = {"author": agent, "content": content}
        self.log.append({"op": "write", "agent": agent})

    def recall(self, agent, query, limit=50):
        rows = [v for k, v in self.d.items() if k.startswith(self.ns + ":")]
        self.log.append({"op": "recall", "agent": agent})
        return rows[-max(limit, 200):]

    def facts(self, agent, query, kind, limit=50, exclude_author=None):
        from autoresearch.integrations.shared_memory import SharedMemory
        return SharedMemory.facts(self, agent, query, kind, limit, exclude_author)


def _shared(namespace):
    if os.environ.get("PAST_API_KEY"):
        from autoresearch.integrations.shared_memory import PastDevMemory
        return PastDevMemory(run_tag=namespace)
    return ModalDictMemory(shared_dict, namespace)


@app.function(image=image, secrets=secrets, timeout=3600, max_containers=64)
def worker(spec):
    from autoresearch.swarm import run_cell
    spec = {**spec, "llm": spec.get("llm") or ("anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "offline")}
    return run_cell(spec, shared=_shared(spec["namespace"]) if spec.get("use_shared", True) else None)


@app.function(image=grid_image, secrets=secrets, timeout=6 * 3600, max_containers=64)
def research_cell(cell):
    from autoresearch.grid import run_cell
    return run_cell(cell, root="/root")


def _research_grid(prereg, arms, seeds, llm, out, max_cells, dry_run, yes, allow_dirty):
    from autoresearch.grid import grid_cells, load_prereg, write_cell
    if not prereg:
        raise SystemExit("--mode research-grid needs --prereg results/prereg/<exp>.json")
    cells = grid_cells(load_prereg(prereg), arms.split() or None,
                       [int(s) for s in seeds.split()] if seeds else None, llm or "anthropic")
    cells = cells[:max_cells] if max_cells else cells
    print(f"{len(cells)} cell(s), code version {CODE_VERSION}")
    for c in cells:
        print(" ", c["cell"], " ".join(c["argv"]))
    if dry_run:
        return
    if CODE_VERSION.endswith("-dirty") and not allow_dirty:
        raise SystemExit("uncommitted changes: commit first so CODE_VERSION names the code that ran (or --allow-dirty)")
    if (llm or "anthropic") != "offline" and not yes:
        raise SystemExit("a paid grid needs --yes once the user has approved it (AGENTS.md rule 5)")
    failed = 0
    for res in research_cell.map(cells, return_exceptions=True):
        if isinstance(res, Exception):
            failed += 1
            print("cell raised:", repr(res)[:300])
            continue
        d = write_cell(res, out)
        failed += not res["ok"]
        print(("ok    " if res["ok"] else "FAILED"), res["cell"], f"{res['seconds']}s ->", d,
              "" if res["ok"] else (res["error"] or "")[:300])
    print(f"{len(cells) - failed}/{len(cells)} cells finished -> {out}")


@app.local_entrypoint()
def main(mode: str = "swarm", task: str = "eval_awareness", rounds: int = 3, workers: int = 8,
         iterations: int = 8, samples: int = 8, seeds: str = "", researcher: str = "demo_realist",
         llm: str = "", out: str = "", prereg: str = "", arms: str = "", max_cells: int = 0,
         dry_run: bool = False, yes: bool = False, allow_dirty: bool = False):
    import uuid
    if mode == "research-grid":
        return _research_grid(prereg, arms, seeds, llm, out or "results/research_grid", max_cells, dry_run, yes,
                              allow_dirty)
    out = out or "results/modal_run.json"
    seeds = int(seeds) if seeds else 4
    from autoresearch.benchmark import CONDITIONS
    from autoresearch.swarm import run_swarm, summarize_rounds
    from autoresearch.tasks import TASKS
    ns = uuid.uuid4().hex[:8]
    common = dict(iterations=iterations, samples=samples, researcher=researcher, llm=llm or None)
    if mode == "swarm":
        # with vs without the shared memory layer, same seeds, all in parallel per round
        report = {}
        for arm, use in (("shared", True), ("isolated", False)):
            report[arm] = run_swarm(task, rounds, workers,
                                    map_fn=lambda specs, u=use, a=arm: worker.map(
                                        [{**s, "namespace": f"{ns}-{a}", "use_shared": u} for s in specs]),
                                    **common)
            print(arm, json.dumps(report[arm]["rounds"], indent=1))
    else:
        specs = [{"task": t, "seed": s, "round": 0, "worker": f"{c}-{t}-{s}", "namespace": f"{ns}-{c}-{s}",
                  "use_shared": CONDITIONS[c]["use_memory"], "flags": CONDITIONS[c], **common}
                 for c in CONDITIONS for t in TASKS for s in range(seeds)]
        rows = list(worker.map(specs))
        report = {"grid": rows}
        for c in CONDITIONS:
            sel = [r for r in rows if r["worker"].startswith(c + "-")]
            print(c, round(sum(r["score"] for r in sel) / len(sel), 3))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out, "w"), indent=1, default=str)
    print("wrote", out)
