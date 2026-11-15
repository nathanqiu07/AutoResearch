"""Real public git repos as the Petri target's sandbox (idea real-repo-sandboxes, Exa + Modal).

A sandbox the auditor fills by hand tends to look invented: neat trees, placeholder
names, no history. Here Exa finds public GitHub repos on an environment's topic,
GitHub's public API checks each one (licence, archived, size, real history), and
the survivors become RepoSource dicts that `attach_repos` puts on AuditSeed rows.
The Petri harness (harness/petri/sandbox_tools.py) then clones the repo into the
sample's Modal Sandbox before the auditor starts and tells the auditor where it is.

RepoSource (the AuditSeed "repo" field; tools must be "sandbox"):
    {"url": "https://github.com/owner/name", "ref": commit or branch (optional),
     "depth": history depth to clone (optional, default 200; "full" for all of it),
     "licence": SPDX id or null, "source_url": the URL Exa returned, "published": YYYY-MM-DD or null,
     "path": destination dir (optional, default /home/user/<name>),
     "scrub": optional, default true: make the clone look like a working copy (no clone-source
              remote or reflog; HEAD on a branch), "remote_url": optional `origin` to set when scrubbing}
Instead of "url", a source may give "local_path", an absolute path to a git repo on the
harness host (`local_repo_source` builds one; its licence is read from a committed
LICENSE/COPYING file, else null). The harness bundles it and copies it into the sandbox.

`find_repos` pins `ref` to the default branch's head commit at search time, so every
arm and re-run clones the same tree. Every Exa result a repo came from is logged as a
source with used_for="repo_sandbox".

    python3 -m autoresearch.research.real_repos find --topic "kubernetes deploy scripts" --out repos.jsonl
    python3 -m autoresearch.research.real_repos local --path /abs/path/to/repo --out repos.jsonl
    python3 -m autoresearch.research.real_repos attach --seeds in.jsonl --repos repos.jsonl --out out.jsonl

`find` calls Exa (EXA_API_KEY, paid per search) and GitHub's public REST API
(unauthenticated: 60 requests an hour; a GITHUB_TOKEN env var, if set, is sent
for a higher limit and never printed). `local` and `attach` make no network calls.
Standard library only; the network is injectable (`exa`, `fetch`) so tests run offline.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlsplit

from ..integrations.exa import Source

API = "https://api.github.com"
USED_FOR = "repo_sandbox"
DEFAULT_DEPTH = 200
DEFAULT_MAX_SIZE_KB = 50_000          # GitHub's `size` is in KB; a sandbox clone should be quick
DEFAULT_MIN_COMMITS = 5
PERMISSIVE_LICENCES = frozenset({"MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD",
                                 "Unlicense", "Zlib", "BSL-1.0", "CC0-1.0", "PostgreSQL", "NCSA", "UPL-1.0"})
LICENCE_POLICIES = ("permissive", "known")
UNKNOWN_LICENCES = frozenset({None, "", "NOASSERTION", "OTHER"})
# First path segments of github.com URLs that are site pages, not owners.
RESERVED_OWNERS = frozenset({
    "about", "apps", "blog", "collections", "contact", "customer-stories", "enterprise", "events", "explore",
    "features", "login", "marketplace", "new", "notifications", "orgs", "organizations", "pricing", "readme",
    "search", "security", "settings", "site", "sponsors", "topics", "trending", "users", "join", "pulls",
    "issues", "codespaces", "copilot", "solutions", "resources", "team", "gist", "stars", "watching"})
NAME = re.compile(r"^[A-Za-z0-9._-]+$")
OWNER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")
QUERY_TEMPLATE = "{topic} github repository"

Fetch = Callable[[str], Any]   # GET a GitHub API URL -> parsed JSON, or None when it does not exist


# ---------- URLs ----------
def parse_github_repo(url: str) -> Optional[Tuple[str, str]]:
    """(owner, name) of the repo a github.com URL points into (a file, issue or tree page
    counts as its repo), or None for anything that is not a repo page."""
    try:
        parts = urlsplit(url.strip())
    except (AttributeError, ValueError):
        return None
    if parts.scheme not in ("http", "https") or (parts.hostname or "").lower() not in ("github.com", "www.github.com"):
        return None
    if parts.username or parts.password:
        return None
    segs = [x for x in parts.path.split("/") if x]
    if len(segs) < 2:
        return None
    owner, name = segs[0], segs[1]
    if name.endswith(".git"):
        name = name[:-4]
    if owner.lower() in RESERVED_OWNERS or not OWNER.match(owner) or not NAME.match(name) or name in (".", ".."):
        return None
    return owner, name


def repo_url(owner: str, name: str) -> str:
    return f"https://github.com/{owner}/{name}"


def day(timestamp: Optional[str]) -> Optional[str]:
    """YYYY-MM-DD from an ISO timestamp (Exa's publishedDate, GitHub's pushed_at)."""
    return timestamp[:10] if isinstance(timestamp, str) and re.match(r"^\d{4}-\d{2}-\d{2}", timestamp) else None


def validate_repo_source(src: Any) -> List[str]:
    """Problems with a RepoSource dict ([] if it is usable). The harness checks the details
    that matter for safe cloning again (harness/petri/sandbox_tools.repo_problems)."""
    if not isinstance(src, dict):
        return ["repo source must be an object"]
    problems = []
    url, local = src.get("url"), src.get("local_path")
    if (url is None) == (local is None):
        problems.append("needs exactly one of url or local_path")
    if url is not None and (not isinstance(url, str) or not url.startswith("https://")
                            or parse_github_repo(url) is None):
        problems.append("url must be https://github.com/owner/name")
    if local is not None and not (isinstance(local, str) and os.path.isabs(local)):
        problems.append("local_path must be an absolute path")
    depth = src.get("depth")
    if depth is not None and depth != "full" and (isinstance(depth, bool) or not isinstance(depth, int) or depth < 1):
        problems.append('depth must be a positive integer or "full"')
    if src.get("scrub") is not None and not isinstance(src["scrub"], bool):
        problems.append("scrub must be true or false")
    for k in ("ref", "licence", "source_url", "published", "path", "remote_url"):
        if src.get(k) is not None and not isinstance(src[k], str):
            problems.append(f"{k} must be a string or null")
    return problems


def parse_depth(text: str):
    """--depth: a positive integer or "full"."""
    if text == "full":
        return text
    n = int(text)
    if n < 1:
        raise argparse.ArgumentTypeError("depth must be a positive integer or full")
    return n


# ---------- local repos ----------
LICENCE_FILES = re.compile(r"^(LICEN[CS]E|COPYING|UNLICENSE)([.-][A-Za-z0-9.]+)?$", re.IGNORECASE)
# (SPDX id, phrases that must all appear), most specific first; matched on whitespace-collapsed text.
LICENCE_MARKERS = (
    ("AGPL-3.0", ("GNU AFFERO GENERAL PUBLIC LICENSE", "Version 3")),
    ("LGPL-3.0", ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 3")),
    ("LGPL-2.1", ("GNU LESSER GENERAL PUBLIC LICENSE", "Version 2.1")),
    ("GPL-3.0", ("GNU GENERAL PUBLIC LICENSE", "Version 3")),
    ("GPL-2.0", ("GNU GENERAL PUBLIC LICENSE", "Version 2")),
    ("MPL-2.0", ("Mozilla Public License", "2.0")),
    ("Apache-2.0", ("Apache License", "Version 2.0")),
    ("Unlicense", ("This is free and unencumbered software released into the public domain",)),
    ("MIT", ("Permission is hereby granted, free of charge", "WITHOUT WARRANTY OF ANY KIND")),
    ("BSD-3-Clause", ("Redistribution and use in source and binary forms", "Neither the name")),
    ("BSD-2-Clause", ("Redistribution and use in source and binary forms",)),
    ("ISC", ("Permission to use, copy, modify, and/or distribute this software for any purpose",)),
)


def detect_licence(text: str) -> str:
    """The SPDX id a licence file's text matches, or "NOASSERTION" if none is recognised."""
    flat = " ".join(text.split())
    for spdx, phrases in LICENCE_MARKERS:
        if all(p.lower() in flat.lower() for p in phrases):
            return spdx
    return "NOASSERTION"


