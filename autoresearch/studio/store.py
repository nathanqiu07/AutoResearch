"""Profile storage for the studio: one researcher directory per profile.

Files the studio writes inside data/researchers/<slug>/ (everything else is the
existing layout described in taste/researcher.py and taste/trackp.py):

  studio.json      studio metadata: name, mode, bio, questionnaire answers, summary, build log
  corpus/*.txt     documents with front matter (the same format as taste/scrape._write_doc)
  CONSENT.md       personal mode only, the personal track's consent form (trackp.CONSENT_TEMPLATE)
  profile.json     the TasteProfile the loop loads (Researcher.cached_profile)

A directory without studio.json was made some other way (demo researchers, Track S
harvests). The studio shows it read-only and never writes into it.
"""
from __future__ import annotations

import datetime
import glob
import hashlib
import json
import os
import re
import threading
from collections import Counter, defaultdict
from functools import wraps
from typing import Dict, List, Optional, Tuple

from ..llm import LLM, OfflineLLM, extract_json
from ..taste.choices import fit_choice_model_cv, load_choices
from ..taste.extract import profile_from_texts
from ..taste.profile import FEATURES, TasteProfile
from ..taste.researcher import list_researchers
from ..taste import trackp
from .questionnaire import BY_ID, QUESTIONS

STUDIO_FILE = "studio.json"
MODES = ("personal", "public")
KINDS = ("research", "other")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,62}$")
DOC_RE = re.compile(r"^(research|other)__[a-z0-9_]+\.txt$")
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
QUESTIONNAIRE_STEM = "studio_questionnaire"
MAX_DOC_CHARS = 400_000


class StudioError(ValueError):
    """A request the studio refuses; the message is shown to the user."""


# The server handles requests and background jobs on several threads. Every function that
# reads, changes and writes a profile's files holds that profile's lock, so two concurrent
# saves (two questionnaire answers, an answer during a gather) never overwrite each other.
_LOCKS = defaultdict(threading.RLock)
_LOCKS_GUARD = threading.Lock()


def _lock_for(root: str, slug: str) -> threading.RLock:
    with _LOCKS_GUARD:
        return _LOCKS[(os.path.abspath(root), slug)]


def _locked(fn):
    @wraps(fn)
    def inner(root, slug, *args, **kwargs):
        with _lock_for(root, slug):
            return fn(root, slug, *args, **kwargs)
    return inner


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _dir(root: str, slug: str) -> str:
    if not SLUG_RE.match(slug or ""):
        raise StudioError(f"invalid profile id {slug!r}: lowercase letters, digits and _ only")
    return os.path.join(root, slug)


def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def _write_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


# ---- profiles ----------------------------------------------------------------

def create_profile(root: str, name: str, mode: str, slug: Optional[str] = None) -> dict:
    name = (name or "").strip()
    if not name:
        raise StudioError("a name is required")
    if mode not in MODES:
        raise StudioError(f"mode must be one of {MODES}")
    slug = slug or slugify(name)
    d = _dir(root, slug)
    if os.path.exists(d):
        raise StudioError(f"a researcher called {slug!r} already exists; pick another id")
    os.makedirs(os.path.join(d, "corpus"))
    meta = {"slug": slug, "name": name, "mode": mode, "created": _now(), "updated": _now(),
            "affiliation": "", "homepage": "", "bio": "", "bio_source": "", "s2_author": None,
            "questionnaire": {}, "summary": None, "build": None}
    _write_json(os.path.join(d, STUDIO_FILE), meta)
    return meta


def is_editable(root: str, slug: str) -> bool:
    return os.path.exists(os.path.join(_dir(root, slug), STUDIO_FILE))


def load_meta(root: str, slug: str) -> dict:
    d = _dir(root, slug)
    if not os.path.isdir(d):
        raise KeyError(slug)
    return _read_json(os.path.join(d, STUDIO_FILE), {"slug": slug, "name": slug, "mode": "external"})


def require_editable(root: str, slug: str) -> dict:
    meta = load_meta(root, slug)
    if not is_editable(root, slug):
        raise StudioError(f"{slug!r} was not made in the studio; it is read-only here")
    return meta


@_locked
def update_meta(root: str, slug: str, **fields) -> dict:
    meta = require_editable(root, slug)
    meta.update(fields)
    meta["updated"] = _now()
    _write_json(os.path.join(_dir(root, slug), STUDIO_FILE), meta)
    return meta


