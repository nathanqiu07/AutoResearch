"""Shared plumbing for the attribution test (PROTOCOL.md): paths, jsonl, and the one `claude -p` wrapper.

Every real call is cached on disk by (model, tag, system, prompt), logged in calls.log, and refused once
calls.log holds the cap for its (model, budget) line. Writes only inside this directory."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TP = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(TP, "..", ".."))
sys.path.insert(0, ROOT)

# (model, budget line) -> cap; a budget line groups tags (abstraction vs prediction)
CAPS = {("sonnet", "abstract"): 50, ("sonnet", "predict"): 1100, ("haiku", "predict"): 400}
WORKERS = 4
LOCK = threading.Lock()


def p(*parts):
    out = os.path.join(HERE, *parts)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    with open(path, "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def started(model, line):
    return sum(1 for r in read_jsonl(p("calls.log"))
               if r.get("status") == "started" and r["model"] == model and r["line"] == line)


def call(model, line, tag, prompt, system):
    """claude -p, isolated (no tools, no MCP, no settings, no session)."""
    key = hashlib.sha256(json.dumps([model, tag, system, prompt]).encode()).hexdigest()[:32]
    cpath = p("cache", key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    with LOCK:
        n = started(model, line)
        if n >= CAPS[(model, line)]:
            raise RuntimeError(f"{model}/{line} cap {CAPS[(model, line)]} reached")
        with open(p("calls.log"), "a") as f:  # the slot is reserved before the call
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "n": n + 1, "model": model, "line": line,
                                "tag": tag, "key": key, "chars": len(prompt), "status": "started"}) + "\n")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "", "--strict-mcp-config",
           "--no-session-persistence", "--setting-sources", "", "--system-prompt", system]
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="attrib_cli_") as cwd:
        proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=900, cwd=cwd)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
    ok = proc.returncode == 0 and not data.get("is_error")
    with LOCK, open(p("calls.log"), "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "line": line, "tag": tag,
                            "key": key, "status": "ok" if ok else "error", "secs": round(time.time() - t0, 1),
                            "cost_usd": data.get("total_cost_usd"), "out": str(data.get("result"))[:100]}) + "\n")
    if not ok:
        raise RuntimeError(f"claude CLI error: {str(data.get('result'))[:300]}")
    with open(cpath, "w") as f:
        json.dump({"model": model, "tag": tag, "system": system, "prompt": prompt, "result": data["result"]}, f,
                  ensure_ascii=False)
    return data["result"]
