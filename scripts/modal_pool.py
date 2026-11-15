#!/usr/bin/env python3
"""Pool several Modal workspaces for the C2 GPU steps, each with its own dollar budget (WS C2).

Modal bills per workspace and one step's auditor (4xH100) cannot be split across workspaces, so
pooling is per step: `pick` chooses the first workspace in the pool file whose budget fits the
step's worst case (GPUs x wall-clock limit x H100 price) and holds that amount; `close` replaces
the hold with the actual (GPUs x elapsed minutes). A step that crashes before `close` keeps its
worst case on the ledger, which errs toward spending less. Workspaces are used in the listed order
and a workspace is reused until it is full, because each new workspace re-downloads model weights
on its first deploy (billed GPU time).

Pool file (default ~/.autoresearch/pool.json; it names env vars and Modal profiles, never secrets):
    {"tinker": [{"label": "nathan", "key_env": "TINKER_API_KEY", "budget_usd": 100}, ...],
     "modal":  [{"label": "nathan", "profile": "nqiu07", "budget_usd": 60}, ...]}
A Modal profile is added once per teammate with
    modal token set --token-id <id> --token-secret <secret> --profile <name>

    python3 scripts/modal_pool.py pick --run-id ID --gpus 4 --minutes 150   # prints shell exports
    python3 scripts/modal_pool.py close --run-id ID --label nathan --gpus 4 --minutes 37
    python3 scripts/modal_pool.py status                                    # Modal and Tinker ledgers
Without a pool file, one workspace is used: the active Modal profile, budget --budget-usd
(or MODAL_BUDGET_USD).
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

H100_USD_PER_HOUR = float(os.environ.get("H100_USD_PER_HOUR", "3.95"))   # Modal list price; check modal.com/pricing
LEDGER_DIR = Path(os.environ.get("AUTORESEARCH_LEDGER_DIR", "~/.autoresearch")).expanduser()
DEFAULT_POOL = Path(os.environ.get("POOL_FILE", "~/.autoresearch/pool.json")).expanduser()
MODAL_TOML = Path(os.environ.get("MODAL_CONFIG_PATH", "~/.modal.toml")).expanduser()


def gpu_cost(gpus: int, minutes: float, usd_per_hour: float = H100_USD_PER_HOUR) -> float:
    return gpus * minutes / 60.0 * usd_per_hour


def modal_profiles(path: Path = MODAL_TOML) -> Dict[str, bool]:
    """{profile name: is active} from ~/.modal.toml (section headers and `active = true`)."""
    if not path.exists():
        return {}
    profiles, current = {}, None
    for line in path.read_text().splitlines():
        m = re.match(r"\s*\[([^\]]+)\]\s*$", line)
        if m:
            current = m.group(1).strip().strip('"')
            profiles[current] = False
        elif current and re.match(r"\s*active\s*=\s*true\s*$", line):
            profiles[current] = True
    return profiles


def accounts(pool_file: Path, budget_usd: Optional[float]) -> List[dict]:
    known = modal_profiles()
    if pool_file.exists():
        entries = json.loads(pool_file.read_text()).get("modal") or []
    else:
        if budget_usd is None:
            raise SystemExit("no pool file and no --budget-usd / MODAL_BUDGET_USD: refusing to deploy without a limit")
        active = os.environ.get("MODAL_PROFILE") or next((p for p, on in known.items() if on), None) \
            or (next(iter(known)) if len(known) == 1 else None)
        if not active:
            raise SystemExit("cannot tell which Modal profile is active; set MODAL_PROFILE")
        entries = [{"label": "default", "profile": active, "budget_usd": budget_usd}]
    if not entries:
        raise SystemExit(f"{pool_file} has no \"modal\" accounts")
    labels = [e["label"] for e in entries]
    if len(set(labels)) != len(labels):
        raise SystemExit(f"duplicate Modal pool labels: {labels}")
    for e in entries:
        if e["profile"] not in known:
            raise SystemExit(f"Modal account {e['label']!r}: profile {e['profile']!r} is not in {MODAL_TOML} "
                             f"(add it: modal token set --token-id ... --token-secret ... --profile {e['profile']})")
    return entries


class Ledger:
    def __init__(self, label: str, root: Path = LEDGER_DIR):
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / f"modal_ledger_{label}.json"

    def __enter__(self):
        self._lock = open(str(self.path) + ".lock", "w")
        fcntl.flock(self._lock, fcntl.LOCK_EX)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {"spent_usd": 0.0, "open": {}, "runs": []}
        return self

    def save(self):
        self.data["note"] = "estimate: GPUs x deployed minutes x list price; the Modal dashboard is the bill"
        tmp = str(self.path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=1)
        os.replace(tmp, self.path)

    def __exit__(self, *exc):
        fcntl.flock(self._lock, fcntl.LOCK_UN)
        self._lock.close()

    def committed(self) -> float:
        return float(self.data.get("spent_usd", 0.0)) + sum(float(v["worst_usd"]) for v in self.data["open"].values())


def pick(entries: List[dict], run_id: str, gpus: int, minutes: float, root: Path = LEDGER_DIR) -> dict:
    worst = gpu_cost(gpus, minutes)
    reasons = []
    for e in entries:
        with Ledger(e["label"], root) as led:
            room = float(e["budget_usd"]) - led.committed()
            if worst <= room + 1e-9:
                led.data["open"][run_id] = {"worst_usd": round(worst, 4), "gpus": gpus, "minutes_limit": minutes,
                                            "opened": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
                led.save()
                return {"label": e["label"], "profile": e["profile"], "worst_usd": worst, "room_usd": room}
            reasons.append(f"[{e['label']}] ${room:.2f} left < ${worst:.2f} worst case")
    raise SystemExit(f"no Modal workspace has room for {gpus} GPU(s) x {minutes:g} min (${worst:.2f}): " + "; ".join(reasons))


def close(label: str, run_id: str, gpus: int, minutes: float, root: Path = LEDGER_DIR) -> float:
    actual = gpu_cost(gpus, minutes)
    with Ledger(label, root) as led:
        led.data["open"].pop(run_id, None)
        led.data["spent_usd"] = round(float(led.data.get("spent_usd", 0.0)) + actual, 4)
        led.data["runs"].append({"run_id": run_id, "gpus": gpus, "minutes": round(minutes, 2), "usd": round(actual, 4),
                                 "closed": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        led.save()
    return actual


def status(root: Path = LEDGER_DIR) -> str:
    lines = []
    for f in sorted(root.glob("*_ledger_*.json")):
        d = json.loads(f.read_text())
        held = sum(float(v["worst_usd"]) for v in d.get("open", {}).values())
        lines.append(f"{f.stem:32s} spent ${float(d.get('spent_usd', 0)):8.2f}" + (f"  held ${held:.2f}" if held else ""))
    return "\n".join(lines) or f"no ledgers in {root}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick")
    p.add_argument("--run-id", required=True)
    p.add_argument("--gpus", type=int, required=True)
    p.add_argument("--minutes", type=float, required=True)
    p.add_argument("--pool", default=str(DEFAULT_POOL))
    p.add_argument("--budget-usd", type=float, default=float(os.environ["MODAL_BUDGET_USD"]) if os.environ.get("MODAL_BUDGET_USD") else None)
    c = sub.add_parser("close")
    c.add_argument("--run-id", required=True)
    c.add_argument("--label", required=True)
    c.add_argument("--gpus", type=int, required=True)
    c.add_argument("--minutes", type=float, required=True)
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "pick":
        got = pick(accounts(Path(a.pool).expanduser(), a.budget_usd), a.run_id, a.gpus, a.minutes)
        print(f"modal workspace {got['label']} (profile {got['profile']}): holding ${got['worst_usd']:.2f} of "
              f"${got['room_usd']:.2f} left", file=sys.stderr)
        print(f"export MODAL_PROFILE={shlex.quote(got['profile'])} MODAL_POOL_LABEL={shlex.quote(got['label'])}")
    elif a.cmd == "close":
        usd = close(a.label, a.run_id, a.gpus, a.minutes)
        print(f"modal workspace {a.label}: {a.gpus} GPU(s) x {a.minutes:.1f} min = ${usd:.2f}", file=sys.stderr)
    else:
        print(status())
    return 0


if __name__ == "__main__":
    sys.exit(main())