def list_profiles(root: str) -> List[dict]:
    out = []
    for slug in list_researchers(root):
        if not SLUG_RE.match(slug):
            continue
        meta = load_meta(root, slug)
        d = _dir(root, slug)
        out.append({"slug": slug, "name": meta.get("name", slug), "mode": meta.get("mode", "external"),
                    "editable": is_editable(root, slug), "updated": meta.get("updated", ""),
                    "n_docs": len(list_docs(root, slug)),
                    "has_profile": os.path.exists(os.path.join(d, "profile.json")),
                    "has_usermodel": os.path.exists(os.path.join(d, trackp.USERMODEL))})
    out.sort(key=lambda p: p["updated"], reverse=True)   # newest first,
    return sorted(out, key=lambda p: not p["editable"])  # studio profiles before read-only ones


def profile_state(root: str, slug: str) -> dict:
    """Everything the UI shows for one profile."""
    meta = load_meta(root, slug)
    d = _dir(root, slug)
    prof = _read_json(os.path.join(d, "profile.json"), None)
    answered = trackp._read(os.path.join(d, trackp.SEED_CHOICES))
    pairs = trackp._read(os.path.join(d, trackp.SEED_PAIRS))
    return {"meta": meta, "editable": is_editable(root, slug), "docs": list_docs(root, slug),
            "profile": prof, "features": FEATURES,
            "consent": consent_state(root, slug),
            "choices": {"pairs": len(pairs), "answered": len(answered)},
            "has_usermodel": os.path.exists(os.path.join(d, trackp.USERMODEL)),
            "questions": QUESTIONS}


# ---- corpus documents ----------------------------------------------------------

