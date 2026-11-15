"""Run Petri 2.0 for every (condition, seed) with the same target, auditor, judge and settings.

Usage:
    python run_petri.py --conditions stock --split dev            # stock baseline on dev seeds
    python run_petri.py --conditions stock control --split hidden --epochs 5
    python run_petri.py --conditions stock --split dev --seeds seed_48 --epochs 1   # smoke test
    PIPELINE_CONFIG=config_sonnet45.yaml python run_petri.py ...           # Sonnet 4.5 target

All logs go to out/logs/ (one .eval per condition x seed, tagged with condition, split and
seed_id in the task metadata). Re-running skips condition x seed pairs that already have a
successful log unless --force is passed.
"""

from __future__ import annotations

import argparse

from inspect_ai import eval as inspect_eval
from inspect_ai.log import list_eval_logs, read_eval_log
from petri.tasks.petri import audit

from common import OUT, check_auditor_prompt, iter_condition_seeds, load_config, target_model


def done_keys() -> set[tuple]:
    log_dir = OUT / "logs"
    if not log_dir.exists():
        return set()
    keys = set()
    for info in list_eval_logs(str(log_dir)):
        h = read_eval_log(info, header_only=True)
        md = h.eval.metadata or {}
        if h.status == "success" and "condition" in md:
            keys.add((md["condition"], md["split"], md["seed_id"]))
    return keys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", nargs="+", required=True)
    ap.add_argument("--split", required=True, choices=["dev", "hidden"])
    ap.add_argument("--seeds", nargs="*", help="only these seed ids")
    ap.add_argument("--epochs", type=int)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    cfg = load_config()
    m, p = cfg["models"], cfg["petri"]
    epochs = a.epochs or p["epochs"]

    done = set() if a.force else done_keys()
    jobs = []
    for cond in a.conditions:
        for seed_id, seed_f, aud_f in iter_condition_seeds(cond, a.split):
            if a.seeds and seed_id not in a.seeds:
                continue
            problems = check_auditor_prompt(aud_f.read_text())
            if problems:
                raise SystemExit(f"{cond}/{seed_id}: {problems}")
            if (cond, a.split, seed_id) in done:
                print(f"skip {cond}/{a.split}/{seed_id} (already done)")
                continue
            # Pass the seed as a one-item list so Petri does not split it on newlines.
            t = audit(
                max_turns=p["max_turns"],
                seed_instructions=[seed_f.read_text().strip()],
                auditor_system_message=str(aud_f),
                transcript_save_dir=str(OUT / "transcripts" / cond / a.split / seed_id),
            )
            t.metadata = {"condition": cond, "split": a.split, "seed_id": seed_id}
            jobs.append(t)

    print(f"{len(jobs)} tasks x {epochs} epochs")
    if jobs:
        inspect_eval(
            jobs,
            model=target_model(cfg),
            model_roles={"auditor": m["auditor"], "target": target_model(cfg), "judge": m["petri_judge"]},
            epochs=epochs,
            log_dir=str(OUT / "logs"),
            max_tasks=p["max_tasks"],
            max_connections=p["max_connections"],
            fail_on_error=False,
            display="plain",
        )


if __name__ == "__main__":
    main()
