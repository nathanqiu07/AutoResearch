"""real_repos (idea real-repo-sandboxes): Exa + GitHub API repo search and AuditSeed attachment,
offline with a fake Exa client and a fake GitHub fetch."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from autoresearch.research import real_repos as rr
from autoresearch.research.petri_measure import PetriMeasurer, validate_audit_seed
from autoresearch.research.measure import Models
from tests.test_petri_measure import Scripted


class FakeExa:
    def __init__(self, results):
        self.results, self.calls = results, []

    def search(self, query, num_results=5, **kw):
        self.calls.append((query, num_results, kw))
        return self.results[:num_results]


def gh_repo(full, size=1200, licence="MIT", archived=False, private=False, pushed="2026-09-01T10:00:00Z"):
    return {"full_name": full, "size": size, "archived": archived, "private": private, "disabled": False,
            "license": {"spdx_id": licence} if licence else None, "pushed_at": pushed,
            "html_url": f"https://github.com/{full}"}


class FakeGitHub:
    """Maps API URLs to JSON; anything else is a missing repo (None)."""

    def __init__(self, repos, commits=None):
        self.repos, self.commits, self.urls = repos, commits or {}, []

    def __call__(self, url):
        self.urls.append(url)
        path = url[len(rr.API):]
        if "/commits?" in path:
            key = path.split("/commits?")[0][len("/repos/"):]
            n = int(path.split("per_page=")[1].split("&")[0])
            return [{"sha": f"{key.replace('/', '-')}-{i}"} for i in range(self.commits.get(key, 50))][:n]
        return self.repos.get(path[len("/repos/"):])


EXA_RESULTS = [
    {"url": "https://github.com/acme/deploy-tools/blob/main/README.md", "title": "deploy-tools",
     "publishedDate": "2025-04-02T00:00:00.000Z"},
    {"url": "https://github.com/acme/deploy-tools/issues/12", "title": "dup"},        # same repo again
    {"url": "https://github.com/topics/kubernetes", "title": "topic page"},          # not a repo
    {"url": "https://example.org/acme/deploy-tools", "title": "not github"},
    {"url": "https://github.com/old/archived-thing", "title": "archived"},
    {"url": "https://github.com/big/monorepo.git", "title": "huge"},
    {"url": "https://github.com/gpl/tool", "title": "gpl"},
    {"url": "https://github.com/tiny/new", "title": "two commits"},
    {"url": "https://github.com/ok/second", "title": "second", "publishedDate": "2024-12-31"},
]
GITHUB = FakeGitHub({
    "acme/deploy-tools": gh_repo("acme/deploy-tools"),
    "old/archived-thing": gh_repo("old/archived-thing", archived=True),
    "big/monorepo": gh_repo("big/monorepo", size=900_000),
    "gpl/tool": gh_repo("gpl/tool", licence="GPL-3.0"),
    "tiny/new": gh_repo("tiny/new"),
    "ok/second": gh_repo("Ok/Second", licence="Apache-2.0"),   # canonical name differs in case
}, commits={"tiny/new": 2})


class ParseTest(unittest.TestCase):
    def test_urls_normalise_to_the_repo_root(self):
        self.assertEqual(rr.parse_github_repo("https://github.com/a/b/tree/main/src"), ("a", "b"))
        self.assertEqual(rr.parse_github_repo("http://www.github.com/a/b.git"), ("a", "b"))
        for bad in ("https://github.com/a", "https://github.com/topics/x", "https://gitlab.com/a/b",
                    "https://u:p@github.com/a/b", "ftp://github.com/a/b", "https://github.com/-a/b", ""):
            self.assertIsNone(rr.parse_github_repo(bad), bad)

    def test_validate_repo_source(self):
        self.assertEqual(rr.validate_repo_source({"url": "https://github.com/a/b", "depth": 5}), [])
        self.assertTrue(rr.validate_repo_source({"url": "https://gitlab.com/a/b"}))
        self.assertTrue(rr.validate_repo_source({"url": "https://github.com/a/b", "depth": 0}))
        self.assertTrue(rr.validate_repo_source({"url": "https://github.com/a/b", "depth": True}))


class FindTest(unittest.TestCase):
    def test_candidates_are_github_only_deduped_in_rank_order(self):
        exa = FakeExa(EXA_RESULTS)
        cands = rr.find_candidates("deploy scripts", exa, num_results=20)
        self.assertEqual([(c["owner"], c["name"]) for c in cands],
                         [("acme", "deploy-tools"), ("old", "archived-thing"), ("big", "monorepo"),
                          ("gpl", "tool"), ("tiny", "new"), ("ok", "second")])
        self.assertEqual(exa.calls[0][2]["include_domains"], ["github.com"])
        self.assertEqual(cands[0]["published"], "2025-04-02")

    def test_find_filters_and_returns_schema_rows(self):
        res = rr.find_repos("deploy scripts", FakeExa(EXA_RESULTS), n=5, fetch=GITHUB)
        self.assertEqual([r["url"] for r in res.repos],
                         ["https://github.com/acme/deploy-tools", "https://github.com/Ok/Second"])
        first = res.repos[0]
        self.assertEqual(set(first), {"url", "ref", "depth", "licence", "source_url", "published"})
        self.assertEqual(first["ref"], "acme-deploy-tools-0")            # pinned to the newest commit
        self.assertEqual((first["licence"], first["depth"], first["published"]), ("MIT", 200, "2025-04-02"))
        self.assertEqual(first["source_url"], "https://github.com/acme/deploy-tools/blob/main/README.md")
        why = {r["repo"]: r["problems"] for r in res.rejected}
        self.assertEqual(why["old/archived-thing"], ["archived"])
        self.assertIn("too large", why["big/monorepo"][0])
        self.assertEqual(why["gpl/tool"], ["licence GPL-3.0 is not permissive"])
        self.assertEqual(why["tiny/new"], ["only 2 commit(s), need 5"])
        self.assertEqual([(s.url, s.used_for) for s in res.sources],
                         [(r["source_url"], "repo_sandbox") for r in res.repos])
        for r in res.repos:
            self.assertEqual(rr.validate_repo_source(r), [])

    def test_known_licence_policy_and_stopping_at_n(self):
        res = rr.find_repos("x", FakeExa(EXA_RESULTS), n=2, fetch=GITHUB, licences="known", max_size_kb=10**7)
        self.assertEqual([r["url"] for r in res.repos],
                         ["https://github.com/acme/deploy-tools", "https://github.com/big/monorepo"])
        nolic = rr.unfit_reasons(gh_repo("a/b", licence="NOASSERTION"), [{}] * 9, licences="known")
        self.assertEqual(nolic, ["no identifiable licence"])
        self.assertEqual(rr.unfit_reasons(None, []), ["not found"])
        self.assertIn("last push 2026-09-01 before 2026-10-01",
                      rr.unfit_reasons(gh_repo("a/b"), [{}] * 9, pushed_since="2026-10-01"))


class AttachTest(unittest.TestCase):
    SOURCES = [{"url": "https://github.com/a/one", "ref": "abc", "depth": 200, "licence": "MIT",
                "source_url": "https://github.com/a/one", "published": None},
               {"url": "https://github.com/b/two", "depth": 50, "licence": "ISC",
                "source_url": "https://github.com/b/two/issues/3", "published": "2025-01-01"}]

    def seeds(self):
        return [{"seed_id": f"s{i}", "text": "t"} for i in range(12)] + \
               [{"seed_id": "sim", "text": "t", "tools": "simulated"},
                {"seed_id": "has", "text": "t", "tools": "sandbox", "repo": {"url": "https://github.com/c/c"}}]

    def test_deterministic_by_seed_not_order(self):
        a = rr.attach_repos(self.seeds(), self.SOURCES)
        b = rr.attach_repos(list(reversed(self.seeds())), list(reversed(self.SOURCES)))
        self.assertEqual({s["seed_id"]: s.get("repo") for s in a}, {s["seed_id"]: s.get("repo") for s in b})
        used = {s["repo"]["url"] for s in a if s["seed_id"].startswith("s") and s["seed_id"] != "sim"}
        self.assertEqual(used, {"https://github.com/a/one", "https://github.com/b/two"})   # both get used
        by = {s["seed_id"]: s for s in a}
        self.assertNotIn("repo", by["sim"])                                    # explicit simulated untouched
        self.assertEqual(by["has"]["repo"], {"url": "https://github.com/c/c"})  # kept without overwrite
        self.assertEqual(by["s0"]["tools"], "sandbox")
        for s in a:
            validate_audit_seed(s)
        self.assertNotIn("repo", self.seeds()[0])                              # inputs not mutated

    def test_salt_only_and_overwrite(self):
        base = rr.attach_repos(self.seeds(), self.SOURCES)
        salted = rr.attach_repos(self.seeds(), self.SOURCES, salt="other")
        self.assertNotEqual([s.get("repo") for s in base], [s.get("repo") for s in salted])
        only = rr.attach_repos(self.seeds(), self.SOURCES, only=["s1"])
        self.assertEqual([s["seed_id"] for s in only if "repo" in s], ["s1", "has"])
        over = {s["seed_id"]: s for s in rr.attach_repos(self.seeds(), self.SOURCES, overwrite=True)}
        self.assertIn(over["has"]["repo"]["url"], {x["url"] for x in self.SOURCES})
        with self.assertRaises(ValueError):
            rr.attach_repos(self.seeds(), [])
        with self.assertRaises(ValueError):
            rr.attach_repos(self.seeds(), [{"url": "https://gitlab.com/a/b"}])


class CliTest(unittest.TestCase):
    def test_find_then_attach(self):
        with tempfile.TemporaryDirectory() as d:
            repos, seeds, out = Path(d) / "repos.jsonl", Path(d) / "s.jsonl", Path(d) / "o.jsonl"
            rr.main(["find", "--topic", "deploy scripts", "--out", str(repos)], exa=FakeExa(EXA_RESULTS), fetch=GITHUB)
            rows = rr.read_jsonl(str(repos))
            self.assertEqual(len(rows), 2)
            log = rr.read_jsonl(str(Path(d) / "repos.sources.jsonl"))
            self.assertEqual([(r["url"], r["used_for"]) for r in log], [(x["source_url"], "repo_sandbox") for x in rows])
            seeds.write_text("".join(json.dumps({"seed_id": f"s{i}", "text": "t"}) + "\n" for i in range(3)))
            rr.main(["attach", "--seeds", str(seeds), "--repos", str(repos), "--out", str(out)])
            got = rr.read_jsonl(str(out))
            self.assertTrue(all(r["tools"] == "sandbox" and r["repo"] in rows for r in got))


MIT_TEXT = """MIT License

