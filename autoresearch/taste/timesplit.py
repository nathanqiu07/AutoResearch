"""Track S time split (PLAN 12.2): the profile is built only from documents
dated strictly before the cutoff T, so held-out pairs drawn from work after T
test prediction rather than recall.

Corpus files carry their date in front matter:

    ---
    publishedDate: 2024-05-01T00:00:00.000Z
    ---
    <text>

A file without a date is left out: it could have been written after T."""
from __future__ import annotations

import datetime
import glob
import os
import re
from typing import List, Optional, Tuple

from ..llm import LLM
from .extract import profile_from_texts
from .profile import TasteProfile
from .researcher import Researcher

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def read_doc(path: str) -> Tuple[Optional[datetime.date], str]:
    """(published date or None, body without front matter)."""
    with open(path) as f:
        raw = f.read()
    m = FRONT_MATTER.match(raw)
    if not m:
        return None, raw
    date = None
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "publishedDate" and value.strip():
            date = datetime.date.fromisoformat(value.strip()[:10])
    return date, raw[m.end():]


def docs_before(researcher: Researcher, cutoff: str) -> List[Tuple[str, str]]:
    """(kind, text) for every corpus document dated strictly before cutoff (YYYY-MM-DD)."""
    t = datetime.date.fromisoformat(cutoff)
    out = []
    for p in sorted(glob.glob(os.path.join(researcher.root, "corpus", "*.txt"))):
        date, text = read_doc(p)
        if date is not None and date < t:
            kind = "other" if os.path.basename(p).startswith("other__") else "research"
            out.append((kind, text))
    return out


def profile_before(researcher: Researcher, cutoff: str, llm: LLM) -> TasteProfile:
    return profile_from_texts(researcher.slug, docs_before(researcher, cutoff), llm)
