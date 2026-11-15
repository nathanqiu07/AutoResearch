# The public track: from a researcher's writing to preference pairs

How one researcher's public writing becomes binary preference pairs for the public track
(PLAN §6.3, §12.2), and how the pairs are checked before E2 uses them. Code names keep their
history (`track_s`, `timesplit`, `track_eval`); the design is in
`docs/superpowers/specs/2026-11-14-track-s-extraction-design.md`.

Each pair puts what the researcher did next to a plausible alternative he did not take. Every
"did" option is tied to a verbatim quote from his text, and every pair carries its source
document's date, so a cutoff T splits the pairs into history (fit) and held-out (test).

## 1. Pipeline and commands

Every stage reads only the files earlier stages wrote, appends as it goes, and skips work
already done, so any stage can be rerun or resumed after a crash. Paths are relative to
`data/researchers/<slug>/`. Exa responses are cached under `runs/track_s/cache/exa`, user-model
calls under `runs/track_s/cache/usermodel`. Claude stages use the `claude-cli` backend with
`claude-sonnet-5-5` by default, and `--max-usd` caps each stage's spend.

| Stage | Command | Writes |
|---|---|---|
| harvest | `python3 -m autoresearch.taste.timesplit harvest --researcher <slug> --name "<Full Name>" --start YYYY-MM-DD --end YYYY-MM-DD --lesswrong <lw slug> --feed <rss url>` | `corpus/*.txt`, `harvest_manifest.jsonl` |
| extract | `python3 -m autoresearch.taste.timesplit extract --researcher <slug>` | `extraction/exa.jsonl` |
| check | `python3 -m autoresearch.taste.timesplit check --researcher <slug> --max-usd 60` | `extraction/decisions.jsonl`, `rejected.jsonl`, `checked.jsonl` |
| distract | `python3 -m autoresearch.taste.timesplit distract --researcher <slug> --cutoff 2025-04-01 --max-usd 20` | `extraction/distractors.jsonl` |
| pairs | `python3 -m autoresearch.taste.timesplit pairs --researcher <slug> --cutoff 2025-04-01 --max-usd 20` | `pairs_timesplit.jsonl`, `history_timesplit.jsonl`, `heldout_timesplit.jsonl` |
| review (optional) | `python3 -m autoresearch.taste.timesplit review --researcher <slug>` | `review_timesplit.jsonl` |
| gate | `python3 -m autoresearch.taste.track_eval gate --researcher <slug> --max-usd 10` | `gate_timesplit.jsonl`; may rewrite the pairs files |
| agree | `python3 -m autoresearch.taste.track_eval agree --researcher <slug> --max-usd 15` | `agreement.jsonl` (run after the gate, since the gate can replace pairs) |
| select | `python3 -m autoresearch.taste.track_eval select --researcher <slug> --max-usd 40` | prints the chosen method and scores |
| e2 | `python3 -m autoresearch.taste.track_eval e2 --researcher <slug> --name "<Full Name>" --selected <m> --max-usd 40` | `results/track_s/E2_<slug>.json` |
| final | `python3 -m autoresearch.taste.track_eval final --researcher <slug> --selected <m> --max-usd 10` | `usermodel.json` |

Beforehand the researcher's directory needs `CONSENT.md` and a hand-written `identity.json` (section 7).

## 2. Harvest: finding his work

**Listings first.** The authoritative listings supply the URL, authors, date and title of
each item: his arXiv author query (`list_arxiv_author`, filtered to papers that list him),
every LessWrong post he wrote or co-wrote (`list_lesswrong_user`, via LessWrong's GraphQL
API), and his personal blog's RSS feed (`list_feed`). Exa search alone kept only 26 of his
documents, because LessWrong and GitHub results rarely carry an author field.

**Exa search adds.** On top of the listings, `scrape_exa` runs one Exa deep search with an
output schema plus four extra queries, then per-quarter searches restricted to each source's
domains (arXiv; LessWrong and the Alignment Forum; the Apollo blog; X; YouTube; GitHub) with
his surname as required text, then crawls the Apollo blog and research pages for subpages.

