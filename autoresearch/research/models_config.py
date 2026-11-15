"""configs/models.json: the agreed model lineup, and checks on it (WS C2, PLAN 4.4 / 12.3 item 4).

The config names every model role once, so all workstreams use the same ids:

  roles:  generator, dev_target, heldout_targets (list), dev_judge (J1),
          heldout_judges (J2, list). Each entry is an autoresearch
          "backend:model" spec (llm.get_llm), "+thinking" where reasoning is on.
  petri:  per mode ("dev" | "final"), Inspect model ids for the Petri harness
          (target, auditor, judge); final mode may list several targets.

Families come from C1's `measure.model_family`, so the config check and the
Measurer's own warnings agree. `research_args(cfg, mode, target)` gives the
`--generator/--target/--judge/--heldout-*` flags for the research CLI, which is
how runs use the API backends instead of claude-cli for targets (api-target).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .measure import model_family

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "models.json"
ROLES = ("generator", "dev_target", "heldout_targets", "dev_judge", "heldout_judges")


def _list(x) -> List[str]:
    return list(x) if isinstance(x, list) else ([x] if x else [])


def config_warnings(cfg: Dict) -> List[str]:
    """Missing roles; held-out judges from the generator's family; held-out
    targets without a cross-family judge; targets running through claude-cli
    (the CLI passes harness context to the model, a confound for eval awareness).
    Petri's own judge is a cross-check only, so its family is not checked."""
    roles = cfg.get("roles", {})
    out = [f"configs/models.json: role {r!r} missing" for r in ROLES if not roles.get(r)]
    gen = roles.get("generator", "")
    gen_fam = model_family(gen) if gen else "other"
    judges = _list(roles.get("heldout_judges"))
    for j in judges:
        if gen_fam != "other" and model_family(j) == gen_fam:
            out.append(f"held-out judge {j} shares the generator's family ({gen_fam})")
    for t in [roles.get("dev_target", "")] + _list(roles.get("heldout_targets")):
        if t.startswith("claude-cli:"):
            out.append(f"target {t} runs through claude-cli: use an API backend (harness-context confound)")
    scorers = judges + _list(roles.get("dev_judge"))   # the headline judge is the first cross-family one
    for t in _list(roles.get("heldout_targets")):
        if scorers and all(model_family(j) == model_family(t) for j in scorers):
            out.append(f"held-out target {t} has no judge from another family (no headline judge)")
    for mode in ("dev", "final"):
        p = cfg.get("petri", {}).get(mode, {})
        for r in ("targets" if mode == "final" else "target", "auditor", "judge"):
            if not p.get(r):
                out.append(f"configs/models.json: petri.{mode}.{r} missing")
    return out


def research_args(cfg: Dict, mode: str = "dev", heldout_target: Optional[str] = None) -> List[str]:
    """CLI flags for `python3 -m autoresearch research|evaluate-design` from the config.
    Final mode needs one held-out target (each is run and reported separately)."""
    r = cfg["roles"]
    args = ["--generator", r["generator"], "--target", r["dev_target"], "--judge", r["dev_judge"]]
    if mode == "final":
        ht = heldout_target or _list(r["heldout_targets"])[0]
        if ht not in _list(r["heldout_targets"]):
            raise ValueError(f"{ht} is not a held-out target in the config")
        args += ["--mode", "final", "--heldout-target", ht, "--heldout-judges", *_list(r["heldout_judges"])]
    return args


def load_models_config(path: Optional[str] = None) -> Dict:
    with open(path or CONFIG) as f:
        return json.load(f)


if __name__ == "__main__":  # python3 -m autoresearch.research.models_config [path]
    import sys
    cfg = load_models_config(sys.argv[1] if len(sys.argv) > 1 else None)
    for role, spec in cfg.get("roles", {}).items():
        print(f"{role:16s} " + ", ".join(f"{s} [{model_family(s)}]" for s in _list(spec)))
    problems = config_warnings(cfg)
    print("\n".join("warning: " + p for p in problems) or "no problems")
    print("dev flags:   " + " ".join(research_args(cfg)))
    for t in _list(cfg["roles"].get("heldout_targets")):
        print("final flags: " + " ".join(research_args(cfg, "final", t)))
    sys.exit(1 if problems else 0)
