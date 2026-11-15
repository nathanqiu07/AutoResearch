# Profile Studio

A local web UI for building a researcher profile that the research loop uses through
`--researcher <id>`.

```bash
python3 -m autoresearch.studio            # http://127.0.0.1:8765, profiles in data/researchers/
python3 -m autoresearch.studio --root runs/studio-test --port 8766   # scratch directory
```

Standard library only, bound to 127.0.0.1. Code: `autoresearch/studio/` (`store.py` files and
profile building, `sources.py` public sources, `server.py` JSON API and jobs, `static/` the page).

Fonts load from Google Fonts (Caveat, IBM Plex Mono, Newsreader) and PDF reading from cdnjs; without
internet the page falls back to system fonts and only PDF upload is unavailable.

**Keys.** Home: <kbd>A</kbd> your own profile, <kbd>B</kbd> a known researcher. In the one-question-per-screen
flows (new profile, questionnaire, trade-offs): <kbd>Enter</kbd> continues, <kbd>Shift</kbd>+<kbd>Enter</kbd> is a new
line, letter keys pick an option, <kbd>↑</kbd>/<kbd>↓</kbd> move between questions.

## Two ways in

**Your own profile (personal).** About & consent → materials → questionnaire → trade-offs →
build & review → use in the loop.

* Materials: file uploads (PDF text is extracted in the browser with pdf.js from cdnjs; Markdown,
  LaTeX, text, HTML, BibTeX directly), pasted text, links, and your publication record
  (Semantic Scholar author pick and/or arXiv name match). Each item is `research` or `other`
  (non-research writing, weighted 0.4 by `taste/extract.py`).
* Questionnaire: 12 open questions (`studio/questionnaire.py`). Answers are saved as
  `corpus/{research,other}__studio_questionnaire.txt`, so they feed text extraction like any document.
* Trade-offs: the personal track's trade-off questionnaire (its bank fixes the set). The studio
  calls `trackp seed-pairs`, `pending_items`
  and `record`, so answers land in `seed_choices.jsonl` exactly as from the terminal or chat, and
  follow the same consent gate (`CONSENT.md`). The studio never writes `tracks.json`: making
  someone the team's personal track (key P) stays a deliberate `trackp init`.
* Optional user model: fits a WS A method on those answers via `trackp.fit_user_model` and
  writes `usermodel.json`.

**A known researcher (public).** Search by name → pick among same-named Semantic Scholar authors
(affiliation, counts, top papers) → gather sources → review the corpus → build → use.

* Sources: Semantic Scholar papers with abstracts, arXiv (kept only when the name is in the author
  list), a Wikipedia bio (card only, never taste evidence), a LessWrong username, an RSS feed, extra
  URLs, and an optional paid Exa harvest (`taste/scrape.scrape_exa`, needs `EXA_API_KEY`).
* One work found twice (an arXiv paper cross-posted to LessWrong) is kept once, with the fuller
  text, and the other URL is recorded as `also_at`.

## What it writes

In `data/researchers/<id>/`: `corpus/*.txt` (front matter as in `taste/scrape._write_doc`),
`profile.json` (a `TasteProfile`), `studio.json` (name, bio, questionnaire answers, summary card,
build log), and in personal mode `CONSENT.md`, `seed_pairs.jsonl`, `seed_choices.jsonl` and
optionally `usermodel.json` / `history.jsonl`.

The loop loads `usermodel.json` when present (all decision points), otherwise `profile.json`
(D1 only; `research/advisor.load_user_model`). Hand edits to principles or weights are marked
with `sources.manual_edit` and `build.edited` so an edited profile is never taken for a fitted one.

Directories not made in the studio (no `studio.json`) are shown read-only and never written.

## Cost

Building with `offline` makes no model calls (keyword lexicon; for trying the flow only). With
`anthropic` or `claude-cli` it makes one call per document read, one to merge the extracted
principles into at most 10 (the loop puts every principle into the proposer prompt; the raw list
stays in `studio.json`), and one for the summary card. A 15-document build with Sonnet via
`claude-cli` took about a minute and $0.29. The
page states the count and asks before starting. Fitting a user model and the Exa harvest are paid
too and ask first.