def _one_line(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def split_front_matter(raw: str) -> Tuple[dict, str]:
    m = FRONT_MATTER.match(raw)
    if not m:
        return {}, raw
    fm = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    return fm, raw[m.end():]


@_locked
def add_doc(root: str, slug: str, kind: str, title: str, text: str, source: str, url: str = "",
            date: str = "", extra: Optional[Dict[str, str]] = None, stem: Optional[str] = None) -> Tuple[str, bool]:
    """Write one corpus document. Returns (file name, created), where created is False when
    the item was already in the corpus.

    The name is derived from the title and the URL (or the text), so adding the same item
    twice rewrites one file. The same work found under another URL (an arXiv paper
    cross-posted to a forum, say) is matched by title: the fuller text is kept and the other
    URL is recorded as `also_at`, so one work never counts twice in the profile."""
    require_editable(root, slug)
    if kind not in KINDS:
        raise StudioError(f"kind must be one of {KINDS}")
    text = (text or "").strip()
    if not text:
        raise StudioError(f"no text for {title or url or 'document'}")
    title = _one_line(title or url or text[:60])
    key = url or text
    stem = stem or (slugify(title)[:50] + "_" + hashlib.sha256(key.encode()).hexdigest()[:8])
    name = f"{kind}__{stem}.txt"
    path = os.path.join(_dir(root, slug), "corpus", name)
    created = not os.path.exists(path)
    also_at = []
    if created and source != "questionnaire":
        for other in _same_title(root, slug, title, exclude=name):
            if other["chars"] >= len(text) + len(title) + 4:   # body length includes the "# title" line
                return other["file"], False
            also_at.append(other["url"] or other["file"])
            os.remove(os.path.join(_dir(root, slug), "corpus", other["file"]))
    fm = {"title": title, "url": url, "publishedDate": date, "kind": kind, "source": source,
          "added": _now(), "also_at": json.dumps(also_at) if also_at else "", **(extra or {})}
    lines = ["---"] + [f"{k}: {_one_line(v)}" for k, v in fm.items() if v not in (None, "")] + ["---"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n# " + title + "\n\n" + text[:MAX_DOC_CHARS] + "\n")
    return name, created


def _same_title(root: str, slug: str, title: str, exclude: str) -> List[dict]:
    """Other documents with this exact (normalised) title. Their file names start with the
    title's slug, so only those few files are opened."""
    norm = slugify(title)
    if not norm:
        return []
    names = [os.path.basename(p) for p in glob.glob(os.path.join(_dir(root, slug), "corpus", f"*__{norm[:50]}_*.txt"))]
    return [d for d in _describe(root, slug, names)
            if d["file"] != exclude and d["source"] != "questionnaire" and slugify(d["title"]) == norm]


def list_docs(root: str, slug: str) -> List[dict]:
    cdir = os.path.join(_dir(root, slug), "corpus")
    if not os.path.isdir(cdir):
        return []
    return _describe(root, slug, sorted(n for n in os.listdir(cdir) if n.endswith(".txt")))


def _describe(root: str, slug: str, names: List[str]) -> List[dict]:
    cdir = os.path.join(_dir(root, slug), "corpus")
    out = []
    for name in names:
        with open(os.path.join(cdir, name), errors="replace") as f:
            fm, body = split_front_matter(f.read())
        out.append({"file": name, "kind": "other" if name.startswith("other__") else "research",
                    "title": fm.get("title") or name[:-4].split("__", 1)[-1].replace("_", " "),
                    "url": fm.get("url", ""), "date": (fm.get("publishedDate") or "")[:10],
                    "source": fm.get("source", "external"), "chars": len(body)})
    return out


def _doc_path(root: str, slug: str, name: str) -> str:
    if not DOC_RE.match(name or ""):
        raise StudioError(f"invalid document name {name!r}")
    path = os.path.join(_dir(root, slug), "corpus", name)
    if not os.path.exists(path):
        raise KeyError(name)
    return path


def read_doc(root: str, slug: str, name: str) -> dict:
    with open(_doc_path(root, slug, name), errors="replace") as f:
        fm, body = split_front_matter(f.read())
    return {"file": name, "front_matter": fm, "text": body}


@_locked
def delete_doc(root: str, slug: str, name: str) -> None:
    require_editable(root, slug)
    os.remove(_doc_path(root, slug, name))


# ---- consent (personal mode) -------------------------------------------------

def _consent_items() -> List[str]:
    return [line[6:] for line in trackp.CONSENT_TEMPLATE.splitlines() if line.startswith("- [ ] ")]


def consent_state(root: str, slug: str) -> List[dict]:
    path = os.path.join(_dir(root, slug), "CONSENT.md")
    text = open(path).read() if os.path.exists(path) else ""
    return [{"text": item, "ticked": f"- [x] {item}" in text} for item in _consent_items()]


@_locked
def write_consent(root: str, slug: str, ticked: List[bool]) -> List[dict]:
    meta = require_editable(root, slug)
    if meta["mode"] != "personal":
        raise StudioError("consent is collected for personal profiles only")
    items = _consent_items()
    if len(ticked) != len(items):
        raise StudioError(f"expected {len(items)} consent answers")
    form = trackp.CONSENT_TEMPLATE.format(name=meta["name"], slug=slug, date=datetime.date.today().isoformat())
    for item, t in zip(items, ticked):
        form = form.replace(f"- [ ] {item}", f"- [{'x' if t else ' '}] {item}")
    form = form.replace("Recorded by:", f"Recorded by: {meta['name']}, self-reported in Profile Studio, {_now()}")
    with open(os.path.join(_dir(root, slug), "CONSENT.md"), "w") as f:
        f.write(form)
    return consent_state(root, slug)


def consent_complete(root: str, slug: str) -> bool:
    state = consent_state(root, slug)
    return bool(state) and all(s["ticked"] for s in state)


# ---- open-ended questionnaire ------------------------------------------------

@_locked
def save_answers(root: str, slug: str, answers: Dict[str, str]) -> dict:
    """Store answers in studio.json and rewrite the questionnaire corpus documents
    (one per kind) so profile building reads them like any other writing."""
    meta = require_editable(root, slug)
    unknown = sorted(set(answers) - set(BY_ID))
    if unknown:
        raise StudioError(f"unknown questions: {unknown}")
    merged = {**meta.get("questionnaire", {}), **{k: (v or "").strip() for k, v in answers.items()}}
    merged = {k: v for k, v in merged.items() if v}
    cdir = os.path.join(_dir(root, slug), "corpus")
    for kind in KINDS:
        qa = [(q["text"], merged[q["id"]]) for q in QUESTIONS if q["kind"] == kind and q["id"] in merged]
        name = f"{kind}__{QUESTIONNAIRE_STEM}.txt"
        if qa:
            body = "\n\n".join(f"Q: {q}\nA: {a}" for q, a in qa)
            add_doc(root, slug, kind, f"{meta['name']}: questionnaire answers ({kind})", body,
                    source="questionnaire", stem=QUESTIONNAIRE_STEM)
        elif os.path.exists(os.path.join(cdir, name)):
            os.remove(os.path.join(cdir, name))
    return update_meta(root, slug, questionnaire=merged)


# ---- forced-choice trade-off items (personal track seed pairs) --------------------

@_locked
def ensure_seed_pairs(root: str, slug: str) -> int:
    """Write the personal track's trade-off items through trackp's own CLI, so the studio
    serves exactly the questionnaire WS B ships (its bank fixes the set). Existing pairs and
    answers are kept. Returns the number of pairs."""
    meta = require_editable(root, slug)
    if meta["mode"] != "personal":
        raise StudioError("trade-off items are for personal profiles")
    if not consent_complete(root, slug):
        raise StudioError("tick every consent box before answering trade-off items")
    try:
        trackp.main(["--root", root, "seed-pairs", "--researcher", slug])
    except SystemExit as e:   # trackp's CLI reports bad arguments or state by exiting
        raise StudioError(f"the personal track's seed-pairs command failed ({e.code}); "
                          "the studio's console has its message") from None
    return len(trackp._read(os.path.join(_dir(root, slug), trackp.SEED_PAIRS)))


def pending_choices(root: str, slug: str, limit: int = 0) -> dict:
    items = trackp.pending_items(root, slug, ("seed",))
    shown = items[:limit] if limit else items
    return {"n_pending": len(items), "items": [trackp.public(it) for it in shown]}


@_locked
def record_choice(root: str, slug: str, item_id: str, shown: int, reason: str = "") -> None:
    require_editable(root, slug)
    item = next((it for it in trackp.pending_items(root, slug, ("seed",)) if it["id"] == item_id), None)
    if item is None:
        raise StudioError(f"{item_id} is not pending (already answered or unknown)")
    trackp.record(root, slug, item, int(shown), reason.strip())


# ---- building the profile ------------------------------------------------------

def _doc_order(doc: dict) -> tuple:
    """Questionnaire answers first, then material the person added by hand, then dated
    publications newest first, then the rest."""
    src = doc["source"]
    rank = 0 if src == "questionnaire" else 1 if src in ("upload", "paste", "url") else 2 if doc["date"] else 3
    digits = doc["date"].replace("-", "")
    return (rank, -int(digits) if digits.isdigit() else 0, doc["file"])


def select_docs(root: str, slug: str, max_docs: int) -> List[dict]:
    docs = sorted(list_docs(root, slug), key=_doc_order)
    return docs[:max_docs] if max_docs else docs


STOP = set("""a an and are as at be by for from has have in into is it its of on or our that the their this to
we with using via towards toward can not do does how what when which who why new study analysis approach based
paper results result model models learning large language data""".split())


def _keywords(titles: List[str], k: int = 8) -> List[str]:
    grams = Counter()
    for t in titles:
        words = [w for w in re.findall(r"[a-z][a-z\-]+", t.lower()) if w not in STOP and len(w) > 2]
        grams.update(words)
        grams.update(f"{a} {b}" for a, b in zip(words, words[1:]))
    ranked = [g for g, c in grams.most_common(80) if c > 1 or " " in g]
    out = []
    for g in sorted(ranked, key=lambda g: (-grams[g] * (1.5 if " " in g else 1), g)):
        if not any(g in o or o in g for o in out):
            out.append(g)
        if len(out) == k:
            break
    return out


def summarize(meta: dict, docs: List[dict], doc_texts: List[str], llm: LLM) -> dict:
    """A short human-readable profile card: summary, interests, methods, open questions."""
    titles = [d["title"] for d in docs if d["source"] != "questionnaire"]
    if isinstance(llm, OfflineLLM):
        kw = _keywords(titles)
        return {"summary": (f"{meta['name']}: profile built offline from {len(docs)} documents. "
                            "Interests are the most frequent title phrases; run with a real model "
                            "for a written summary."),
                "interests": kw, "methods": [], "open_questions": [], "generated_by": llm.label}
    sample = "\n".join(f"- {t}" for t in titles[:80])
    qa = "\n\n".join(t[:3000] for d, t in zip(docs, doc_texts) if d["source"] == "questionnaire")
    prompt = ("Write a research profile of one researcher from the material below. Use only what the "
              "material supports. Return JSON {\"summary\": 2-3 sentences, \"interests\": [<=8 short "
              "topics], \"methods\": [<=6 short descriptions of how they tend to do research], "
              "\"open_questions\": [<=4 questions they seem to be pursuing]}.\n\n"
              f"Name: {meta['name']}\nAffiliation: {meta.get('affiliation') or 'unknown'}\n"
              f"Bio: {meta.get('bio') or 'none'}\n\nTitles of their work:\n{sample or 'none'}\n\n"
              f"Their own questionnaire answers:\n{qa or 'none'}")
    out = extract_json(llm.complete(prompt, temperature=0.0, max_tokens=1200)) or {}
    if not isinstance(out, dict):
        out = {}
    return {"summary": str(out.get("summary", "")), "interests": list(out.get("interests", []))[:8],
            "methods": list(out.get("methods", []))[:6], "open_questions": list(out.get("open_questions", []))[:4],
            "generated_by": llm.label}


MAX_PRINCIPLES = 10


def consolidate_principles(principles: List[str], llm: LLM, k: int = MAX_PRINCIPLES) -> List[str]:
    """Merge the per-document principles into at most k distinct ones.

    taste/extract.py returns up to six principles per document and drops only exact repeats,
    so a large corpus yields dozens of near-duplicates, and the loop puts every principle into
    the proposer prompt (ideas.taste_brief). One call merges them, using only the given rules;
    offline, or if the reply is unusable, the first k distinct ones are kept."""
    unique = list(dict.fromkeys(_one_line(p) for p in principles if _one_line(p)))
    if len(unique) <= k:
        return unique
    if isinstance(llm, OfflineLLM):
        return unique[:k]
    listing = "\n".join(f"- {p}" for p in unique)
    out = extract_json(llm.complete(
        f"These research principles were extracted, document by document, from one researcher's writing. "
        f"Many say the same thing. Merge them into at most {k} distinct principles. Keep the researcher's "
        "specific stance and concrete wording; order them by how often the idea recurs; do not add any idea "
        "that is not in the list. Return JSON {\"principles\": [short imperative rules]}.\n\n" + listing,
        temperature=0.0, max_tokens=1500))
    merged = out.get("principles") if isinstance(out, dict) else None
    if not isinstance(merged, list):
        return unique[:k]
    merged = [_one_line(p) for p in merged if isinstance(p, str) and _one_line(p)][:k]
    return merged or unique[:k]


def build_profile(root: str, slug: str, llm: LLM, max_docs: int = 40, log=print) -> dict:
    """Fit profile.json from the selected documents (taste/extract.profile_from_texts), plus
    any feature-vector choices in choices.jsonl, and write the summary card to studio.json."""
    meta = require_editable(root, slug)
    d = _dir(root, slug)
    docs = select_docs(root, slug, max_docs)
    if not docs:
        raise StudioError("add at least one document or questionnaire answer first")
    texts = []
    for doc in docs:
        with open(os.path.join(d, "corpus", doc["file"]), errors="replace") as f:
            texts.append(split_front_matter(f.read())[1])
    log(f"extracting taste from {len(docs)} documents with {llm.label}")
    prof = profile_from_texts(slug, [(doc["kind"], t) for doc, t in zip(docs, texts)], llm)
    cpath = os.path.join(d, "choices.jsonl")
    if os.path.exists(cpath):
        choices = load_choices(cpath)
        if choices:
            log(f"fitting {len(choices)} feature choices on top of the text prior")
            prof = fit_choice_model_cv(choices, slug, prof)
    raw_principles = list(prof.principles)
    if len(raw_principles) > MAX_PRINCIPLES:
        log(f"merging {len(raw_principles)} extracted principles into at most {MAX_PRINCIPLES}")
        prof.principles = consolidate_principles(raw_principles, llm)
    log("writing the profile summary")
    card = summarize(meta, docs, texts, llm)
    with _lock_for(root, slug), open(os.path.join(d, "profile.json"), "w") as f:
        f.write(prof.to_json())
    build = {"at": _now(), "llm": llm.label, "docs_used": len(docs), "docs_available": len(list_docs(root, slug)),
             "calls": llm.budget.calls, "cost_usd": round(llm.budget.cost_usd, 4), "edited": False,
             "principles_extracted": len(raw_principles)}
    update_meta(root, slug, summary=card, build=build, principles_raw=raw_principles)
    return {"profile": json.loads(prof.to_json()), "summary": card, "build": build}


@_locked
def save_edited_profile(root: str, slug: str, principles: List[str], weights: Dict[str, float]) -> dict:
    """The person's own corrections to the fitted profile. Marked in `sources` and the build
    log so a hand-edited profile is never mistaken for a purely fitted one."""
    meta = require_editable(root, slug)
    path = os.path.join(_dir(root, slug), "profile.json")
    if not os.path.exists(path):
        raise StudioError("build the profile before editing it")
    prof = TasteProfile.from_dict(_read_json(path, {}))
    bad = sorted(set(weights) - set(FEATURES))
    if bad:
        raise StudioError(f"unknown features: {bad}")
    prof.weights = {f: max(-1.0, min(1.0, float(weights.get(f, prof.weights.get(f, 0.0))))) for f in FEATURES}
    prof.principles = [_one_line(p) for p in principles if _one_line(p)]
    prof.sources["manual_edit"] = 1.0
    with open(path, "w") as f:
        f.write(prof.to_json())
    update_meta(root, slug, build={**(meta.get("build") or {}), "edited": True, "edited_at": _now()})
    return json.loads(prof.to_json())
