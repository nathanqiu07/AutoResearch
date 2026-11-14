#!/usr/bin/env python3
"""agentctl: coordination for multiple coding agents working on this repo.

Everything is plain files under .agents/, synced through git, designed so
concurrent agents never produce merge conflicts:
  * one file per message, per claim, per lock (append-only, unique names);
  * a task's status lives in its own file and only its claimant edits it;
  * "first push wins": claim/lock commits right away; if the push is
    rejected, the agent rebases and re-checks the claim's owner.

  agentctl.py register NAME --role "what I work on"
  agentctl.py sync                         pull --rebase (do this before starting anything)
  agentctl.py status                       board, claims, locks, unread count
  agentctl.py task add SLUG "title" [--body ...] [--area paths]
  agentctl.py task list [--status open]
  agentctl.py claim SLUG   /  release SLUG  /  done SLUG --summary "..."
  agentctl.py lock PATH... --reason "..."  /  unlock PATH...
  agentctl.py post "subject" "body" [--to NAME|all] [--task SLUG]
  agentctl.py inbox [--all]                messages to you or to all, unread first
  agentctl.py heartbeat                    refresh your claims/locks (stale after 2h)

Your agent name comes from $AGENT_NAME or `register` (stored, untracked, in
.agents/.me). Pass --no-git to skip git (tests, offline use).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import uuid

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
A = os.path.join(ROOT, ".agents")
STALE_HOURS = 2.0


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t=None):
    return (t or now()).isoformat()


def parse_iso(s):
    return dt.datetime.fromisoformat(s)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


class Ctl:
    def __init__(self, root=A, use_git=True):
        self.root, self.use_git = root, use_git
        for d in ("tasks", "claims", "messages", "locks", "agents"):
            os.makedirs(os.path.join(root, d), exist_ok=True)

    # ---------- identity ----------
    def me(self):
        name = os.environ.get("AGENT_NAME")
        p = os.path.join(self.root, ".me")
        if not name and os.path.exists(p):
            name = open(p).read().strip()
        if not name:
            sys.exit("no agent name: run `agentctl.py register NAME` or set AGENT_NAME")
        return name

    def register(self, name, role):
        name = slugify(name)
        open(os.path.join(self.root, ".me"), "w").write(name)
        self._write_json(f"agents/{name}.json", {"name": name, "role": role, "registered": iso(),
                                                 "last_seen": iso()})
        self._commit(f"agent {name} registered", [f"agents/{name}.json"])
        return name

    # ---------- git ----------
    def _git(self, *args, check=True):
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=check)

    def sync(self):
        if not self.use_git:
            return
        r = self._git("pull", "--rebase", "--autostash", check=False)
        if r.returncode != 0:
            print("sync failed; resolve manually:\n" + r.stderr.strip(), file=sys.stderr)

    def _commit(self, msg, rel_paths, push=True):
        if not self.use_git:
            return True
        paths = [os.path.join(self.root, p) for p in rel_paths]
        self._git("add", "--", *paths)
        if self._git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return True
        self._git("commit", "-m", f"[agents] {msg}", "--", *paths)
        if not push:
            return True
        for _ in range(3):
            if self._git("push", check=False).returncode == 0:
                return True
            self._git("pull", "--rebase", "--autostash", check=False)
        print("warning: push failed; your coordination change is committed locally only", file=sys.stderr)
        return False

    # ---------- files ----------
    def _path(self, rel):
        return os.path.join(self.root, rel)

    def _write_json(self, rel, obj):
        with open(self._path(rel), "w") as f:
            json.dump(obj, f, indent=1)

    def _read_json(self, rel):
        p = self._path(rel)
        return json.load(open(p)) if os.path.exists(p) else None

    @staticmethod
    def _stale(rec):
        return (now() - parse_iso(rec["heartbeat"])).total_seconds() > STALE_HOURS * 3600

    # ---------- tasks ----------
    def task_add(self, slug, title, body="", area=""):
        slug = slugify(slug)
        rel = f"tasks/{slug}.json"
        if self._read_json(rel):
            sys.exit(f"task {slug} exists")
        self._write_json(rel, {"slug": slug, "title": title, "body": body, "area": area,
                               "status": "open", "created_by": self.me(), "created": iso(),
                               "summary": ""})
        self._commit(f"task {slug} added", [rel])
        return slug

    def tasks(self, status=None):
        out = []
        for f in sorted(os.listdir(self._path("tasks"))):
            if f.endswith(".json"):
                t = self._read_json(f"tasks/{f}")
                c = self._read_json(f"claims/{t['slug']}.json")
                t["owner"] = c["agent"] if c and not self._stale(c) else None
                if t["status"] == "open" and t["owner"]:
                    t["status"] = "claimed"
                if status is None or t["status"] == status:
                    out.append(t)
        return out

    def claim(self, slug):
        self.sync()
        me = self.me()
        t = self._read_json(f"tasks/{slug}.json")
        if not t:
            sys.exit(f"no task {slug}")
        if t["status"] == "done":
            sys.exit(f"task {slug} is done")
        c = self._read_json(f"claims/{slug}.json")
        if c and c["agent"] != me and not self._stale(c):
            sys.exit(f"task {slug} is claimed by {c['agent']} (heartbeat {c['heartbeat']})")
        self._write_json(f"claims/{slug}.json", {"task": slug, "agent": me, "claimed": iso(),
                                                 "heartbeat": iso()})
        self._commit(f"{me} claims {slug}", [f"claims/{slug}.json"])
        self.sync()  # first push wins: re-check after rebase
        c = self._read_json(f"claims/{slug}.json")
        if c["agent"] != me:
            sys.exit(f"lost the race: {slug} is claimed by {c['agent']}")
        return True

    def release(self, slug, done=False, summary=""):
        me = self.me()
        c = self._read_json(f"claims/{slug}.json")
        if c and c["agent"] != me:
            sys.exit(f"{slug} is claimed by {c['agent']}, not you")
        rels = []
        if c:
            os.remove(self._path(f"claims/{slug}.json"))
            rels.append(f"claims/{slug}.json")
        if done:
            t = self._read_json(f"tasks/{slug}.json")
            t.update(status="done", summary=summary, done_by=me, done=iso())
            self._write_json(f"tasks/{slug}.json", t)
            rels.append(f"tasks/{slug}.json")
        if self.use_git and c:
            self._git("rm", "--cached", "-q", "--ignore-unmatch", self._path(f"claims/{slug}.json"), check=False)
        self._commit(f"{me} {'finished' if done else 'released'} {slug}", rels)

    # ---------- locks (path areas) ----------
    @staticmethod
    def _lock_name(path):
        return slugify(path.replace("/", "__")) or "root"

    def locks(self):
        out = []
        for f in sorted(os.listdir(self._path("locks"))):
            if f.endswith(".json"):
                l = self._read_json(f"locks/{f}")
                l["stale"] = self._stale(l)
                out.append(l)
        return out

    def conflicting_lock(self, path, me):
        path = path.rstrip("/")
        for l in self.locks():
            if l["agent"] == me or l["stale"]:
                continue
            lp = l["path"].rstrip("/")
            if path == lp or path.startswith(lp + "/") or lp.startswith(path + "/"):
                return l
        return None

    def lock(self, paths, reason=""):
        self.sync()
        me, rels = self.me(), []
        for p in paths:
            c = self.conflicting_lock(p, me)
            if c:
                sys.exit(f"{p} overlaps a lock on {c['path']} held by {c['agent']}: {c['reason']}")
            rel = f"locks/{self._lock_name(p)}.json"
            self._write_json(rel, {"path": p, "agent": me, "reason": reason, "locked": iso(),
                                   "heartbeat": iso()})
            rels.append(rel)
        self._commit(f"{me} locks {' '.join(paths)}", rels)

    def unlock(self, paths):
        me, rels = self.me(), []
        for p in paths:
            rel = f"locks/{self._lock_name(p)}.json"
            l = self._read_json(rel)
            if l and l["agent"] == me:
                os.remove(self._path(rel))
                rels.append(rel)
                if self.use_git:
                    self._git("rm", "--cached", "-q", "--ignore-unmatch", self._path(rel), check=False)
        self._commit(f"{me} unlocks {' '.join(paths)}", rels)

    def heartbeat(self):
        me, rels = self.me(), []
        for d in ("claims", "locks"):
            for f in os.listdir(self._path(d)):
                rel = f"{d}/{f}"
                rec = self._read_json(rel) if f.endswith(".json") else None
                if rec and rec.get("agent") == me:
                    rec["heartbeat"] = iso()
                    self._write_json(rel, rec)
                    rels.append(rel)
        a = self._read_json(f"agents/{me}.json")
        if a:
            a["last_seen"] = iso()
            self._write_json(f"agents/{me}.json", a)
            rels.append(f"agents/{me}.json")
        self._commit(f"{me} heartbeat", rels)

    # ---------- messages ----------
    def post(self, subject, body, to="all", task=""):
        me = self.me()
        t = now()
        name = f"{t.strftime('%Y%m%dT%H%M%SZ')}-{me}-{uuid.uuid4().hex[:6]}.json"
        self._write_json(f"messages/{name}", {"id": name[:-5], "from": me, "to": to, "task": task,
                                              "subject": subject, "body": body, "sent": iso(t)})
        self._commit(f"{me} -> {to}: {subject[:50]}", [f"messages/{name}"])
        return name[:-5]

    def messages(self, me=None, include_read=False):
        me = me or self.me()
        read_p = self._path(f".read-{me}")
        seen = set(open(read_p).read().split()) if os.path.exists(read_p) else set()
        out = []
        for f in sorted(os.listdir(self._path("messages"))):
            if not f.endswith(".json"):
                continue
            m = self._read_json(f"messages/{f}")
            if m["to"] in ("all", me) and m["from"] != me and (include_read or m["id"] not in seen):
                out.append(m)
        return out

    def mark_read(self, ids, me=None):
        me = me or self.me()
        with open(self._path(f".read-{me}"), "a") as f:
            for i in ids:
                f.write(i + "\n")


def main(argv=None):
    p = argparse.ArgumentParser(prog="agentctl", description=__doc__.split("\n\n")[0])
    p.add_argument("--no-git", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register"); r.add_argument("name"); r.add_argument("--role", default="")
    sub.add_parser("sync"); sub.add_parser("status"); sub.add_parser("heartbeat")
    t = sub.add_parser("task"); ts = t.add_subparsers(dest="tcmd", required=True)
    ta = ts.add_parser("add"); ta.add_argument("slug"); ta.add_argument("title")
    ta.add_argument("--body", default=""); ta.add_argument("--area", default="")
    tl = ts.add_parser("list"); tl.add_argument("--status")
    c = sub.add_parser("claim"); c.add_argument("slug")
    rl = sub.add_parser("release"); rl.add_argument("slug")
    d = sub.add_parser("done"); d.add_argument("slug"); d.add_argument("--summary", required=True)
    lk = sub.add_parser("lock"); lk.add_argument("paths", nargs="+"); lk.add_argument("--reason", default="")
    ul = sub.add_parser("unlock"); ul.add_argument("paths", nargs="+")
    po = sub.add_parser("post"); po.add_argument("subject"); po.add_argument("body")
    po.add_argument("--to", default="all"); po.add_argument("--task", default="")
    ib = sub.add_parser("inbox"); ib.add_argument("--all", action="store_true")
    a = p.parse_args(argv)
    ctl = Ctl(use_git=not a.no_git)

    if a.cmd == "register":
        print("registered as", ctl.register(a.name, a.role))
    elif a.cmd == "sync":
        ctl.sync()
    elif a.cmd == "heartbeat":
        ctl.heartbeat()
    elif a.cmd == "task" and a.tcmd == "add":
        print("added", ctl.task_add(a.slug, a.title, a.body, a.area))
    elif a.cmd == "task":
        for x in ctl.tasks(a.status):
            print(f"[{x['status']:<7}] {x['slug']:<32} {x['title']}" + (f"  (owner: {x['owner']})" if x["owner"] else ""))
    elif a.cmd == "claim":
        ctl.claim(a.slug); print("claimed", a.slug)
    elif a.cmd == "release":
        ctl.release(a.slug); print("released", a.slug)
    elif a.cmd == "done":
        ctl.release(a.slug, done=True, summary=a.summary); print("done", a.slug)
    elif a.cmd == "lock":
        ctl.lock(a.paths, a.reason); print("locked", *a.paths)
    elif a.cmd == "unlock":
        ctl.unlock(a.paths); print("unlocked", *a.paths)
    elif a.cmd == "post":
        print("sent", ctl.post(a.subject, a.body, a.to, a.task))
    elif a.cmd == "inbox":
        ms = ctl.messages(include_read=a.all)
        for m in ms:
            print(f"--- {m['sent']} from {m['from']} to {m['to']}" + (f" [task {m['task']}]" if m["task"] else ""))
            print(f"    {m['subject']}\n    {m['body']}")
        ctl.mark_read([m["id"] for m in ms])
        if not ms:
            print("no new messages")
    elif a.cmd == "status":
        ctl.sync()
        me = os.environ.get("AGENT_NAME") or (open(ctl._path(".me")).read().strip() if os.path.exists(ctl._path(".me")) else None)
        print(f"you: {me or '(unregistered)'}")
        for x in ctl.tasks():
            if x["status"] != "done":
                print(f"  [{x['status']:<7}] {x['slug']:<32} {x['title']}" + (f"  (owner: {x['owner']})" if x["owner"] else ""))
        for l in ctl.locks():
            print(f"  lock {l['path']} by {l['agent']}{' (stale)' if l['stale'] else ''}: {l['reason']}")
        if me:
            print(f"  unread messages: {len(ctl.messages(me))}")


if __name__ == "__main__":
    main()
