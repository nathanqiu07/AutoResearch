"""Shared paths, pre-T selection and the `claude -p` wrapper for profiles_contrastive.

Every real CLI call goes through `call`: cached in cache/ by sha256(model, system, prompt, occurrence),
logged to calls.log, and refused once its model's cap is reached (sonnet 70, haiku 300). The n-th
identical prompt in one process gets its own cache slot, so repeated gate votes are separate samples
on the first run and free cache hits on a rerun."""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

SLUG, T = "owain_evans", "2026-01-01"
DATA = os.path.join(ROOT, "data", "researchers", SLUG)
CORPUS = os.path.join(DATA, "corpus")
CAPS = {"sonnet": 70, "haiku": 300}
# Hobbhahn is a tester: his co-authored docs never enter profile material (BRIEF.md).
BANNED_AUTHOR = "hobbhahn"
# Pre-T docs left out of the map step: two history-of-ideas essays and BIG-bench (a 450-author
# benchmark where he is a middle author; nothing in it is his choice).
SKIP_DOCS = {
    "research__lives_of_the_cambridge_polymath_geniuses_3cfa4144.txt",
    "research__the_rationalists_of_the_1950s_and_before_also_call_b7148df3.txt",
    "research__beyond_the_imitation_game_quantifying_and_extrapol_11125731.txt",
}

_LOCK = threading.Lock()
_SEEN = collections.Counter()


def p(*parts):
    return os.path.join(HERE, *parts)


def read_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def header(path):
    """The YAML-ish front matter of a corpus file as a dict of raw strings."""
    meta = {}
    with open(path, errors="ignore") as f:
        if f.readline().strip() != "---":
            return meta
        for line in f:
            if line.strip() == "---":
                break
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def corpus_docs():
    """Every corpus doc: file, title, date, authors, position, kind, pre_t, hobbhahn."""
    out = []
    for name in sorted(os.listdir(CORPUS)):
        m = header(os.path.join(CORPUS, name))
        date = m.get("publishedDate", "")
        out.append(dict(file=name, title=m.get("title", ""), date=date, kind=m.get("kind", ""),
                        position=m.get("author_position", ""), authors=m.get("authors", ""),
                        pre_t=bool(re.match(r"\d{4}-\d{2}-\d{2}$", date)) and date < T,
                        hobbhahn=BANNED_AUTHOR in m.get("authors", "").lower()))
    return out


def pre_t_docs():
    """Docs whose evidence may enter a profile: dated before T, no Hobbhahn authorship."""
    return [d for d in corpus_docs() if d["pre_t"] and not d["hobbhahn"]]


def doc_text(name):
    with open(os.path.join(CORPUS, name), errors="ignore") as f:
        return f.read()


def calls_by_model():
    c = collections.Counter()
    if os.path.exists(p("calls.log")):
        for r in read_jsonl(p("calls.log")):
            if r.get("status") == "started":
                c[r["model"]] += 1
    return c


def call(model, prompt, system="You are a careful research analyst.", tag=""):
    base = hashlib.sha256(json.dumps([model, system, prompt]).encode()).hexdigest()
    with _LOCK:
        occ = _SEEN[base]
        _SEEN[base] += 1
    key = f"{base[:32]}_{occ}"
    cpath = p("cache", key + ".json")
    if os.path.exists(cpath):
        with open(cpath) as f:
            return json.load(f)["result"]
    with _LOCK:
        n = calls_by_model()[model]
        if n >= CAPS[model]:
            raise RuntimeError(f"{model} cap {CAPS[model]} reached")
        with open(p("calls.log"), "a") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "n": n + 1, "tag": tag,
                                "key": key, "chars": len(prompt), "status": "started"}) + "\n")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "", "--strict-mcp-config",
           "--no-session-persistence", "--setting-sources", "", "--system-prompt", system]
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="pc_cli_") as cwd:
        proc = subprocess.run(cmd, check=False, input=prompt, capture_output=True, text=True, timeout=900, cwd=cwd)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "result": (proc.stderr or proc.stdout)[:300]}
    ok = proc.returncode == 0 and not data.get("is_error")
    with _LOCK, open(p("calls.log"), "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": model, "tag": tag, "key": key,
                            "status": "ok" if ok else "error", "secs": round(time.time() - t0, 1),
                            "cost_usd": data.get("total_cost_usd"), "out": str(data.get("result"))[:120]}) + "\n")
    if not ok:
        raise RuntimeError(f"claude CLI error ({tag}): {str(data.get('result'))[:300]}")
    with open(cpath, "w") as f:
        json.dump({"model": model, "tag": tag, "system": system, "prompt": prompt, "result": data["result"]}, f,
                  ensure_ascii=False)
    return data["result"]


def json_obj(text):
    """The first {...} object in a model reply (code fences and prose around it ignored)."""
    return json.loads(text[text.find("{"):text.rfind("}") + 1])