**Exa fetches every text,** up to 200k characters per document. Listed items are fetched by
their listed URL, because his blog serves only that form; when it differs from the canonical
URL it is kept as `fetched_url` in front matter, and extraction uses it.

**Authorship,** in order of trust: the listing's author list, then arXiv metadata, then Exa's
`author` field (split on `,`, `;` and ` and `), then a byline in the first 500 characters of
the text. A mention of his name elsewhere is not a byline. Items with none of these are dropped
as `no_author_evidence`; items whose authors do not include him as `not_author`. Author
position (`solo`, `first`, `middle`, `last`) is recorded.

**Date,** in order: listing date, arXiv v1 date, Exa's `publishedDate`, the first ISO date in
the opening 2,000 characters of text. The source is recorded as `date_source`. A document with
no date is excluded from both sides of the split, since it could postdate T.

**One work, one document.** arXiv abs/pdf/html variants and LessWrong/Alignment Forum copies
collapse by canonical URL. Copies of one work in different places (arXiv, LessWrong, a blog)
are merged by the clean title from his own listings (arXiv API, LessWrong GraphQL, blog RSS)
when one exists, not by Exa's page title, which can carry a site suffix such as
" - LessWrong". Titles of 12+ characters are compared after normalising. The earliest-dated copy
is kept (arXiv preferred on a tie) and the others go to the manifest as `crosspost_of`. This
keeps one piece of work from landing on both sides of T. One paper had straddled the old T:
"Constitutional Black-Box Monitoring for Scheming in LLM Agents", arXiv 2026-02-28 and
LessWrong 2026-03-03.

**Index pages are dropped** (`index_page`): a site root, `/blog`, `/research`, `/posts` or a
LessWrong user page is a listing, not a document, and its later titles would leak past T.

X posts, if found, are grouped into one `other__` file per month, dated by the month's last post.

## 3. Extraction: Exa's structured summaries

For each corpus document, `exa_extract` sends one `/contents` request with a `summary`
holding a query (`SUMMARY_QUERY`) and a JSON schema (`DECISION_SCHEMA`). It asks for every
research decision labelled D1 to D6 (which experiment to pursue, what evidence to collect,
whether to accept a result, whether to continue a line of work, how to read an ambiguous
result, how strongly to state a claim), each with the problem, what was done, alternatives the
text names, the stated reason, and a verbatim quote of 20 to 300 characters. It also asks for
future-work ideas; no later stage uses them now (section 6).

- **arXiv papers are summarised from `arxiv.org/html/<id>`, not the abstract page.** On the
  abstract page Exa summarises from the abstract alone: in a smoke test on his two longest
  papers one summary came back empty and the other said the decisions were "not stated in the
  provided highlights". The HTML page gave six decisions whose quotes are in the paper.
- **Per-URL statuses are recorded** as `exa_error`. `CRAWL_TIMEOUT` (HTTP 504) rows are
  dropped and retried on the next run, and the Exa client does not cache a response that
  contains a failed URL. A "success" status with an empty summary is recorded as
  `empty summary`; Exa gives no reason for these. A summary that is not JSON is kept with
  `summary is not JSON`. Documents with any `exa_error` are extracted by Claude alone.
- **Exa covers only a long document's opening.** In the smoke test every Exa quote fell in the
  first ~8k characters of the paper. So Exa's output is treated as candidates, and Claude reads
  the whole document in the next stage.

## 4. Claude check

`check_decisions` reads each document in chunks of 150k characters with a 2k overlap. For
every Exa candidate whose quote appears in the chunk, Claude (prompt `check-v1`) returns
`keep`, `correct` with fixed fields, or `drop`, and then lists decisions the candidates missed.
Nothing is sent back to Exa.

