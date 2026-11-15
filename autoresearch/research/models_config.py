"""configs/models.json and model-family checks (WS C2, PLAN 4.4 / 12.3 item 4).

The config names every model role once, so all workstreams use the same ones:

  roles:  dev_target, heldout_target, dev_judge (J1), heldout_judges (J2, two,
          from families other than the generator), generator, screening_target.
          Each is an autoresearch "backend:model" spec (see llm.get_llm).
  petri:  per mode ("dev" | "final"), Inspect model ids for the Petri harness:
          target, auditor, judge.

Who wrote a transcript explains ~11% of judge variance (EvalDetectBench), so a
held-out judge from the generator's family biases the held-out score. The
existing Measurer check compares backends only; `family_warnings` compares
model families, so e.g. an Anthropic generator and a claude-cli judge are caught.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

CONFIG = Path(__file__).resolve().parents[2] / "configs" / "models.json"

# Ordered: the first pattern that matches the model id names the family.
FAMILIES = [
    ("anthropic", r"claude|anthropic|\bhaiku\b|\bsonnet\b|\bopus\b|\bfable\b"),
    ("openai", r"\bgpt|openai|\bo[1-9](-|$)|codex"),
    ("google", r"gemini|gemma|google"),
    ("qwen", r"qwen"),
    ("moonshot", r"kimi|moonshot"),
    ("deepseek", r"deepseek"),
    ("meta", r"llama|meta-"),
    ("mistral", r"mistral|mixtral|magistral"),
    ("xai", r"grok|x-ai|xai"),
]
ROLES = ("generator", "dev_target", "heldout_target", "dev_judge", "heldout_judges", "screening_target")


def model_family(spec: str) -> str:
    """Family of a model spec ("anthropic:claude-x", "openai-compat:Qwen/Qwen3-8B",
    an Inspect id "openai-api/modal/Qwen/...", or a bare name); "unknown" if no
    pattern matches. Backends that only serve one vendor count as that vendor."""
    s = (spec or "").lower()
    if s.startswith(("anthropic:", "anthropic-batch:", "claude-cli:")):
        return "anthropic"
    model = s.split(":", 1)[1] if ":" in s.split("/", 1)[0] else s
    if model.startswith("openai-api/") and model.count("/") >= 2:   # Inspect id: openai-api/<server>/<model>
        model = model.split("/", 2)[2]
    elif model.startswith(("openai/", "anthropic/", "google/", "together/", "vllm/")):
        model = model.split("/", 1)[1] if not model.startswith(("openai/", "anthropic/")) else model
    for fam, pat in FAMILIES:
        if re.search(pat, model):
            return fam
    if s.startswith("openai:"):
        return "openai"
    return "unknown"


def _label_family(llm) -> str:
    if getattr(llm, "name", "") == "offline":
        return "offline"
    return model_family(getattr(llm, "label", "") or "")


def family_warnings(models) -> List[str]:
    """Warnings for a `Models` bundle: held-out judges or the held-out target from
    the generator's family, or two held-out judges from one family."""
    gen = _label_family(models.generator)
    out: List[str] = []
    if gen in ("offline", "unknown"):
        return out
    judges = list(getattr(models, "heldout_judges", []) or [])
    fams = [_label_family(j) for j in judges]
    for j, f in zip(judges, fams):
        if f == gen:
            out.append(f"held-out judge {j.label} is from the generator's family ({gen}); pick another family "
                       "(generator identity biases judges, EvalDetectBench)")
    known = [f for f in fams if f not in ("offline", "unknown")]
    if len(known) != len(set(known)):
        out.append(f"held-out judges share a family ({', '.join(known)}); PLAN 4.4 asks for two different families")
    ht = getattr(models, "heldout_target", None)
    if ht is not None and _label_family(ht) == gen:
        out.append(f"held-out target {ht.label} is from the generator's family ({gen})")
    return out


def config_warnings(cfg: Dict) -> List[str]:
    """The same checks on a configs/models.json dict, plus missing roles."""
    roles = cfg.get("roles", {})
    out = [f"configs/models.json: role {r!r} missing" for r in ROLES if not roles.get(r)]
    gen = model_family(roles.get("generator", ""))
    judges = roles.get("heldout_judges") or []
    fams = [model_family(j) for j in judges]
    if len(judges) < 2:
        out.append("configs/models.json: PLAN 4.4 asks for two held-out judges")
    for j, f in zip(judges, fams):
        if f == gen and gen != "unknown":
            out.append(f"held-out judge {j} is from the generator's family ({gen})")
    if len(set(fams)) != len(fams):
        out.append(f"held-out judges share a family ({', '.join(fams)})")
    for mode in ("dev", "final"):
        p = cfg.get("petri", {}).get(mode, {})
        for r in ("target", "auditor", "judge"):
            if not p.get(r):
                out.append(f"configs/models.json: petri.{mode}.{r} missing")
        if p.get("judge") and p.get("target") and model_family(p["judge"]) == model_family(p["target"]):
            out.append(f"petri.{mode}: the Petri judge is from the target's family ({model_family(p['target'])})")
    return out


def load_models_config(path: Optional[str] = None) -> Dict:
    with open(path or CONFIG) as f:
        return json.load(f)


if __name__ == "__main__":  # python3 -m autoresearch.research.models_config [path]
    import sys
    cfg = load_models_config(sys.argv[1] if len(sys.argv) > 1 else None)
    problems = config_warnings(cfg)
    for r, spec in cfg.get("roles", {}).items():
        specs = spec if isinstance(spec, list) else [spec]
        print(f"{r:17s} " + ", ".join(f"{s} [{model_family(s)}]" for s in specs))
    print("\n".join("warning: " + p for p in problems) or "no problems")
    sys.exit(1 if problems else 0)
