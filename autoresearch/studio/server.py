"""HTTP server for the studio: a JSON API over store/sources plus the static frontend.

Binds to 127.0.0.1 only. Slow work (gathering sources, building a profile, fitting a user
model) runs as a background job that the page polls; one job per profile at a time so two
jobs never write the same directory.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import threading
import time
import traceback
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, Optional

from ..llm import Budget, get_llm
from ..taste.profile import FEATURES
from ..taste.researcher import DEFAULT_ROOT
from . import sources, store
from .questionnaire import QUESTIONS

STATIC = os.path.join(os.path.dirname(__file__), "static")
MAX_BODY = 60 * 1024 * 1024
BACKENDS = ("offline", "anthropic", "claude-cli")
METHODS = ("m0", "m1", "m2", "m3", "m4", "m5", "m6", "m7")


class Jobs:
    def __init__(self):
        self._jobs: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def start(self, kind: str, slug: str, fn: Callable[[Callable[[str], None]], object]) -> dict:
        with self._lock:
            busy = [j for j in self._jobs.values() if j["slug"] == slug and j["status"] == "running"]
            if busy:
                raise store.StudioError(f"a {busy[0]['kind']} job is already running for {slug}")
            job = {"id": uuid.uuid4().hex[:12], "kind": kind, "slug": slug, "status": "running",
                   "log": [], "result": None, "error": None, "started": time.time(), "finished": None}
            self._jobs[job["id"]] = job

        def log(msg: str):
            job["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")

        def run():
            try:
                job["result"] = fn(log)
                job["status"] = "done"
            except Exception as e:
                job["error"] = str(e) if isinstance(e, store.StudioError) else f"{type(e).__name__}: {e}"
                log("error: " + job["error"])
                if not isinstance(e, store.StudioError):
                    traceback.print_exc()
                job["status"] = "error"
            job["finished"] = time.time()
        threading.Thread(target=run, daemon=True).start()
        return job

    def get(self, job_id: str) -> dict:
        return self._jobs[job_id]


def _llm(body: dict, default_model: str, max_calls: int):
    backend = body.get("backend") or "offline"
    if backend not in BACKENDS:
        raise store.StudioError(f"backend must be one of {BACKENDS}")
    return get_llm(backend, body.get("model") or default_model, Budget(max_calls=max_calls))


def make_app(root: str):
    jobs = Jobs()
    root = os.path.abspath(root)
    os.makedirs(root, exist_ok=True)

    def config(_q, _b):
        return {"root": root, "features": FEATURES, "questions": QUESTIONS, "backends": BACKENDS,
                "methods": METHODS, "exa_available": sources.exa_available(),
                "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}

    def build_job(slug, body):
        store.require_editable(root, slug)
        max_docs = int(body.get("max_docs") or 40)
        llm = _llm(body, "claude-sonnet-5-5", max_calls=max_docs + 5)   # one per doc + merge + summary
        return jobs.start("build", slug, lambda log: store.build_profile(root, slug, llm, max_docs, log))

    def gather_job(slug, body):
        store.require_editable(root, slug)
        return jobs.start("gather", slug, lambda log: sources.gather(root, slug, body, log))

    def fit_job(slug, body):
        meta = store.require_editable(root, slug)
        if meta["mode"] != "personal":
            raise store.StudioError("a user model is fitted on the person's own trade-off answers (personal mode)")
        method = body.get("method") or "m1"
        if method not in METHODS:
            raise store.StudioError(f"method must be one of {METHODS}")
        max_calls = int(body.get("max_calls") or 500)
        llm = _llm(body, "claude-haiku-5-5", max_calls)

        def run(log):
            from ..taste import trackp
            from ..taste.methods import create_method
            log(f"fitting {method} with {llm.label} on the recorded trade-off answers")
            path = trackp.fit_user_model(root, slug, lambda: create_method(
                method, llm, seed=0, cache_dir=os.path.join("runs", "taste-cache"), max_calls=max_calls))
            log(f"wrote {os.path.relpath(path, root)} ({llm.budget.calls} model calls)")
            return {"path": path, "calls": llm.budget.calls}
        return jobs.start("fit", slug, run)

    def doc_post(slug, body):
        name, created = store.add_doc(root, slug, body.get("kind", "research"), body.get("title", ""),
                                      body.get("text", ""), source=body.get("source") or "upload",
                                      url=body.get("url", ""), date=body.get("date", ""),
                                      extra={"filename": body.get("filename", "")})
        return {"file": name, "created": created}

    def patch(slug, body):
        allowed = {"name", "affiliation", "homepage", "bio", "bio_source", "s2_author"}
        bad = sorted(set(body) - allowed)
        if bad:
            raise store.StudioError(f"cannot set {bad}")
        return store.update_meta(root, slug, **body)

    routes = [
        ("GET", r"/api/config", lambda m, q, b: config(q, b)),
        ("GET", r"/api/profiles", lambda m, q, b: store.list_profiles(root)),
        ("POST", r"/api/profiles", lambda m, q, b: store.create_profile(root, b.get("name"), b.get("mode"),
                                                                        b.get("slug") or None)),
        ("GET", r"/api/profiles/(\w+)", lambda m, q, b: store.profile_state(root, m[0])),
        ("PATCH", r"/api/profiles/(\w+)", lambda m, q, b: patch(m[0], b)),
        ("POST", r"/api/profiles/(\w+)/consent", lambda m, q, b: store.write_consent(root, m[0], b.get("ticked", []))),
        ("POST", r"/api/profiles/(\w+)/answers", lambda m, q, b: store.save_answers(root, m[0], b.get("answers", {}))),
        ("POST", r"/api/profiles/(\w+)/docs", lambda m, q, b: doc_post(m[0], b)),
        ("GET", r"/api/profiles/(\w+)/docs/([\w.]+)", lambda m, q, b: store.read_doc(root, m[0], m[1])),
        ("DELETE", r"/api/profiles/(\w+)/docs/([\w.]+)",
         lambda m, q, b: (store.delete_doc(root, m[0], m[1]), {"deleted": m[1]})[1]),
        ("POST", r"/api/profiles/(\w+)/gather", lambda m, q, b: gather_job(m[0], b)),
        ("POST", r"/api/profiles/(\w+)/build", lambda m, q, b: build_job(m[0], b)),
        ("PUT", r"/api/profiles/(\w+)/profile",
         lambda m, q, b: store.save_edited_profile(root, m[0], b.get("principles", []), b.get("weights", {}))),
        ("POST", r"/api/profiles/(\w+)/choices/generate",
         lambda m, q, b: {"pairs": store.ensure_seed_pairs(root, m[0])}),
        ("GET", r"/api/profiles/(\w+)/choices/pending",
         lambda m, q, b: store.pending_choices(root, m[0], int(q.get("limit", ["0"])[0]))),
        ("POST", r"/api/profiles/(\w+)/choices/record",
         lambda m, q, b: (store.record_choice(root, m[0], b.get("id", ""), int(b.get("choice") or 0),
                                              b.get("reason", "")), {"recorded": b.get("id")})[1]),
        ("POST", r"/api/profiles/(\w+)/fit", lambda m, q, b: fit_job(m[0], b)),
        ("GET", r"/api/search/s2", lambda m, q, b: sources.s2_search(q.get("name", [""])[0])),
        ("GET", r"/api/search/s2/(\d+)/titles", lambda m, q, b: sources.s2_author_sample_titles(m[0])),
        ("GET", r"/api/search/wikipedia", lambda m, q, b: sources.wikipedia_summary(q.get("name", [""])[0])),
        ("GET", r"/api/jobs/(\w+)", lambda m, q, b: jobs.get(m[0])),
    ]
    compiled = [(meth, re.compile("^" + pat + "$"), fn) for meth, pat, fn in routes]

    def dispatch(method: str, path: str, query: dict, body: dict):
        for meth, rx, fn in compiled:
            m = rx.match(path)
            if m and meth == method:
                return 200, fn(m.groups(), query, body)
        return 404, {"error": f"no route {method} {path}"}

    return dispatch


class Handler(BaseHTTPRequestHandler):
    dispatch = None  # set by serve()

    def log_message(self, fmt, *args):  # quieter than the default per-request line
        if not self.path.startswith("/api/jobs/"):
            super().log_message(fmt, *args)

    def _send(self, code: int, payload, ctype="application/json"):
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str):
        rel = "index.html" if path in ("/", "") else path[len("/static/"):] if path.startswith("/static/") else None
        full = os.path.realpath(os.path.join(STATIC, rel)) if rel else None
        if not full or not full.startswith(os.path.realpath(STATIC) + os.sep) or not os.path.isfile(full):
            return self._send(404, {"error": "not found"})
        with open(full, "rb") as f:
            self._send(200, f.read(), mimetypes.guess_type(full)[0] or "application/octet-stream")

    def _handle(self, method: str):
        url = urllib.parse.urlparse(self.path)
        if not url.path.startswith("/api/"):
            return self._static(url.path) if method == "GET" else self._send(405, {"error": "method not allowed"})
        n = int(self.headers.get("content-length") or 0)
        if n > MAX_BODY:
            return self._send(413, {"error": "request too large"})
        try:
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            code, out = type(self).dispatch(method, url.path, urllib.parse.parse_qs(url.query), body)
        except store.StudioError as e:
            code, out = 400, {"error": str(e)}
        except KeyError as e:
            code, out = 404, {"error": f"not found: {e.args[0] if e.args else ''}"}
        except (RuntimeError, ValueError) as e:
            code, out = 502 if isinstance(e, RuntimeError) else 400, {"error": str(e)}
        except Exception as e:
            traceback.print_exc()
            code, out = 500, {"error": f"{type(e).__name__}: {e}"}
        self._send(code, out)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")


def serve(root: str = DEFAULT_ROOT, port: int = 8765, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    handler = type("StudioHandler", (Handler,), {"dispatch": staticmethod(make_app(root))})
    return ThreadingHTTPServer((host, port), handler)


def main(argv=None):
    p = argparse.ArgumentParser(description="Profile Studio: build a researcher profile for the research loop")
    p.add_argument("--root", default=DEFAULT_ROOT, help="researchers directory (default data/researchers)")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    httpd = serve(args.root, args.port)
    print(f"Profile Studio on http://127.0.0.1:{args.port}  (profiles in {os.path.abspath(args.root)})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