Code then verifies every kept, corrected and added quote against the full document text.
`normalize_for_quote` applies NFKC (which unfolds PDF ligatures), straightens curly quotes,
joins words hyphenated across line breaks, collapses whitespace and lowercases; the normalised
quote must be at least 20 characters and appear in the normalised text. Duplicate quotes
within a document are kept once.

| Outcome | Where | Tag or reason |
|---|---|---|
| Exa decision kept as written | `decisions.jsonl` | `exa_verified` |
| Exa decision fixed by Claude | `decisions.jsonl` | `exa_corrected` |
| Decision Exa missed, or any decision from a document Exa failed on | `decisions.jsonl` | `claude_fallback` |
| Quote not in the text | `rejected.jsonl` | `quote_not_found` |
| Claude dropped it | `rejected.jsonl` | `claude_drop` |
| Claude gave no verdict on it in any chunk | `rejected.jsonl` | `unchecked` |

Each kept decision gets `decision_id` = a hash of the document name and normalised quote, plus
the document's URL and date.

## 5. The time split

**T = 2025-04-01** (Ethan's call, 2026-11-14). The user model predicts with Sonnet 5.5, whose
training data runs to June 2026 (https://platform.claude.com/docs/en/about-claude/models/overview).
T started at 2026-03-01, that cutoff minus three months. After cross-posts were merged, that T
left 33 held-out decisions from 5 documents, under the floor in section 8 (at least 40 pairs
from at least 10 documents). At 2025-04-01 there are 96 held-out decisions from 14 documents.
The cost is contamination risk, which is why the contamination check in section 8 is required.

A pair is **history** when its source document is dated before T and **held-out** when it is
dated on or after T. All pairs from one document share its date, so a document never spans the
split. No post-T material reaches history:

- History pairs come only from documents dated strictly before T, and the `m1_docs` prompt arm
  and `profile_before` read only those documents (`docs_before`); undated documents are excluded.
- A history decision's contemporaneous-distractor search ends the day before T, and results
  without a date or dated after the window are discarded in code.
- A pair's context may not contain the title of any of his documents dated after the decision
  (`check_pair`).
- Each distractor records the cutoff it was chosen for, and `pairs` refuses distractors chosen
  for a different T; E2 reads T from the pairs rather than a flag.

Tests: `tests/test_timesplit.py` (`test_no_document_dated_on_or_after_cutoff_reaches_the_profile`,
`test_history_decision_never_sees_material_from_after_cutoff`, and others) and
`tests/test_track_eval.py` (`test_docs_arm_sees_no_document_from_after_cutoff`).

## 6. Distractors

`next_distractor` takes the first source that yields an alternative (`SOURCES`):

1. **named**: the first alternative the document itself names (`alternatives_named`) that
   differs from what was done. He considered it and chose otherwise.
2. **contemporaneous**: an Exa search with the decision's problem as query, 8 results, dated
   within six months either side of the document (ending the day before T for history
   decisions). The search leaves out `identity.json`'s `exclude_text` and `exclude_domains`, and
   code drops any result whose author or highlights still contain the excluded text, since Exa's
   text filters are approximate. Claude picks a result that took a different approach and
   states it in one sentence, or returns none.
3. **generated**: Claude writes a plausible alternative of the same scope. Backup only.

His own future-work ideas are not a source. He would pursue them, so as decoys they would
mislabel his preference (Ethan, 2026-11-15). Each distractor records its source, and E2 reports
accuracy by source.

## 7. Pair rendering

`render_pair` (prompt `pair-v2`) shows the rewriter the problem and the two options in a
seeded random order as Option 1 and Option 2, with no hint which was taken. The stated reason
is left out of the prompt because it would reveal which was taken. The rewriter writes a neutral third-person
context (the situation at the moment of decision; for D3, D5 and D6 the result being judged)
and restates both options in one fixed form: one imperative sentence, present tense, no first
person, no hedges, lengths within 20%, and paper-specific numbers or method names only if both
options carry the same kind.

`check_pair` rejects a pair when:

- the options differ in length by more than 20%;
- either option is more than one sentence (common abbreviations such as "e.g." excepted);
- digits appear in one option and not the other;
- either option uses we, our, us, I, my or me;
- the context or either option matches a banned name from `identity.json`;
- the context names one of his documents dated after this one.

A failing pair gets one rewrite with the problems listed; if it fails again it is dropped and
counted as `failed_checks`. The a/b order of the final pair is seeded per pair. `pairs` never
overwrites an existing `pairs_timesplit.jsonl`, so the held-out set cannot shift under a rerun.

**Anonymised Choice rows.** `history_timesplit.jsonl` and `heldout_timesplit.jsonl` hold WS A's
`Choice` rows, and every field can reach a user model's prompt, so none names him: `user_id` is
`"subject"`, `group_id` is a hash of the source URL (some URLs carry his name), and `reason` is
blanked when it matches a banned name. Pairs rejected in `review` are left out.

`identity.json` is written by hand per researcher. Marius Hobbhahn's:
`{"name": "Marius Hobbhahn", "banned": ["hobbhahn", "marius", "apollo"], "exclude_text": ["Hobbhahn"], "exclude_domains": ["apolloresearch.ai"]}`.

## 8. Validity checks

| Check | What it guards against | Rule |
|---|---|---|
| Distractor gate (`track_eval gate`) | Guessable pairs: the distractor is just a worse idea | A blind judge on a different model (default `claude-opus-5-5`) is asked which option is better research, in both orders. If it picks his option on more than 75% of held-out pairs, each flagged pair is rebuilt once with the next distractor source and judged again. Runs once per pair set. E2 reports accuracy with and without pairs still flagged. |
| Agreement filter (`track_eval agree`) | Pairs that test generic research sense, not his taste | A blind judge (`claude-sonnet-5-5`, no history) is asked which option is better research, in both orders. A pair is dropped from history **and** held-out when it gives his option more than 0.8 in both orders: every arm, m0 included, gets such a pair right, so it only adds noise. Pairs it confidently decides *against* him stay; they are where his taste shows. Its probability for his option in each order is recorded per pair in `agreement.jsonl`, so a new threshold needs no new calls. `select`, `e2` and `final` refuse a pair that was never judged. Same rule on the personal track (Ethan, 2026-11-14). |
| Style-leak probe (in the gate) | Wording that marks the real option | The same judge is asked which option was paraphrased from a published paper, scored over both orders (chance 0.5). Flagged when the low end of the document-clustered 90% interval is above 0.5. Report only; no pair changes. |
| Contamination (`m0_named` vs `m0`) | The predictor already knows his post-T work | E2 runs M0 twice, once told his name. The gap, with a document-resampled interval, is reported next to the result. |
| Document-clustered CIs | Pairs from one document are not independent | All intervals resample source documents (`group_id`), 2,000 draws, 90%. A pair counts as right only if the model picks his option in both a/b orders. |
| Held-out floor | Too few test items for a usable interval | At least 40 held-out pairs from at least 10 documents. Below that, move T back, delete `distractors.jsonl` and the pairs files, and rerun `distract` and `pairs`. Checked by hand; the code does not enforce it. |

E2's arms are `m0`, `m0_named`, `m1_pairs` (WS A's m1 on history pairs), `m1_docs` (pre-T
documents in the prompt, each given at most a quarter of 60k characters) and the method chosen
by `select` (m2 to m7 fit on the earliest 80% of history documents and scored on the rest).
Success: the selected method beats both m1 arms, each 90% interval above 0. The report also
splits accuracy by extraction tag, author position and distractor source.

## 9. Run record: Marius Hobbhahn

Consent is recorded in `data/researchers/marius_hobbhahn/CONSENT.md`; T = 2025-04-01.

| Stage | Result |
|---|---|
| harvest: candidates | 1,757 URLs from listings, Exa search and subpage crawls |
| harvest: kept | 105 documents, 2020 to 2026, all dated (103 by listing, 2 by Exa); merging cross-posts by listing title took the corpus from 127 to 105, 22 copies, each dated by its earliest copy |
| harvest: dropped | 910 `no_author_evidence`, 682 `not_author`, 58 `crosspost_of`, 2 `index_page` |
| harvest: sources | 61 LessWrong, 22 arXiv, 20 personal blog, 2 watcher.apolloresearch.ai; Exa found no X posts |
| harvest: by year | 2020: 6, 2021: 16, 2022: 33, 2023: 13, 2024: 15, 2025: 15, 2026: 7 |
| harvest: author position | 56 solo, 14 first, 14 middle, 21 last |
| harvest: split by date | 91 documents before T, 14 on or after T |
| harvest: arguments | TBD: `--start`, `--end`, `--lesswrong` and `--feed` values were not logged |
| extract | 68 documents with Exa decisions (343 decisions, 116 future-work ideas); 37 empty summaries; 0 crawl timeouts left (52 on the first pass, fixed by retry and `fetched_url`) |
| Exa spend so far | about $6 (harvest about $1.70) |
| check | 105 documents checked; 582 decisions (514 `claude_fallback`, 63 `exa_corrected`, 5 `exa_verified`); 273 rejected (183 `claude_drop`, 84 `unchecked`, 6 `quote_not_found`); Claude about $4.88 |
| distract | 582 distractors: named 445, contemporaneous 115, generated 22, none 0; Exa $0.96, Claude $1.59 |
| pairs | 456 pairs pass the wording checks (126 decisions failed them): 373 history, 83 held out from 14 documents; Claude $6.65; the choice files are anonymised (no hobbhahn, marius or apollo) |
| review | TBD: pairs reviewed, pairs rejected |
| gate | Opus 5.5 judge, threshold 0.75: 40 of 83 held-out pairs flagged; one rebuild round left 40 flagged. Style leak 0.63 (90% CI 0.53 to 0.74), flagged. Both are report-only; E2 reports accuracy with and without the flagged pairs. Claude $3.04 on the final pass |
| select | Not run for this researcher. Choosing among m2 to m7 is WS A's job; E2 uses the method WS A designates (pre-registration amended 2026-11-14, before the selected arm was scored) |
| E2 | pre-registered in `results/prereg/E2_S.json`, committed before held-out scoring. TBD: accuracy and 90% CI per arm, selected minus each m1 arm, contamination gap, success |
| final | TBD: `usermodel.json` saved, pushed or not |

The held-out side has 14 documents and 83 pairs, above the floor of 40 pairs from 10 documents.

## 10. Known limits

- **Form checks are regular expressions.** `check_pair` catches extra sentences, unmatched
  digits, first person and banned names, but not subtler differences in register or
  specificity. The style-leak probe is the check for those, and it only reports.
- **Exa summary coverage.** Exa's summaries cover a long document's opening, and 37 of 105
  documents came back empty with no reason given. Claude's check reads every document in
  full, so coverage rests on Claude there; the `claude_fallback` share shows how much.
- **Training cutoff.** Sonnet 5.5's training cutoff is June 2026, so with T = 2025-04-01 almost
  all held-out work predates the model's cutoff. The `m0_named` vs `m0` contamination gap
  measures how much that matters.
- **No X posts.** Exa found none, so the corpus has papers, forum posts and blog posts only.
- **One model family.** The gate and style judges are Claude models, like the pair writer and
  the predictor, since no other family is available. This replaces PLAN's 20-pair human check
  unless someone runs `review`.
- **Co-authored work** mixes his choices with his co-authors'. Author position is recorded and E2
  reports accuracy by it; no co-authored work is filtered out.
- **Consent scope.** `CONSENT.md` records Ethan's report of Marius's written consent and the
  scope as one session read it: committing his public texts, including X posts, to this private
  repository, and pushing a user model of him to past.dev. Ethan is to confirm that reading.
  If the scope is narrower, remove any `other__` corpus files and do not run
  `usermodel_store push`.
