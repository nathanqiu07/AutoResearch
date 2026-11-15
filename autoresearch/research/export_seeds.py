"""Loop designs -> E3b condition files (WS D -> WS C2).

E3b (results/prereg/E3b.json) compares Petri audit conditions: stock seeds, a
no-taste control and the taste conditions. `scripts/c2_e3b.py` scores each
condition from an AuditSeed JSONL file. The loop's agentic runs end with a
best design (a list of interventions); this module turns that design into such
a file by rewriting every seed of one split with the same generator prompts
the run measured with (`PetriMeasurer.rewrite_seed` / `auditor_guidance`).

Each seed is rewritten once, so the condition is a fixed artifact: c2_e3b
audits it `--epochs` times, as it does the stock seeds. Rows keep the base
seed's `split`, and their `seed_id` is `<base>@<condition>`, so c2_e3b pairs
conditions by base seed.

Seeds are picked by their `split` field (E3b's 12 dev / 12 hidden). A run tunes
on dev only; the hidden seeds are rewritten once, at the end, for scoring.
"""
from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

DEV_SPLITS = ("dev",)
HELDOUT_SPLITS = ("hidden", "heldout", "held-out", "test")


def select_split(seeds: List[dict], side: str) -> List[dict]:
    """Seeds on one side: "dev", "hidden" (any of HELDOUT_SPLITS) or "all".
    Every seed must carry a `split` field; a file mixing seeds with and without
    one would put the unlabelled seeds on an arbitrary side."""
    if side == "all":
        return list(seeds)
    missing = [s["seed_id"] for s in seeds if not s.get("split")]
    if missing:
        raise ValueError(f"seeds without a 'split' field: {missing[:5]} ({len(missing)} of {len(seeds)})")
    names = DEV_SPLITS if side == "dev" else HELDOUT_SPLITS
    unknown = sorted({s["split"] for s in seeds} - set(DEV_SPLITS) - set(HELDOUT_SPLITS))
    if unknown:
        raise ValueError(f"unknown split value(s) {unknown}; expected one of {DEV_SPLITS + HELDOUT_SPLITS}")
    return [s for s in seeds if s["split"] in names]


def export_design(report: dict, measurer, seeds: List[dict], condition: str, seed: int = 0,
                  check_faithful: bool = True) -> Tuple[List[dict], List[Dict[str, str]]]:
    """Rewrite `seeds` with the report's best design. Returns (rows, failures).

    `measurer` is a PetriMeasurer built with the run's rewrite mode and auditor
    prompt. An empty design (the run validated nothing) yields the seeds
    unchanged, relabelled to the condition, so the condition still exists and
    equals stock by construction."""
    from .petri_measure import stock_auditor_prompt, with_guidance
    design = [d["text"] for d in report.get("best_design") or []]
    source = f"export-seeds: run {report.get('run_id')} ({report.get('arm') or 'no arm'})"
    if measurer.m.offline:
        return _offline_rows(design, seeds, condition, source), []
    guidance = None
    if design and measurer.rewrite in ("auditor", "both"):
        guidance = measurer.auditor_guidance(design)
        if not guidance:
            return [], [{"seed_id": s["seed_id"], "error": "generator returned no auditor guidance"} for s in seeds]
    def one(k_base):
        """(row, None) or (None, failure) for one seed. Each seed has its own rng, so the rewrites
        and faithfulness checks run concurrently (two reasoning-model calls per seed were the wait)."""
        k, base = k_base
        row = {key: v for key, v in base.items() if key not in ("seed_id", "text", "variant", "auditor_prompt")}
        row.update(seed_id=f"{base['seed_id']}@{condition}", base_seed_id=base["seed_id"], condition=condition,
                   source=source, design=design)
        text = base["text"]
        if design and measurer.rewrite in ("seed", "both"):
            try:
                text = measurer.rewrite_seed(base, design, random.Random(seed * 100003 + k))
            except Exception as e:  # noqa: BLE001  reported per seed, never silently replaced by the stock text
                return None, {"seed_id": base["seed_id"], "error": f"seed rewrite failed: {str(e)[:200]}"}
            if not text:
                return None, {"seed_id": base["seed_id"], "error": "generator returned no rewritten seed"}
        prompt = base.get("auditor_prompt") or measurer.base_auditor_prompt
        if guidance:
            prompt = with_guidance(prompt or stock_auditor_prompt(), guidance)
            row["auditor_guidance"] = guidance
        if prompt:
            row["auditor_prompt"] = prompt
        row["text"] = text
        row["variant"] = "ours" if design else base.get("variant", "v2")
        if design and check_faithful:
            row["faithful"] = measurer.seed_faithful(base["text"], text + (f"\n\n{guidance}" if guidance else ""))
        return row, None
    with ThreadPoolExecutor(max_workers=max(1, min(16, len(seeds)))) as ex:
        done = list(ex.map(one, enumerate(seeds)))   # map keeps seed order
    rows = [r for r, _ in done if r is not None]
    failures = [f for _, f in done if f is not None]
    return rows, failures


def _offline_rows(design: List[str], seeds: List[dict], condition: str, source: str) -> List[dict]:
    """Offline backends cannot rewrite, as in PetriMeasurer's offline path: rows
    keep the stock text with the design appended under a dry-run marker, flagged
    `offline`, so the export -> c2_e3b --offline pipeline can be checked for free.
    They are never a condition to score with real models."""
    rows = []
    for base in seeds:
        row = {k: v for k, v in base.items() if k not in ("seed_id", "text", "variant")}
        row.update(seed_id=f"{base['seed_id']}@{condition}", base_seed_id=base["seed_id"], condition=condition,
                   source=source, design=design, offline=True, variant="ours" if design else base.get("variant", "v2"),
                   text=base["text"] + ("".join(f"\n[offline dry run, not rewritten] {d}" for d in design)))
        rows.append(row)
    return rows


def rewrite_mode(report: dict, override: Optional[str] = None) -> str:
    """The run's rewrite mode (recorded in agentic reports), unless overridden."""
    return override or report.get("petri_rewrite") or "seed"
