"""Modal: run the research system as a parallel swarm and ablation grid.

Setup (once):
    pip install modal && modal setup
    modal secret create autoresearch-keys ANTHROPIC_API_KEY=... EXA_API_KEY=... PAST_API_KEY=...
    (any key may be omitted: no ANTHROPIC -> offline simulator, no EXA -> no web
     scout, no PAST -> shared memory falls back to a modal.Dict)

Run:
    modal run modal_app.py --mode swarm --task eval_awareness --rounds 3 --workers 8
    modal run modal_app.py --mode grid --seeds 8
"""
import json
import os

import modal

app = modal.App("autoresearch")
image = (modal.Image.debian_slim(python_version="3.11")
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


@app.local_entrypoint()
def main(mode: str = "swarm", task: str = "eval_awareness", rounds: int = 3, workers: int = 8,
         iterations: int = 8, samples: int = 8, seeds: int = 4, researcher: str = "demo_realist",
         llm: str = "", out: str = "results/modal_run.json"):
    import uuid
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
