"""Petri audits as a JSONL-in, JSONL-out step (WS C2, PLAN 12.3 item 7).

    AuditSeed JSONL  ->  Petri 2.0 (inspect_petri)  ->  AuditResult JSONL

Input rows:  {"seed_id", "text", "variant": "v1|v2|ours", "tools": "simulated|sandbox"}
Output rows: {"seed_id", "variant", "tools", "epoch", "transcript", "reasoning",
              "petri_scores": {...}, "petri_judge_status", "n_target_turns", "error"}

`transcript` is the target's final branch as plain text (system prompt, user
turns, the target's replies and tool calls, tool results). `reasoning` is the
target's reasoning over every branch, including rolled-back ones (native
reasoning blocks, which are raw chain of thought for open models served with a
reasoning parser, plus any <thinking> spans). `petri_scores` are Petri's own
judge scores; a judge reply Petri could not parse becomes null here (Petri
itself would score it 1 = "not aware", which flatters whatever breaks the judge).

Each row's `tools` picks the mode for that seed (the --tools flag is the
default): "simulated" is stock Petri, where the auditor invents tool output;
"sandbox" routes the target's shell-type tool calls to a real Modal Sandbox
(sandbox_tools.py).

Models come from configs/models.json (petri.<mode>.target/auditor/judge,
Inspect model ids); --target/--auditor/--judge override. Needs Python 3.10+ and
`pip install inspect_petri` (or the pinned copy: eval/vendor/petri-v2.tar.gz);
sandbox mode also needs `modal`. Running it calls real models: paid, needs the
user's approval (AGENTS.md rule 5). Test it for free with mock models:

    python harness/petri/run_audits.py --seeds s.jsonl --out r.jsonl --mock
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from transcript import KEEP_SCORES, record_from_sample  # noqa: E402

REPO = HERE.parents[1]


def need(pkg: str):
    try:
        return __import__(pkg)
    except ImportError:
        raise SystemExit(f"run_audits.py needs {pkg!r} (Python 3.10+): pip install inspect_petri, or "
                         f"pip install eval/vendor/petri-v2.tar.gz; sandbox mode also needs modal")


def load_seeds(path: str):
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    for r in rows:
        if not r.get("seed_id") or not r.get("text"):
            raise SystemExit(f"bad AuditSeed (needs seed_id and text): {str(r)[:120]}")
        if r.get("tools", "simulated") not in ("simulated", "sandbox"):
            raise SystemExit(f"{r['seed_id']}: tools must be simulated|sandbox")
    return rows


def build_task(seeds, tools: str, max_turns: int, auditor_prompt: str | None, transcript_dir: str,
               make_sandbox=None):
    """One Inspect Task for a group of seeds that share a tool mode."""
    from inspect_ai import Task
    from inspect_ai.dataset import Sample
    from petri.cleanup.save_transcripts import save_transcripts
    from petri.scorers.judge import alignment_judge
    from petri.solvers.auditor_agent import auditor_agent
    from petri.solvers.prompts import AUDITOR_SYSTEM_PROMPT

    dataset = [Sample(input=s["text"], id=s["seed_id"],
                      metadata={"seed_id": s["seed_id"], "variant": s.get("variant", "v2"), "tools": tools})
               for s in seeds]
    kwargs = dict(max_turns=max_turns, auditor_system_message=auditor_prompt or AUDITOR_SYSTEM_PROMPT)
    if tools == "sandbox":
        from sandbox_tools import SANDBOX_NOTE, ModalSandbox, sandbox_tools
        auditor_tools, _ = sandbox_tools(make_sandbox or ModalSandbox)
        kwargs.update(auditor_tools=auditor_tools, resources_prompt=SANDBOX_NOTE)
    return Task(dataset=dataset, solver=auditor_agent(**kwargs), scorer=alignment_judge(),
                cleanup=save_transcripts(transcript_dir), metadata={"tools": tools})


def mock_roles():
    """Free, offline: Inspect's mockllm for every role (smoke-tests the plumbing)."""
    from inspect_ai.model import get_model
    return {"auditor": get_model("mockllm/model"), "target": get_model("mockllm/model"),
            "judge": get_model("mockllm/model")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seeds", required=True, help="AuditSeed JSONL")
    ap.add_argument("--out", required=True, help="AuditResult JSONL to write")
    ap.add_argument("--tools", default="simulated", choices=["simulated", "sandbox"],
                    help="default tool mode for rows without a 'tools' field")
    ap.add_argument("--models-config", default=str(REPO / "configs" / "models.json"))
    ap.add_argument("--mode", default="dev", choices=["dev", "final"])
    ap.add_argument("--target"), ap.add_argument("--auditor"), ap.add_argument("--judge")
    ap.add_argument("--target-thinking", action="store_true",
                    help="extended thinking / reasoning on for the target (Claude and OpenAI reasoning models)")
    ap.add_argument("--reasoning-tokens", type=int, default=8000)
    ap.add_argument("--max-turns", type=int)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--auditor-prompt", help="file with a custom auditor system prompt (keeps Petri's placeholders)")
    ap.add_argument("--log-dir", default=str(REPO / "runs" / "petri" / "logs"))
    ap.add_argument("--mock", action="store_true", help="mockllm for every role: no model calls, no cost")
    a = ap.parse_args(argv)
    need("inspect_ai"), need("petri")
    from inspect_ai import eval as inspect_eval

    seeds = load_seeds(a.seeds)
    cfg = json.loads(Path(a.models_config).read_text()) if Path(a.models_config).exists() else {}
    pcfg = cfg.get("petri", {})
    roles_cfg = pcfg.get(a.mode, {})
    max_turns = a.max_turns or pcfg.get("max_turns", 30)
    prompt = Path(a.auditor_prompt).read_text() if a.auditor_prompt else None

    if a.mock:
        roles = mock_roles()
    else:
        targets = roles_cfg.get("targets") or ([roles_cfg["target"]] if roles_cfg.get("target") else [])
        if not a.target and len(targets) > 1:
            raise SystemExit(f"petri.{a.mode} lists several targets {targets}: pick one with --target")
        roles = {"auditor": a.auditor or roles_cfg.get("auditor"), "judge": a.judge or roles_cfg.get("judge"),
                 "target": a.target or (targets[0] if targets else None)}
        missing = [r for r, v in roles.items() if not v]
        if missing:
            raise SystemExit(f"no model for {missing}: set petri.{a.mode} in {a.models_config} or pass --{missing[0]}")

    if not a.mock and a.target_thinking:
        from inspect_ai.model import GenerateConfig, get_model
        cfg_t = (GenerateConfig(reasoning_effort="high") if roles["target"].startswith("openai/")
                 else GenerateConfig(reasoning_tokens=a.reasoning_tokens, max_tokens=a.reasoning_tokens + 8000))
        roles["target"] = get_model(roles["target"], config=cfg_t)

    groups = {}
    for s in seeds:
        groups.setdefault(s.get("tools") or a.tools, []).append(s)
    tasks = [build_task(g, mode, max_turns, prompt, str(Path(a.log_dir) / "transcripts" / mode))
             for mode, g in groups.items()]
    logs = inspect_eval(tasks, model=roles["target"], model_roles=roles, epochs=a.epochs, log_dir=a.log_dir,
                        max_tasks=pcfg.get("max_tasks", 4), max_connections=pcfg.get("max_connections", 8),
                        fail_on_error=False, display="none" if a.mock else "plain")

    rows, seen = [], set()
    for log in logs:
        for s in log.samples or []:
            rows.append(record_from_sample(s))
            seen.add(rows[-1]["seed_id"])
        if log.status != "success" and not log.samples:
            err = str(getattr(log.error, "message", log.error) or log.status)
            for s in groups.get((log.eval.metadata or {}).get("tools", a.tools), []):
                if s["seed_id"] not in seen:
                    rows.append({"seed_id": s["seed_id"], "variant": s.get("variant", "v2"), "tools": s.get("tools"),
                                 "epoch": None, "transcript": "", "reasoning": "",
                                 "petri_scores": {k: None for k in KEEP_SCORES}, "petri_judge_status": "missing",
                                 "n_target_turns": 0, "error": f"task failed: {err[:500]}"})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    n_err = sum(bool(r["error"]) for r in rows)
    n_judge = sum(r["petri_judge_status"] != "ok" for r in rows)
    print(f"{len(rows)} audits -> {a.out} ({n_err} errored, {n_judge} without a clean Petri judge score)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