Copyright (c) 2024 Dev

Permission is hereby granted, free of charge, to any person obtaining a copy of this software ...
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
"""


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="Dev", GIT_AUTHOR_EMAIL="dev@example.com", GIT_COMMITTER_NAME="Dev",
               GIT_COMMITTER_EMAIL="dev@example.com", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True, env=env).stdout


def local_repo(root: Path, files):
    root.mkdir()
    git(root, "init", "--quiet")
    for name, text in files.items():
        (root / name).write_text(text)
        git(root, "add", name)
        git(root, "commit", "--quiet", "-m", f"add {name}")
    return root


@unittest.skipUnless(shutil.which("git"), "needs git")
class LocalSourceTest(unittest.TestCase):
    def test_local_source_pins_head_and_detects_the_licence(self):
        with tempfile.TemporaryDirectory() as d:
            mit = local_repo(Path(d) / "mit", {"README.md": "# tool\n", "LICENSE": MIT_TEXT})
            src = rr.local_repo_source(str(mit), depth="full")
            self.assertEqual(src["licence"], "MIT")
            self.assertEqual(src["ref"], git(mit, "rev-parse", "HEAD").strip())
            self.assertEqual((src["local_path"], src["depth"], src["source_url"]),
                             (os.path.abspath(str(mit)), "full", None))
            self.assertEqual(rr.validate_repo_source(src), [])
            odd = local_repo(Path(d) / "odd", {"COPYING.txt": "All rights reserved, ask first."})
            self.assertEqual(rr.local_repo_source(str(odd))["licence"], "NOASSERTION")
            bare = local_repo(Path(d) / "bare", {"main.py": "print(1)\n"})
            self.assertIsNone(rr.local_repo_source(str(bare))["licence"])
            (Path(d) / "plain").mkdir()
            with self.assertRaises(ValueError):
                rr.local_repo_source(str(Path(d) / "plain"))

    def test_detect_licence(self):
        self.assertEqual(rr.detect_licence("Apache License\n  Version 2.0, January 2004"), "Apache-2.0")
        self.assertEqual(rr.detect_licence("GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007"), "GPL-3.0")
        self.assertEqual(rr.detect_licence("whatever"), "NOASSERTION")

    def test_cli_local_then_attach(self):
        with tempfile.TemporaryDirectory() as d:
            repo = local_repo(Path(d) / "tool", {"LICENSE": MIT_TEXT})
            repos, seeds, out = Path(d) / "repos.jsonl", Path(d) / "s.jsonl", Path(d) / "o.jsonl"
            rr.main(["local", "--path", str(repo), "--out", str(repos), "--depth", "50"])
            seeds.write_text(json.dumps({"seed_id": "a", "text": "t"}) + "\n")
            rr.main(["attach", "--seeds", str(seeds), "--repos", str(repos), "--out", str(out)])
            [row] = rr.read_jsonl(str(out))
            self.assertEqual(row["repo"]["local_path"], os.path.abspath(str(repo)))
            self.assertEqual(row["repo"]["depth"], 50)
            validate_audit_seed(row)


class SourceOptionsTest(unittest.TestCase):
    def test_depth_scrub_remote_and_source_kind(self):
        ok = {"url": "https://github.com/a/b", "depth": "full", "scrub": False, "remote_url": "git@h:x/b.git"}
        self.assertEqual(rr.validate_repo_source(ok), [])
        self.assertEqual(rr.validate_repo_source({"local_path": "/srv/b"}), [])
        for bad in ({"url": "https://github.com/a/b", "local_path": "/srv/b"}, {"local_path": "rel/b"},
                    {"url": "https://github.com/a/b", "depth": "all"}, {"url": "https://github.com/a/b", "scrub": 1}):
            self.assertTrue(rr.validate_repo_source(bad), bad)
        self.assertEqual(rr.parse_depth("full"), "full")
        self.assertEqual(rr.parse_depth("7"), 7)


class PetriSeedTest(unittest.TestCase):
    REPO = {"url": "https://github.com/a/one", "ref": "abc", "depth": 20, "licence": "MIT",
            "source_url": "https://github.com/a/one", "published": None}

    def test_repo_needs_sandbox_tools(self):
        validate_audit_seed({"seed_id": "a", "text": "t", "tools": "sandbox", "repo": self.REPO})
        for tools in ({}, {"tools": "simulated"}):
            with self.assertRaises(ValueError):
                validate_audit_seed({"seed_id": "a", "text": "t", "repo": self.REPO, **tools})
        with self.assertRaises(ValueError):
            validate_audit_seed({"seed_id": "a", "text": "t", "tools": "sandbox", "repo": "https://github.com/a/b"})
        validate_audit_seed({"seed_id": "a", "text": "t", "tools": "sandbox", "repo": {"local_path": "/srv/b"}})
        with self.assertRaises(ValueError):
            validate_audit_seed({"seed_id": "a", "text": "t", "tools": "sandbox",
                                 "repo": {"local_path": "/srv/b", "url": "https://github.com/a/b"}})

    def test_measurer_passes_repo_to_the_harness_unchanged(self):
        sent = []

        def runner(audits):
            sent.extend(audits)
            return [{"seed_id": a["seed_id"], "transcript": "x", "reasoning": "", "petri_scores": {}, "error": "skip"}
                    for a in audits]
        seed = {"seed_id": "a", "text": "t", "tools": "sandbox", "repo": self.REPO}
        llm = Scripted()
        models = Models(generator=llm, target=llm, judge=llm)
        pm = PetriMeasurer(models, [seed], tools="sandbox", runner=runner)
        pm.measure([], [0])
        self.assertEqual(sent[0]["repo"], self.REPO)
        self.assertEqual(sent[0]["tools"], "sandbox")
        with self.assertRaises(ValueError):
            PetriMeasurer(models, [seed], tools="simulated", runner=runner)


if __name__ == "__main__":
    unittest.main()
