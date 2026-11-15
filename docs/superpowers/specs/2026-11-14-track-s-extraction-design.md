# Track S: Marius Hobbhahn's research taste as binary preference data

Status: draft for Ethan's approval (2026-11-14), workstream B, covering board tasks `real-researcher`
and `exa-live-run`, and extending `timesplit-builder` (claimed under this checkout's agent name, `ethan-c`).

## Intent

PLAN §6.3 and §12.2 call for a Track S user model built from one public researcher's dated
writing. Ethan chose Marius Hobbhahn (Apollo Research). Ethan reports that Marius's written consent was received and covers these uses; it is recorded in `CONSENT.md` (see Constraints). WS A's
user-model methods fit and predict only on **binary pairs**: `Choice` requires `chosen` to be
`"a"` or `"b"` (`autoresearch/taste/usermodel.py:21`). So everything we scrape has to become
pairs of the form "what he actually did" vs "a plausible alternative he didn't take", each with a
date, so that a time split can test the model on work published after a cutoff T.

Ethan asked for three things:
* Make maximum use of Exa's features.
* Exa extracts decisions first; Claude checks each one and fills in where Exa fails.
* Document how the extraction is done.

## Goals

1. A dated corpus of his own work (papers, posts, blog, talks, X) in `data/researchers/marius_hobbhahn/`.
2. Pairs extracted from that corpus, each traceable to a quote from his text, mapped to the
   loop's decision points D1–D6.
3. A time split: history pairs before T, held-out pairs after T. A test proves no post-T material
   reaches the history.
4. E2 for Track S: M0, two raw-history baselines and the selected method on the held-out pairs, plus the quality checks
   below that tell us whether the accuracy number means anything.
5. A saved `usermodel.json` pushed to shared memory for the R1-S arm of E4.
6. `docs/track-s-extraction.md`: how the extraction works, with the counts from the real run.

## Non-goals

* Track P, the combined P+S track, and changes to WS A's methods.
* Editing files locked by other agents. WS A owns `taste/usermodel.py`, `taste/__main__.py` and
  `taste/methods/`; WS D owns `research/advisor.py`. We use their public interfaces only.

## Anti-goals (it fails even if it runs)

* **Guessable pairs:** a model that knows nothing about him picks his option most of the time
  because the distractor is just a worse idea. Then E2 measures research common sense, not his taste.
* **Contamination:** the predicting model already saw his post-T work in training and remembers it.
* **Leakage:** any post-T document reaches the history or the prompt arm, or a pair's context
  states what he chose or anything learned after that decision.
* **Invented decisions:** a pair whose "what he did" has no supporting quote in his text.

## Constraints

* Standard library only in `autoresearch/` (AGENTS.md §3). Exa is called over HTTP with
  `urllib`, as `integrations/exa.py` already does; no `exa-py`.
* Keys come only from env vars. `EXA_API_KEY` isn't yet visible to this machine's agent shell;
  Ethan will add it to `~/.zshrc`. The Claude steps use the `claude-cli` backend (no
  `ANTHROPIC_API_KEY`) through `llm.Budget`, which caps spend.
* Ethan approved real model calls (2026-11-14), with a **$200 ceiling** for the whole job: Exa,
  the Claude stages and E2 together. Each stage's `Budget` is set from what is left. Post on the
  board when the live run starts and ends (AGENTS.md rule 5).
* Consent: Ethan reported in the Claude Code session on 2026-11-14 that Marius gave written
  consent covering this work: committing his texts, including X posts, to this private repo, and
  pushing a model of him to past.dev. `CONSENT.md` records that report, its date and that scope.
* The repo is private, so the corpus text is committed. `history_text` and other workers need it.

## Approaches considered

| | Who extracts decisions | Trade-off |
|---|---|---|
| A | Exa's structured summaries only | Most Exa, cheapest; Exa's model and prompt are hidden, so the step can't be documented, reproduced, or checked for made-up decisions |
| B | Exa retrieves, Claude extracts | Fully documented and reproducible; makes no use of Exa's extraction |
| **C (chosen)** | Exa extracts, Claude checks and falls back | Most Exa, and every pair is tied to a quote; costs the most |

Ethan chose C, with this rule: **nothing is sent back to Exa.** Claude keeps, corrects or drops
each Exa decision and adds the ones Exa missed. Fallback pairs are used in training and tagged
with their origin. Re-asking Exa would just re-roll a model we can't see, and would make the
two extractions stop being independent. The one exception is retrieval: if Exa's text for a
document is cut off, its full text is fetched again.

## The pipeline

Six stages. Each writes a file, and later stages read only those files, so any stage can be
rerun alone. Exa and Claude responses are cached under `runs/track_s/cache/`, so a rerun
doesn't pay twice.

### 1. Harvest (Exa)

**Enumerate his output.** A **deep search** with an `outputSchema` returns a list of items
`{title, url, date, kind}`. It runs alongside ordinary searches, each restricted by:
* `category`: research paper, pdf, tweet, github, news;
* `includeDomains`: arxiv.org, lesswrong.com, alignmentforum.org, apolloresearch.ai, x.com,
  youtube.com, github.com;
* `includeText` "Hobbhahn".

Searches run per date window, using `startPublishedDate`/`endPublishedDate` quarter by quarter,
to get past the per-query result cap. **Subpage crawling** of apolloresearch.ai's blog and
research pages picks up items search misses. The union is deduplicated by canonical URL:
arXiv abs/pdf/html variants become one item, and LessWrong/Alignment Forum crossposts become one.

**Keep only his own work.** Exa's `author` field is compared with a second source:
* arXiv items against arXiv's free metadata API, which gives the author list, his position and the v1 date;
* LessWrong/Alignment Forum and the blog against the byline in the page text.

Pages that only mention him are dropped.

**Full text and dates.** Contents use `text` (full markdown) with live crawl as a fallback. The date is taken in this order:
1. arXiv v1 submission date;
2. Exa's `publishedDate`;
3. a date in the page text.

Each file records which source the date came from. Items without a date are kept out of
the time split entirely, on both sides.

**X posts** are grouped into one document per month (`kind: tweet`), dated by the month's last
post. Single posts are too short to carry a decision.

**Output.** `corpus/research__<slug>.txt` or `corpus/other__<slug>.txt` (`.txt`, because
`Researcher.docs` and `history_text` glob for it), each starting with a front-matter block:
`url, title, publishedDate, date_source, authors, author_position, kind, exa_request_id`.
The date key is `publishedDate` because the existing `taste/timesplit.read_doc` reads it. Plus
`harvest_manifest.jsonl`: one line per kept or dropped item, with the reason.

### 2. Extract (Exa structured summary)

For each document, a contents request with `summary: {query, schema}` asks Exa's model for:

```json
{"decisions": [{"point": "D1..D6", "problem": "...", "did": "...",
                "alternatives_named": ["..."], "stated_reason": "...", "quote": "..."}],
 "future_work": [{"idea": "...", "quote": "..."}]}
```

D1–D6 are explained in the query using `research/decisions.py`'s own wording, mapped to research
in general:
* D1 which experiment or hypothesis to pursue;
* D2 what evidence to collect, for example asking the model directly vs using probes;
* D3 whether to accept a result;
* D4 whether to continue or drop a line of work;
* D5 how to interpret an ambiguous result;
* D6 how strongly to state a claim.

Before the full run, a smoke test on two of his longest papers checks whether the summary
covers the whole document. If it is cut off, the Claude stage reads the rest (stage 3), and the
extraction doc reports that.

Output: `extraction/exa.jsonl`, the raw response per document.

### 3. Check and fallback (Claude)

Claude gets the document's full text and Exa's decisions. Documents longer than about 150k
characters go in chunks with a 2k-character overlap. For each Exa decision Claude returns
`keep`, `correct` (with the fixed fields) or `drop`, and then lists any decisions Exa missed.

Every kept, corrected or added decision needs a verbatim quote. **Code checks the quote**: after
normalizing whitespace and quote marks, it must appear in the document text. A quote that
isn't found drops the decision.

Each decision is tagged:
* `exa_verified`: Exa's decision, confirmed;
* `exa_corrected`: Exa's decision, fixed by Claude;
* `claude_fallback`: a decision Exa missed.

Dropped decisions go to `extraction/rejected.jsonl` with the reason. Output:
`extraction/decisions.jsonl`.

### 4. Distractors

For each decision, take the first source that gives a usable alternative. The source is recorded on the pair.

1. **Named in the same document** (`alternatives_named`): he considered it and chose otherwise.
2. **His own unpursued future work**, from earlier documents. "Unpursued" is judged by Claude
   against his later documents. An Exa search restricted to his work (`includeText` "Hobbhahn",
   dated after the idea) finds candidates for that check.
3. **What other groups did on the same problem at the same time.** An Exa search with the
   decision's problem as the query, dated within ±6 months of his document, excluding text
   "Hobbhahn" and the domain apolloresearch.ai. Claude turns the approach it finds into an option.
4. **Claude-generated alternative**: the last resort.

### 5. Write the pairs

Claude rewrites the two options as neutral plans:
* same register, length within ±20% of each other;
* no names, labs or results, only what was planned, as of the document's date;
* so the original's wording can't give away which option is his.

The context is written as of the decision: the problem, the titles of his earlier documents, and
whatever he knew when he decided. For D3, D5 and D6 that includes the result he was judging or
interpreting. It never names him, never states what he chose, and never states anything learned
after the decision.

Code checks every pair:
* length ratio;
* neither "Hobbhahn" nor "Apollo" appears;
* the context names no title dated after the document;
* a/b order comes from a seeded RNG.

All pairs go in `pairs.jsonl`, never `choices.jsonl`: `Researcher.build_profile` reads
`choices.jsonl` as feature vectors and would crash the loop on text rows. Each pair is a `Choice`:
* `user_id` is `marius_hobbhahn`, `source` is `timesplit`, `decision_point` is D1–D6, and `timestamp` is the document date;
* `group_id` is the document URL, and `reason` is his stated reason;
* `example_id` is a hash.

The extraction tag and the distractor source go in a side file keyed by `example_id`
(`pairs_meta.jsonl`), because `Choice` has no free field for them.

### 6. Time split and fit

* **T** is set a little before the training cutoff of the model the user model predicts with
  (Sonnet 5.5, E4's default judge): **cutoff minus 3 months** (Ethan's call). That trades a
  small contamination risk for more held-out pairs, so the contamination check below is required,
  not optional. T is set on the command line, and the value used is written into every output.
* Each row of `pairs.jsonl` carries `split: history|heldout`; `heldout_timesplit.jsonl` is written
  from the held-out rows, as PLAN §12.2 names it.
  Everything from one document stays on one side.
* A **leakage test** asserts that no history pair, and no corpus file used for the E2 fit or the
  prompt arm, is dated on or after T.
* **E2 vs E4.** For E2, the model is fit on pre-T pairs only, and the prompt arm sees only pre-T
  documents. After E2, the final `usermodel.json` used in E4 is fit on all pairs. It is
  saved and pushed with `usermodel_store push`. For E4's R1-S-prompt arm to see the same pairs,
  `history_text` (WS D) must read `pairs.jsonl`; that request goes on the board, not into this diff.
* `timesplit.py` is extended, not replaced: `docs_before` and `profile_before` keep their signatures.

## Measuring it (E2 for Track S)

**Arms.**
* M0, the generic judge, run twice: with no name, and told "this is Marius Hobbhahn".
* Two raw-history baselines: **M1-pairs** (WS A's `m1` with his pre-T pairs) and **M1-docs** (his
  pre-T documents in the prompt, built with `docs_before`, since `history_text` reads every file).
* WS A's selected method. If WS A hasn't selected one yet, choose among m2–m7 on a validation set made of
  the latest 20% of pre-T history pairs by date. The held-out set is used once.

**Protocol.** Each held-out pair is asked in both orders (as `tastebench.py` does). A pair counts
as correct when both orders are right. Bootstrap over source documents (`group_id`) for 90% CIs.

**Success** (PLAN §9, E2): the selected method beats **both** M1 baselines, with each CI excluding 0. The result
counts only alongside these checks:
* **Distractor quality:** name-free M0 accuracy, and a blind "which is better research?" judge
  run with a different Claude model. **Gate before pre-registration:** if the judge picks his
  option on more than 75% of held-out pairs, each pair it flags gets one new distractor from
  the next source in stage 4 and is judged again. Accuracy is then reported with and without the
  pairs still flagged. This replaces PLAN's 20-pair human
  check; no other model family is available (no `OPENAI_API_KEY`). It is a departure from the plan.
* **Contamination:** named M0 minus name-free M0. A clear gap means the model recognizes his work.
* **Extraction quality:** counts by tag (verified, corrected, fallback, rejected), and accuracy split by tag.

Results go in `results/track_s/E2_marius_hobbhahn.json`, with `CODE_VERSION`, T, model ids, n and costs.
`results/prereg/E2_S.json` is committed before the paid E2 run.

## Code layout

| File | What | Owner |
|---|---|---|
| `autoresearch/integrations/exa.py` | `ExaClient.search` gains optional date-range, domain, text, category, deep/`outputSchema` and contents (`text`, `summary`, `subpages`, live crawl) arguments; existing calls unchanged | shared: post the change |
| `autoresearch/taste/scrape.py` | `scrape_exa(...)` harvest; arXiv metadata lookup | WS B |
| `autoresearch/taste/timesplit.py` (exists; extend) | stages 2–6 and the CLI `python3 -m autoresearch.taste.timesplit harvest|extract|check|distract|pairs|split` | WS B (ethan-c lock) |
| `autoresearch/taste/track_eval.py` | `choices.jsonl` → `Choice` loader, E2 arms, paired-order scoring, checks; CLI `eval` | WS B, new |
| `tests/test_timesplit.py` (exists; extend), `tests/test_track_eval.py` (new) | leakage, quote check, pair checks, loader, scoring; fake Exa and LLM | WS B |
| `docs/track-s-extraction.md` | how extraction works, with real counts | WS B, new |
| `data/researchers/marius_hobbhahn/` | corpus, manifests, extraction files, pairs, `CONSENT.md`, `usermodel.json` | WS B |

## Cost

* **Exa:** searches, contents and summaries. Expected under $15.
* **Claude, via the CLI on Ethan's plan:** one check per document plus pair writing and the E2 arms. Roughly 150
  documents at ~30k tokens each for the check stage.
* Hard ceiling: $200 for everything (Ethan, 2026-11-14).

`Budget` caps each stage. The live harvest runs first and reports counts and cost before the
Claude stages start. That report is informational, not a stop: Ethan approved the spend. The run
stops only when the ceiling would be crossed.

## Calls made without Ethan (check these)

* Two raw-history baselines, and success requires beating both.
* Pair contexts may include the result he was judging (D3, D5, D6), never his choice.
* Pairs live in `pairs.jsonl`; WS A/D are asked on the board to read it.
* The 75% distractor gate with one regeneration round.
* T is three months before Sonnet 5.5's cutoff, moved earlier again below 40 held-out pairs from 10 documents.
* The consent scope in Constraints is Claude's reading of "consent covers written on CLI".

## Left to the builder

* Exact Exa queries, window sizes and numeric caps; chunk sizes.
* Prompt wording, kept in versioned constants that are quoted in the extraction doc.
* How to look up the predictor model's training cutoff for T's default.

## Known risks

* **Small held-out set:** even with T three months before the predictor's cutoff, the held-out
  set may be small and the CIs wide. If it has fewer than 40 pairs from at least 10 documents,
  move T earlier again and report the contamination check next to the result.
* **Prompt-arm truncation:** `history_text` (WS D) truncates to 8,000 characters, so the prompt arm sees only the
  start of his history. Flag this to WS D; don't change it here.
* **Mixed authorship:** co-authored papers mix his taste with others'. Author position is recorded and
  accuracy is reported split by it, without filtering.
