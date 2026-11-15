"""Profile Studio: a local web UI for building a researcher profile the research loop can use.

Two ways in, both writing `data/researchers/<slug>/` in the layout the loop already reads
(taste/researcher.py, taste/trackp.py, research/advisor.load_user_model):

* personal: the person's own papers and writing (uploads, pasted text, links, their
  publication record), an open-ended questionnaire, and the personal track's forced-choice
  trade-off items (taste/trackp.py seed pairs), optionally fitted into usermodel.json;
* public: a well-known researcher's public record (Semantic Scholar, arXiv, web pages,
  LessWrong, an RSS feed, optionally an Exa harvest), with a disambiguation step.

Both end in profile.json (a TasteProfile), which `--researcher <slug>` picks up.

    python3 -m autoresearch.studio [--port 8765] [--root data/researchers]
"""
