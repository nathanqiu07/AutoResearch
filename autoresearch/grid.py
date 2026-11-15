"""Research grid: arms x seeds (x settings) of `autoresearch research`, from a
pre-registration (PLAN 12.5 item 4; experiments E4 and E5).

A pre-registration `results/prereg/<exp>.json` names the arms (each a set of
`research` options, e.g. {"taste_mode": "model", "taste_track": "P"} or
{"allocation": "market"}), the seeds, and the settings every arm shares. This
module turns it into cells, one `research` run each, and runs a cell in its own
Python process, so cells never share state. The same `run_cell` runs locally
(`python3 -m autoresearch.grid`) and on Modal (`modal_app.py --mode
research-grid`); a cell returns its output files, which the caller writes to
`<out>/<cell>/` together with `CODE_VERSION`.

Option names are checked against the `research` parser: a key that is neither a
CLI option nor a documented non-option key is an error, so a typo in a
pre-registration cannot be silently ignored.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

# keys in a pre-registration's settings that are documentation, not CLI options
DOC_KEYS = {"comment", "memory", "models", "note", "external"}
# loop thresholds without CLI flags: the pre-registered value must be the loop's own
CONFIG_ONLY = ("accept_p", "confirm_p", "min_validity")
# options a cell sets itself (paths inside the cell)
CELL_OWNED = {"memory", "decisions_dir", "out", "seed", "arm"}
PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _research_options() -> Dict[str, argparse.Action]:
    from .cli import build_parser
    p = build_parser()
    sub = next(a for a in p._actions if isinstance(a, argparse._SubParsersAction))
    return {a.dest: a for a in sub.choices["research"]._actions if a.option_strings}


def option_args(spec: Dict, where: str) -> List[str]:
    """CLI arguments for a dict of `research` options (keys as in ResearchConfig /
    argparse dests). Booleans: web=false -> --no-web, shared_memory=false ->
    --no-shared, other true values -> the flag itself."""
    from .research.loop import ResearchConfig
    opts = _research_options()
    out: List[str] = []
    for k, v in spec.items():
        if k in DOC_KEYS:
            continue
        if k in CELL_OWNED:
            raise ValueError(f"{where}: '{k}' is set per cell by the grid, not in a pre-registration")
        if k in CONFIG_ONLY:
            if v != getattr(ResearchConfig(), k):
                raise ValueError(f"{where}: {k}={v} differs from the loop's {getattr(ResearchConfig(), k)}; "
                                 "no CLI option sets it")
            continue
        if k in ("web", "shared_memory"):
            if not v:
                out.append("--no-web" if k == "web" else "--no-shared")
            continue
        if k not in opts:
            raise ValueError(f"{where}: '{k}' is not a `research` option")
        flag = opts[k].option_strings[-1]
        if isinstance(v, bool):
            if v != bool(opts[k].default):
                out.append(flag)
        elif isinstance(v, list):
            out += [flag, *map(str, v)]
        elif v is not None:
            out += [flag, str(v)]
    return out


def runnable_arms(prereg: Dict) -> Dict[str, Dict]:
    """Arms this CLI can run (an arm with only a 'note' is documented, e.g. the external agent)."""
    return {a: v for a, v in prereg["arms"].items() if set(v) - DOC_KEYS}


def grid_cells(prereg: Dict, arms: Optional[List[str]] = None, seeds: Optional[List[int]] = None,
               llm: str = "anthropic", extra: Optional[List[str]] = None) -> List[Dict]:
    """One cell per arm x seed (x setting when the pre-registration lists
    `settings`: named option sets crossed with every arm)."""
    run = runnable_arms(prereg)
    arms = arms or list(run)
    bad = [a for a in arms if a not in run]
    if bad:
        raise ValueError(f"arms not runnable or unknown: {bad} (runnable: {sorted(run)})")
    shared = option_args(prereg.get("shared_run_settings", {}), "shared_run_settings")
    settings = prereg.get("settings") or {"": {}}
    cells = []
    for arm in arms:
        a_args = option_args(run[arm], f"arm {arm}")
        for sname, sopts in settings.items():
            s_args = option_args(sopts, f"setting {sname}")
            for seed in seeds if seeds is not None else prereg["seeds"]:
                cid = f"{arm}/{sname}/seed{seed}" if sname else f"{arm}/seed{seed}"
                cells.append({"cell": cid, "experiment": prereg.get("experiment", ""), "arm": arm,
                              "setting": sname, "seed": seed,
                              "argv": ["--llm", llm, "research", "--arm", arm, "--seed", str(seed),
                                       *shared, *a_args, *s_args, *(extra or [])]})
    return cells


def run_cell(cell: Dict, root: Optional[str] = None, timeout: float = 6 * 3600) -> Dict:
    """Run one cell in a fresh Python process from `root` (where data/ lives);
    returns its status, stdout tail, code version and every output file as text."""
    from .research.decisions import code_version
    root = root or PKG_ROOT
    tmp = tempfile.mkdtemp(prefix="ar_cell_")
    argv = [*cell["argv"], "--memory", os.path.join(tmp, "memory"), "--decisions-dir", os.path.join(tmp, "decisions"),
            "--out", os.path.join(tmp, "out")]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [PKG_ROOT, os.environ.get("PYTHONPATH")]))}
    t0 = time.time()
    try:
        proc = subprocess.run([sys.executable, "-m", "autoresearch", *argv], cwd=root, env=env,
                              capture_output=True, text=True, timeout=timeout)
        ok, err, stdout = proc.returncode == 0, (proc.stderr or "")[-2000:] if proc.returncode else None, proc.stdout
    except subprocess.TimeoutExpired as e:
        ok, err, stdout = False, f"timeout after {timeout:.0f}s", (e.stdout or "") if isinstance(e.stdout, str) else ""
    files = {}
    for d, _, fs in os.walk(tmp):
        for f in fs:
            p = os.path.join(d, f)
            if os.path.getsize(p) <= 20_000_000:
                with open(p, errors="replace") as fh:
                    files[os.path.relpath(p, tmp)] = fh.read()
    shutil.rmtree(tmp, ignore_errors=True)
    return {"cell": cell["cell"], "ok": ok, "error": err, "argv": argv, "code_version": code_version(),
            "seconds": round(time.time() - t0, 1), "stdout": stdout[-4000:], "files": files}


def write_cell(result: Dict, out_root: str) -> str:
    """Write a cell's files under <out_root>/<cell>/ with CODE_VERSION and cell.json."""
    d = os.path.join(out_root, result["cell"])
    os.makedirs(d, exist_ok=True)
    for rel, text in result["files"].items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    with open(os.path.join(d, "CODE_VERSION"), "w") as f:
        f.write(result["code_version"] + "\n")
    with open(os.path.join(d, "cell.json"), "w") as f:
        json.dump({k: v for k, v in result.items() if k != "files"}, f, indent=1)
    return d


def run_local(cells: List[Dict], out_root: str, workers: int = 4) -> List[Dict]:
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        results = list(ex.map(run_cell, cells))
    for r in results:
        write_cell(r, out_root)
    return results


def load_prereg(path: str) -> Dict:
    with open(path) as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="run a pre-registered research grid locally (Modal: modal_app.py)")
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--arms", nargs="*")
    ap.add_argument("--seeds", nargs="*", type=int)
    ap.add_argument("--llm", default="offline")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm the user approved a paid grid")
    args, extra = ap.parse_known_args(argv)
    cells = grid_cells(load_prereg(args.prereg), args.arms, args.seeds, args.llm, [x for x in extra if x != "--"])
    for c in cells:
        print(c["cell"], shlex.join(c["argv"]))
    if args.dry_run:
        return 0
    if args.llm != "offline" and not args.yes:
        raise SystemExit("a paid grid needs --yes once the user has approved it (AGENTS.md rule 5)")
    res = run_local(cells, args.out, args.workers)
    bad = [r for r in res if not r["ok"]]
    for r in bad:
        print("FAILED", r["cell"], r["error"])
    print(f"{len(res) - len(bad)}/{len(res)} cells finished -> {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