def _git(path: str, *args: str) -> str:
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed in {path}: {p.stderr.strip()[:300]}")
    return p.stdout


def local_repo_source(path: str, *, depth=DEFAULT_DEPTH, ref: Optional[str] = None) -> dict:
    """A RepoSource for a git repo on this machine, pinned to `ref` (default: HEAD's commit).
    The licence comes from a LICENSE/COPYING file committed at the top of that commit: its
    SPDX id if recognised, "NOASSERTION" if not, null if there is none. No network."""
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise ValueError(f"{path} is not a directory")
    sha = _git(path, "rev-parse", "--verify", "--quiet", f"{ref or 'HEAD'}^{{commit}}").strip()
    licence = None
    for name in _git(path, "ls-tree", "--name-only", sha).splitlines():
        if LICENCE_FILES.match(name):
            licence = detect_licence(_git(path, "show", f"{sha}:{name}"))
            break
    return {"local_path": path, "ref": sha, "depth": depth, "licence": licence,
            "source_url": None, "published": None}


# ---------- Exa: candidates ----------
def find_candidates(topic: str, exa, num_results: int = 20, query_template: str = QUERY_TEMPLATE,
                    **search_kwargs) -> List[Dict[str, Any]]:
    """Repos Exa returns for a topic, searched on github.com only: one entry per repo (the
    first, best-ranked result that points into it), in Exa's order. `exa` is anything with
    ExaClient's `search(query, num_results=..., include_domains=...)`."""
    results = exa.search(query_template.format(topic=topic), num_results=num_results,
                         include_domains=["github.com"], **search_kwargs)
    out, seen = [], set()
    for r in results or []:
        parsed = parse_github_repo(r.get("url") or "")
        if parsed is None:
            continue
        key = (parsed[0].lower(), parsed[1].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append({"owner": parsed[0], "name": parsed[1], "source_url": r["url"],
                    "title": r.get("title") or "", "published": day(r.get("publishedDate"))})
    return out


# ---------- GitHub: metadata ----------
def github_fetch(url: str, timeout: int = 30) -> Any:
    """GET a GitHub REST API URL. None for a repo that doesn't exist, is gone or is empty
    (404, 409, 410, 451). GITHUB_TOKEN is sent if the environment has one."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "autoresearch-real-repos"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        if e.code in (404, 409, 410, 451):
            return None
        if e.code in (403, 429):
            raise RuntimeError(f"GitHub API refused {url} (HTTP {e.code}, probably the rate limit: "
                               f"60 requests an hour without GITHUB_TOKEN)") from None
        raise RuntimeError(f"GitHub API {url} -> HTTP {e.code}") from None


def repo_info(owner: str, name: str, fetch: Fetch = github_fetch) -> Optional[dict]:
    return fetch(f"{API}/repos/{quote(owner)}/{quote(name)}")


def recent_commits(owner: str, name: str, n: int, fetch: Fetch = github_fetch,
                   ref: Optional[str] = None) -> List[dict]:
    """Up to `n` newest commits on `ref` (default branch if None), newest first."""
    url = f"{API}/repos/{quote(owner)}/{quote(name)}/commits?per_page={max(1, min(n, 100))}"
    if ref:
        url += f"&sha={quote(ref, safe='')}"
    got = fetch(url)
    return got if isinstance(got, list) else []


def licence_of(info: dict) -> Optional[str]:
    spdx = (info.get("license") or {}).get("spdx_id")
    return None if spdx in UNKNOWN_LICENCES else spdx


def unfit_reasons(info: Optional[dict], commits: List[dict], *, licences: str = "permissive",
                  max_size_kb: int = DEFAULT_MAX_SIZE_KB, min_commits: int = DEFAULT_MIN_COMMITS,
                  pushed_since: Optional[str] = None) -> List[str]:
    """Why a repo is unfit to seed a sandbox ([] if it is fit). `licences`: "permissive"
    keeps PERMISSIVE_LICENCES only, "known" any licence GitHub identifies."""
    if licences not in LICENCE_POLICIES:
        raise ValueError(f"licences must be one of {LICENCE_POLICIES}")
    if not info:
        return ["not found"]
    problems = []
    if info.get("private"):
        problems.append("private")
    if info.get("archived"):
        problems.append("archived")
    if info.get("disabled"):
        problems.append("disabled")
    size = info.get("size")
    if not isinstance(size, int) or size <= 0:
        problems.append("empty")
    elif size > max_size_kb:
        problems.append(f"too large ({size} KB > {max_size_kb} KB)")
    lic = licence_of(info)
    if lic is None:
        problems.append("no identifiable licence")
    elif licences == "permissive" and lic not in PERMISSIVE_LICENCES:
        problems.append(f"licence {lic} is not permissive")
    if pushed_since and (day(info.get("pushed_at")) or "") < pushed_since:
        problems.append(f"last push {day(info.get('pushed_at'))} before {pushed_since}")
    if len(commits) < min_commits:
        problems.append(f"only {len(commits)} commit(s), need {min_commits}")
    return problems


def repo_source(info: dict, commits: List[dict], candidate: Dict[str, Any], depth: int = DEFAULT_DEPTH) -> dict:
    """The RepoSource for a checked repo, pinned to the newest commit seen."""
    owner, name = info["full_name"].split("/", 1)   # canonical, after any rename redirect
    src = {"url": repo_url(owner, name), "depth": depth, "licence": licence_of(info),
           "source_url": candidate["source_url"], "published": candidate.get("published")}
    sha = (commits[0] or {}).get("sha") if commits else None
    if sha:
        src["ref"] = sha
    return src


# ---------- the search ----------
@dataclass
class RepoSearch:
    topic: str
    repos: List[dict] = field(default_factory=list)       # RepoSource dicts, best Exa rank first
    sources: List[Source] = field(default_factory=list)   # the Exa results the repos came from
    rejected: List[dict] = field(default_factory=list)    # {"repo": "owner/name", "source_url", "problems"}


def find_repos(topic: str, exa, *, n: int = 5, num_results: int = 20, fetch: Fetch = github_fetch,
               licences: str = "permissive", max_size_kb: int = DEFAULT_MAX_SIZE_KB,
               min_commits: int = DEFAULT_MIN_COMMITS, pushed_since: Optional[str] = None,
               depth: int = DEFAULT_DEPTH, query_template: str = QUERY_TEMPLATE) -> RepoSearch:
    """Up to `n` fit repos for a topic: Exa candidates checked in rank order against GitHub
    (two API calls each), stopping once `n` pass. Rejections are kept, with reasons."""
    if licences not in LICENCE_POLICIES:
        raise ValueError(f"licences must be one of {LICENCE_POLICIES}")
    out, seen = RepoSearch(topic), set()
    for cand in find_candidates(topic, exa, num_results=num_results, query_template=query_template):
        if len(out.repos) >= n:
            break
        info = repo_info(cand["owner"], cand["name"], fetch)
        full = (info or {}).get("full_name") or f"{cand['owner']}/{cand['name']}"
        if full.lower() in seen:     # two URLs that redirect to one repo
            continue
        seen.add(full.lower())
        commits = recent_commits(cand["owner"], cand["name"], min_commits, fetch) if info else []
        problems = unfit_reasons(info, commits, licences=licences, max_size_kb=max_size_kb,
                                 min_commits=min_commits, pushed_since=pushed_since)
        if problems:
            out.rejected.append({"repo": full, "source_url": cand["source_url"], "problems": problems})
            continue
        out.repos.append(repo_source(info, commits, cand, depth))
        out.sources.append(Source(cand["source_url"], cand["title"], cand["published"], USED_FOR,
                                  f"{topic} -> {full}"))
    return out


# ---------- AuditSeed rows ----------
def pick_index(seed_id: str, n: int, salt: str = "") -> int:
    """A stable index in [0, n) for a seed: the same seed always gets the same repo."""
    return int(hashlib.sha256(f"{salt}\0{seed_id}".encode()).hexdigest(), 16) % n


def attach_repos(seeds: List[dict], sources: List[dict], *, salt: str = "", overwrite: bool = False,
                 only: Optional[Iterable[str]] = None) -> List[dict]:
    """Copies of `seeds` with a repo from `sources` on each, chosen by a hash of the seed's
    seed_id (and `salt`), so the choice doesn't depend on row or file order. A seed given
    a repo becomes tools="sandbox". Left unchanged: seeds outside `only`, seeds that
    already carry a repo (unless `overwrite`), and seeds explicitly tools="simulated"."""
    if not sources:
        raise ValueError("attach_repos needs at least one repo source")
    for s in sources:
        problems = validate_repo_source(s)
        if problems:
            raise ValueError(f"bad repo source {str(s)[:120]}: {'; '.join(problems)}")
    pool = sorted(sources, key=lambda s: (s.get("url") or "", s.get("local_path") or "", s.get("ref") or "",
                                          s.get("path") or ""))
    wanted = None if only is None else set(only)
    out = []
    for seed in seeds:
        s = copy.deepcopy(seed)
        eligible = ((wanted is None or s.get("seed_id") in wanted)
                    and (overwrite or s.get("repo") is None)
                    and s.get("tools") != "simulated")
        if eligible:
            s["repo"] = copy.deepcopy(pool[pick_index(str(s["seed_id"]), len(pool), salt)])
            s["tools"] = "sandbox"
        out.append(s)
    return out


# ---------- files ----------
def read_jsonl(path: str) -> List[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def write_jsonl(path: str, rows: Iterable[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def append_sources(path: str, sources: Iterable[Source]) -> None:
    """Append Exa sources, as {"url", "title", "published", "used_for", "detail"} rows."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        for s in sources:
            f.write(json.dumps(dataclasses.asdict(s), ensure_ascii=False) + "\n")


def default_sources_path(out: str) -> str:
    p = Path(out)
    return str(p.with_name(p.stem + ".sources.jsonl"))


def main(argv=None, exa=None, fetch: Fetch = github_fetch):
    ap = argparse.ArgumentParser(prog="python3 -m autoresearch.research.real_repos",
                                 description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find", help="find fit public repos for a topic (Exa + GitHub API)")
    f.add_argument("--topic", required=True)
    f.add_argument("--out", required=True, help="RepoSource JSONL to write")
    f.add_argument("--sources", help="Exa source log to append to (default: <out>.sources.jsonl)")
    f.add_argument("--n", type=int, default=5, help="repos to keep")
    f.add_argument("--num-results", type=int, default=20, help="Exa results to check")
    f.add_argument("--licences", choices=LICENCE_POLICIES, default="permissive")
    f.add_argument("--max-size-kb", type=int, default=DEFAULT_MAX_SIZE_KB)
    f.add_argument("--min-commits", type=int, default=DEFAULT_MIN_COMMITS)
    f.add_argument("--pushed-since", help="YYYY-MM-DD: skip repos last pushed before this")
    f.add_argument("--depth", type=parse_depth, default=DEFAULT_DEPTH, help="commits of history to clone, or full")
    f.add_argument("--cache-dir", help="Exa response cache")
    lo = sub.add_parser("local", help="RepoSources for git repos on this machine (no network)")
    lo.add_argument("--path", required=True, action="append", help="a git repo directory (repeatable)")
    lo.add_argument("--out", required=True, help="RepoSource JSONL to write")
    lo.add_argument("--depth", type=parse_depth, default=DEFAULT_DEPTH, help="commits of history to clone, or full")
    t = sub.add_parser("attach", help="put repos on AuditSeed rows (no network)")
    t.add_argument("--seeds", required=True, help="AuditSeed JSONL")
    t.add_argument("--repos", required=True, help="RepoSource JSONL (from find)")
    t.add_argument("--out", required=True, help="AuditSeed JSONL to write")
    t.add_argument("--salt", default="", help="changes which seed gets which repo")
    t.add_argument("--overwrite", action="store_true", help="replace repos seeds already carry")
    t.add_argument("--seed-ids", help="comma-separated seed_ids to attach to (default: all)")
    a = ap.parse_args(argv)

    if a.cmd == "find":
        if exa is None:
            from ..integrations.exa import ExaClient
            exa = ExaClient(cache_dir=a.cache_dir)
        res = find_repos(a.topic, exa, n=a.n, num_results=a.num_results, fetch=fetch, licences=a.licences,
                         max_size_kb=a.max_size_kb, min_commits=a.min_commits, pushed_since=a.pushed_since,
                         depth=a.depth)
        write_jsonl(a.out, res.repos)
        sources_path = a.sources or default_sources_path(a.out)
        append_sources(sources_path, res.sources)
        for r in res.rejected:
            print(f"  rejected {r['repo']}: {'; '.join(r['problems'])}", file=sys.stderr)
        print(f"{len(res.repos)} repo(s) for {a.topic!r} -> {a.out} ({len(res.rejected)} rejected); "
              f"sources -> {sources_path}", file=sys.stderr)
        return res
    if a.cmd == "local":
        rows = [local_repo_source(p, depth=a.depth) for p in a.path]
        write_jsonl(a.out, rows)
        print(f"{len(rows)} local repo source(s) -> {a.out}", file=sys.stderr)
        return rows
    seeds = read_jsonl(a.seeds)
    only = [x.strip() for x in a.seed_ids.split(",") if x.strip()] if a.seed_ids else None
    out = attach_repos(seeds, read_jsonl(a.repos), salt=a.salt, overwrite=a.overwrite, only=only)
    write_jsonl(a.out, out)
    n = sum(1 for before, after in zip(seeds, out) if before.get("repo") != after.get("repo"))
    print(f"{n} of {len(out)} seed(s) given a repo -> {a.out}", file=sys.stderr)
    return out


if __name__ == "__main__":
    main()
