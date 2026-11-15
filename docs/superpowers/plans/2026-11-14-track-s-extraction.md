# Track S Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Marius Hobbhahn's dated public writing into quote-backed binary preference pairs, split them by date, run E2 for Track S, and save the user model for E4.

**Architecture:** Six file-to-file stages: harvest, Exa extraction, Claude check and fallback, distractors, pair writing with the time split, and evaluation. Each stage reads only the previous stages' files under `data/researchers/marius_hobbhahn/`, so any stage can be rerun alone. Exa and Claude responses are cached under `runs/track_s/cache/`. This plan extends the existing `autoresearch/taste/timesplit.py` (commits 62056bd, fbf776f) rather than replacing it.

**Tech Stack:** Python 3.9+, standard library only in `autoresearch/`; Exa over HTTP through `integrations/http.post_json`; Claude through `llm.get_llm("claude-cli", ...)`; `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-14-track-s-extraction-design.md`

## Global Constraints

- Standard library only in `autoresearch/`; no `exa-py`.
- Keys only from env vars (`EXA_API_KEY`); never read, print or commit them.
- No machine-specific paths in code.
- $200 ceiling for the whole job (Exa + Claude stages + E2). Every Claude stage runs under a `llm.Budget` whose `max_cost_usd` is the remaining amount; Exa spend is read from `ExaClient.cost`.
- File names follow what `timesplit.py` already uses: `pairs_timesplit.jsonl`, `review_timesplit.jsonl`, `history_timesplit.jsonl`, `heldout_timesplit.jsonl`. Never write `choices.jsonl` (the feature-vector loader would crash on text rows). This replaces the spec's `pairs.jsonl`; Task 9 updates the spec to match.
- Front-matter date key is `publishedDate` (read by `timesplit.read_doc`).
- No pair context or option contains "Hobbhahn", "Marius" or "Apollo" (case-insensitive).
- T = Sonnet 5.5's training cutoff minus 3 months; below 40 held-out pairs from at least 10 documents, move T earlier and say so in the results.
- Before every push: `git pull --rebase`, then `python3 -m unittest discover -s tests -t .` passes. Stage files by name. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Lock each path with `python3 scripts/agentctl.py lock <path> --reason "real-researcher: <what>"` before its first edit. `timesplit.py` and `tests/test_timesplit.py` are already locked under this checkout's agent name.

## Review Focus

1. An Exa result with no `author` field and no byline in its text: treated as not his and dropped with reason `no_author_evidence`, never a crash. Test in Task 2.
2. Exa's summary comes back as non-JSON or missing `decisions`: the row is stored with `exa_error`, and Task 4 extracts everything as `claude_fallback`. Tests in Tasks 3 and 4.
3. A quote copied from a PDF with curly quotes, ligatures (`ﬁ`) or a hyphenated line break: it still matches the text after normalization. Test in Task 4.
4. A rerun after a crash or a 429 halfway through a stage: finished documents are skipped, nothing is duplicated, and the Exa cache is reused. Tests in Tasks 3 and 4.
5. A document longer than the chunk size whose only decision sits past the first chunk: it is found and its quote verified. Test in Task 4.

---

### Task 1: Exa client options

**Files:**
- Modify: `autoresearch/integrations/exa.py` (`ExaClient.search`, `ExaClient.contents`; add `ExaClient.deep`)
- Test: `tests/test_exa_client.py` (new)

**Interfaces:**
- Produces (field names checked against `https://exa.ai/docs/exa-spec.yaml` on 2026-11-14):
  - `ExaClient.search(query, num_results=5, since_days=None, highlights_query=None, category=None, text_chars=0, *, start_date=None, end_date=None, include_domains=None, exclude_domains=None, include_text=None, exclude_text=None, search_type="auto", summary=None, max_age_hours=None) -> List[dict]`
  - `ExaClient.contents(urls, text_chars=4000, *, summary=None, max_age_hours=None, subpages=0, subpage_target=None) -> List[dict]`
  - `ExaClient.deep(query, output_schema: dict, *, additional_queries=None, system_prompt=None, num_results=25, start_date=None, end_date=None, include_domains=None) -> dict`: the whole response. The structured result is at `response["output"]["content"]`, and its citations are at `response["output"]["grounding"]`.
  - `summary` is `{"query": str, "schema": dict}`. Dates are `YYYY-MM-DD` strings, sent as `YYYY-MM-DDT00:00:00Z`.
  - Spec facts that shape later tasks:
    - `includeText`/`excludeText` are deprecated, and their matching is approximate. Send them, but never rely on them: Tasks 2 and 5 check authorship and exclusion in code.
    - `livecrawl` is deprecated in favour of `maxAgeHours`.
    - Subpage crawling lives on `/contents`, not `/search`.
    - `/findSimilar` is deprecated in favour of `/search` with a descriptive query.
    - The category enum is `company, publication, news, personal site, financial report, people`. Other strings are accepted only as hints, so papers use `publication`.

- [x] **Step 1: Check the field names against Exa's spec.** Done on 2026-11-14; the results are in the Produces block above.

- [ ] **Step 2: Write the failing tests** in `tests/test_exa_client.py`. Patch `autoresearch.integrations.exa.post_json` with a recorder that returns `{"results": [], "costDollars": {"total": 0.01}}`.
  - `test_existing_search_call_sends_the_same_body_as_before`: `search("q", num_results=5, since_days=None, highlights_query=None)` sends exactly `{"query": "q", "type": "auto", "numResults": 5, "contents": {"highlights": {"query": "q", "maxCharacters": 800}}}`. This keeps existing cache keys valid.
  - `test_date_and_domain_filters_reach_the_body`: `start_date="2025-01-01", end_date="2025-03-31", include_domains=["arxiv.org"], exclude_text=["Hobbhahn"]` → `startPublishedDate == "2025-01-01T00:00:00Z"`, `endPublishedDate == "2025-03-31T00:00:00Z"`, `includeDomains == ["arxiv.org"]`, `excludeText == ["Hobbhahn"]`.
  - `test_contents_sends_summary_schema_and_subpages_at_top_level`: `contents(["u"], summary={...}, subpages=5, subpage_target=["blog"], max_age_hours=0)` → body has `urls`, `summary`, `subpages`, `subpageTarget`, `maxAgeHours` at the top level.
  - `test_deep_search_sends_output_schema_and_type_deep`.
  - `test_cost_is_summed_across_calls`: two calls → `client.cost == 0.02`.

- [ ] **Step 3: Run them to see them fail.** Run: `python3 -m unittest tests.test_exa_client -v`. Expected: FAIL (unexpected keyword arguments / missing `deep`).

- [ ] **Step 4: Implement the three methods.** Add each optional key to the body only when it is set, so old calls keep their bodies.

- [ ] **Step 5: Run the full suite.** Run: `python3 -m unittest discover -s tests -t .`. Expected: OK.

- [ ] **Step 6: Commit and tell the board.** Commit `autoresearch/integrations/exa.py tests/test_exa_client.py`. Then `python3 scripts/agentctl.py post "ExaClient: new optional search/contents args and deep()" "<one line per new argument; existing calls unchanged>" --to all --task real-researcher`.

### Task 2: Harvest his dated work

**Files:**
- Modify: `autoresearch/taste/scrape.py`
- Modify: `autoresearch/cli.py` (the `scrape` subcommand gains `--exa`, `--start`, `--end`)
- Test: `tests/test_scrape_exa.py` (new)

**Interfaces:**
- Consumes: Task 1's `ExaClient.search/contents/deep`.
- Produces:
  - `canonical_url(url: str) -> str`: arXiv abs/pdf/html and version suffixes → `https://arxiv.org/abs/<id>`; `alignmentforum.org/posts/<id>/...` and `lesswrong.com/posts/<id>/...` → `https://www.lesswrong.com/posts/<id>`; trailing slashes, `www.` and query strings dropped otherwise.
  - `fetch_arxiv_meta(arxiv_ids: List[str]) -> Dict[str, dict]` → `{id: {"authors": [str], "published": "YYYY-MM-DD"}}` from `export.arxiv.org/api/query?id_list=` (v1 date).
  - `author_position(authors: List[str], name: str) -> Optional[str]`: `"first" | "last" | "middle" | "solo"`, or `None` if he isn't listed. Matching is by surname "Hobbhahn" plus the first initial "M".
  - `scrape_exa(name: str, root: str, client: ExaClient, start: str, end: str, window_months: int = 3, arxiv_meta: Callable = fetch_arxiv_meta) -> dict`: writes the corpus files and `harvest_manifest.jsonl`; returns `{"kept": int, "dropped": {reason: int}, "exa_cost": float}`.
  - Corpus file front matter keys, in order: `url, title, publishedDate, date_source, authors, author_position, kind, exa_request_id`. `date_source` is one of `arxiv_v1 | exa | text | none`. `kind` is `paper | post | blog | talk | tweet_month | code`. File prefix is `research__` except `tweet_month`, which is `other__`.

- [ ] **Step 1: Write the failing tests** with a fake client. Each test is one behavior:
  - `test_arxiv_variants_collapse_to_one_document`: `/abs/2505.23836`, `/pdf/2505.23836v2` and `/html/2505.23836v1` → one corpus file.
  - `test_lesswrong_and_alignment_forum_crosspost_is_one_document`.
  - `test_page_that_only_mentions_him_is_dropped`: author `"Jane Doe"`, his name only in the body → dropped, manifest reason `not_author`.
  - `test_result_without_author_or_byline_is_dropped_not_crashed` (Review Focus 1): reason `no_author_evidence`.
  - `test_arxiv_v1_date_beats_exa_date`: Exa says 2025-06-10, arXiv meta says 2025-05-28 → `publishedDate: 2025-05-28`, `date_source: arxiv_v1`.
  - `test_undated_item_is_saved_without_publishedDate`: `timesplit.read_doc` returns `None` for its date.
  - `test_tweets_are_grouped_by_month_into_other_files`: three posts in 2025-04 → one `other__` file dated with the month's last post.
  - `test_search_windows_cover_the_whole_range`: `start="2024-01-01", end="2024-12-31", window_months=3` → the recorded searches carry four non-overlapping date windows.

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m unittest tests.test_scrape_exa -v`. Expected: FAIL (`scrape_exa` not defined).

- [ ] **Step 3: Implement.** Enumerate with `deep` (output schema: a list of `{title, url, date, kind}`) plus `search` per window × each `(category, include_domains)` pair below, every call with `include_text=["Hobbhahn"]` and "Marius Hobbhahn" in the query. Also call `contents(["https://www.apolloresearch.ai/blog", "https://www.apolloresearch.ai/research"], subpages=25, subpage_target=["blog", "research"])` to pick up posts search misses. Pairs: `("publication", ["arxiv.org"])`, `(None, ["lesswrong.com", "alignmentforum.org"])`, `(None, ["apolloresearch.ai"])`, `(None, ["x.com", "twitter.com"])`, `(None, ["youtube.com"])`, `(None, ["github.com"])`. Then `contents(urls, text_chars=200_000)` for the kept URLs (cached pages are fine; his past writing doesn't change). Date precedence: arXiv v1 > Exa `publishedDate` > a `YYYY-MM-DD` found in the first 2,000 characters > none.

- [ ] **Step 4: Run the full suite.** Expected: OK.

- [ ] **Step 5: Commit** `autoresearch/taste/scrape.py autoresearch/cli.py tests/test_scrape_exa.py`.

### Task 3: Exa structured extraction

**Files:**
- Modify: `autoresearch/taste/timesplit.py`
- Test: `tests/test_timesplit.py` (new class `ExaExtractTest`)

**Interfaces:**
- Consumes: Task 1's `contents(..., summary=...)`; Task 2's front matter (`url`).
- Produces:
  - Constants `DECISION_SCHEMA: dict` and `SUMMARY_QUERY: str`. The schema matches the spec's §2 JSON exactly: `decisions[{point, problem, did, alternatives_named, stated_reason, quote}]` and `future_work[{idea, quote}]`. The query defines D1–D6 with the spec's wording.
  - `exa_extract(researcher: Researcher, client: ExaClient) -> dict` appends one row per corpus document to `extraction/exa.jsonl`: `{"doc": <file name>, "url": str, "decisions": [...], "future_work": [...], "exa_error": Optional[str], "request_id": str}`. It returns `{"done": int, "skipped_existing": int, "errors": int}`.

- [ ] **Step 1: Write the failing tests:**
  - `test_one_row_per_document_with_a_url`.
  - `test_unparseable_summary_is_kept_with_exa_error` (Review Focus 2): the summary is `"not json"` → `decisions == []` and `exa_error` set.
  - `test_rerun_skips_documents_already_extracted` (Review Focus 4): the second run makes 0 client calls, and the file has no duplicate `doc`.

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m unittest tests.test_timesplit -v`. Expected: the new tests FAIL.

- [ ] **Step 3: Implement `exa_extract`.** Append each row as it finishes, so a crash keeps the work done.

- [ ] **Step 4: Run the full suite.** Expected: OK.

- [ ] **Step 5: Commit.**

### Task 4: Claude check and fallback

**Files:**
- Modify: `autoresearch/taste/timesplit.py`
- Test: `tests/test_timesplit.py` (new class `CheckTest`)

**Interfaces:**
- Consumes: `extraction/exa.jsonl` (Task 3); corpus text through `read_doc`.
- Produces:
  - `normalize_for_quote(text: str) -> str`: NFKC; curly quotes → straight; `-\n` joins; all whitespace runs → one space; lowercase.
  - `quote_in_text(quote: str, text: str) -> bool`: true if the normalized quote is a substring of the normalized text and is at least 20 characters long.
  - `CHECK_PROMPT: str`, a versioned constant (`CHECK_PROMPT_VERSION = "check-v1"`). It asks for JSON `{"verdicts": [{"index": int, "action": "keep"|"correct"|"drop", "decision": {...same fields as the schema...}}], "missed": [{...same fields...}]}`.
  - `check_decisions(researcher: Researcher, llm: LLM, chunk_chars: int = 150_000, overlap: int = 2_000) -> dict` writes `extraction/decisions.jsonl` (one row per decision: the schema fields plus `doc`, `url`, `date`, `tag` ∈ {`exa_verified`, `exa_corrected`, `claude_fallback`}, `decision_id`) and `extraction/rejected.jsonl` (`{doc, decision, reason}`, where reason ∈ {`claude_drop`, `quote_not_found`}). It returns counts per tag and per reason.

- [ ] **Step 1: Write the failing tests** with a scripted fake LLM:
  - `test_kept_decision_with_real_quote_is_exa_verified`.
  - `test_corrected_decision_is_exa_corrected_and_uses_claudes_fields`.
  - `test_decision_whose_quote_is_not_in_the_text_is_rejected` (the code check overrules a `keep`).
  - `test_missed_decision_is_added_as_claude_fallback`.
  - `test_document_where_exa_failed_is_fully_claude_fallback` (Review Focus 2).
  - `test_pdf_quote_with_ligature_curly_quotes_and_hyphen_break_matches` (Review Focus 3): text `"we ﬁrst ran a base-\nline"` vs quote `"we first ran a baseline"` → True. Text with `“realistic”` vs quote `"realistic"` → True.
  - `test_decision_past_the_first_chunk_is_found` (Review Focus 5): `chunk_chars=100`; the decision's quote sits at character 250.
  - `test_rerun_skips_checked_documents` (Review Focus 4).

- [ ] **Step 2: Run them to see them fail.** Expected: FAIL.

- [ ] **Step 3: Implement.** Chunks overlap by `overlap`. Each chunk's prompt carries only the Exa decisions not yet resolved by an earlier chunk. Decisions are deduplicated by normalized quote.

- [ ] **Step 4: Run the full suite.** Expected: OK.

- [ ] **Step 5: Commit.**

### Task 5: Distractors

**Files:**
- Modify: `autoresearch/taste/timesplit.py`
- Test: `tests/test_timesplit.py` (new class `DistractorTest`)

**Interfaces:**
- Consumes: `extraction/decisions.jsonl` (Task 4); Task 1's `search`; `dated_docs`.
- Produces:
  - `SOURCES = ("named", "own_future_work", "contemporaneous", "generated")`.
  - `next_distractor(decision: dict, researcher: Researcher, llm: LLM, client: Optional[ExaClient], cutoff: str, after: Optional[str] = None) -> Optional[dict]` → `{"text": str, "source": one of SOURCES, "evidence_url": Optional[str]}`. It tries sources in order, starting after `after`.
  - `find_distractors(researcher, llm, client, cutoff) -> dict` writes `extraction/distractors.jsonl` (`{decision_id, text, source, evidence_url}`).
  - Visibility rule: for a decision dated before `cutoff`, the future-work candidates, the "was it pursued?" check and the contemporaneous search may use only material dated before `cutoff`. The contemporaneous `end_date` is `min(decision date + 6 months, cutoff - 1 day)`; for held-out decisions it is decision date + 6 months.
  - The contemporaneous search passes `exclude_text=["Hobbhahn"]` and `exclude_domains=["apolloresearch.ai"]`, and code drops any result whose author or text contains "Hobbhahn" (`excludeText` is approximate).

- [ ] **Step 1: Write the failing tests:**
  - `test_named_alternative_is_used_first`.
  - `test_own_future_work_is_skipped_when_he_pursued_it_later` (the fake LLM says "pursued").
  - `test_history_decision_never_sees_material_from_after_cutoff`: no prompt or search for a pre-T decision contains a post-T doc's text or an `end_date` on or after T.
  - `test_contemporaneous_search_excludes_his_own_work`: the recorded body has `excludeText == ["Hobbhahn"]`.
  - `test_generated_is_the_last_resort`.
  - `test_next_distractor_after_a_source_starts_at_the_following_one`.

- [ ] **Step 2: Run them to see them fail.** Expected: FAIL.

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Run the full suite.** Expected: OK.

- [ ] **Step 5: Commit.**

### Task 6: Write the pairs and the split (replaces `build_pairs`)

**Files:**
- Modify: `autoresearch/taste/timesplit.py`: remove `build_pairs`, `EXTRACT_PROMPT` and `_pick_prompt`; change `_context` and `write_choice_files`; add the CLI subcommands.
- Test: `tests/test_timesplit.py`: replace `FakeLLM` and the `build`-based tests in `TimeSplitPairsTest`. Keep `test_research_docs_before_cutoff_become_history_and_after_become_heldout`, `test_chosen_option_is_not_always_in_the_same_position`, `test_build_refuses_to_overwrite_existing_pairs` and `test_pair_rejected_in_review_leaves_the_heldout_file`, rewritten against `write_pairs`. Keep the leakage tests in `TimeSplitLeakageTest` unchanged.

**Interfaces:**
- Consumes: `decisions.jsonl` (Task 4), `distractors.jsonl` (Task 5).
- Produces:
  - `PAIR_PROMPT` (versioned, `PAIR_PROMPT_VERSION = "pair-v1"`) → JSON `{"context": str, "did": str, "alternative": str}`.
  - `check_pair(pair: dict, later_titles: List[str]) -> List[str]`: problems, empty if fine. It checks: the length ratio of the two options is ≤ 1.2; no banned name (Global Constraints) in the context or either option; the context contains none of `later_titles` (titles of his documents dated after the decision).
  - `write_pairs(researcher: Researcher, llm: LLM, cutoff: str, seed: int = 0) -> dict` writes `pairs_timesplit.jsonl`. It raises `FileExistsError` if the file exists. Each row holds `pair_id, split, date, source_doc, url, decision_point, context, a_text, b_text, chosen, reason, tag, distractor_source, author_position, cutoff, prompt_versions`. It then calls `write_choice_files`. A failed `check_pair` gets one rewrite, then the pair is dropped and counted under `failed_checks`. It returns `{"pairs", "history", "heldout", "failed_checks", "cutoff"}`.
  - `write_choice_files` builds `Choice(user_id=slug, context=pair["context"], a_text, b_text, chosen, decision_point=pair["decision_point"], reason=pair["reason"], timestamp=pair["date"], source="timesplit", example_id=pair_id, group_id=pair["url"])`.
  - CLI: `python3 -m autoresearch.taste.timesplit {harvest,extract,check,distract,pairs,review} --researcher SLUG [--cutoff YYYY-MM-DD] [--llm claude-cli] [--model claude-sonnet-5-5] [--max-usd N] [--start --end]`. The `review` subcommand is the existing one.

- [ ] **Step 1: Write the failing tests:**
  - `test_context_never_names_him`: the fake LLM writes "Marius Hobbhahn" in the context → the pair is rewritten once, then dropped; `failed_checks == 1`.
  - `test_unequal_option_lengths_fail_the_check` (ratio 1.5 → a problem).
  - `test_context_naming_a_later_title_fails_the_check`.
  - `test_choice_rows_carry_decision_point_reason_and_group_id`.
  - `test_ab_order_is_seeded`: the same seed gives the same order twice; across 12 pairs both positions occur.
  - The four kept tests, rewritten.

- [ ] **Step 2: Run them to see them fail.** Expected: FAIL.

- [ ] **Step 3: Implement.** a/b order comes from `random.Random(f"{seed}:{pair_id}")`.

- [ ] **Step 4: Run the full suite.** Expected: OK.

- [ ] **Step 5: Commit.**

### Task 7: E2 evaluation and the distractor gate

**Files:**
- Create: `autoresearch/taste/track_eval.py`
- Test: `tests/test_track_eval.py`

**Interfaces:**
- Consumes: `history_timesplit.jsonl`, `heldout_timesplit.jsonl`, `pairs_timesplit.jsonl`; `timesplit.docs_before`, `timesplit.next_distractor`; `methods.create_method(method, llm, **kwargs)`; `research.decisions.code_version()`.
- Produces:
  - `load_choices(path: str) -> List[Choice]`.
  - `paired_correct(model, choice: Choice) -> bool`: asks `predict(context, [a, b])` and `predict(context, [b, a])`; true only if both pick his option.
  - `cluster_ci(correct_by_group: Dict[str, List[bool]], level=0.9, n=2000, seed=0) -> Tuple[float, float, float]` → (accuracy, low, high). It resamples groups and computes the ratio of summed correct to summed n.
  - `cluster_diff_ci(a: Dict[str, List[bool]], b: Dict[str, List[bool]], ...)`: the same, for the paired accuracy difference (same groups).
  - `DocsInPrompt(llm, docs: List[Tuple[str, str]], max_chars=60_000)`: the M1-docs arm, with `predict(context, options) -> Prediction`.
  - `NamedNoHistory(llm, name)`: M0 with "These are choices made by {name}." prepended to the context.
  - `blind_judge(choices: List[Choice], llm) -> Dict[str, bool]`: example_id → the judge picked his option in both orders.
  - `distractor_gate(researcher, judge_llm, pair_llm, client, cutoff, threshold=0.75) -> dict`: if the flagged share exceeds the threshold, each flagged pair gets `next_distractor(after=its source)`, is rewritten with `PAIR_PROMPT` and judged again (one round). It writes `gate_timesplit.jsonl` and returns `{"flagged_before", "flagged_after", "regenerated"}`.
  - `select_method(history: List[Choice], llm, candidates=("m2","m3","m4","m5","m6","m7")) -> str`: fits each on the earliest 80% of history by date and scores paired accuracy on the latest 20%.
  - `run_e2(researcher, llm, judge_llm, cutoff, selected: str) -> dict`, written to `results/track_s/E2_<slug>.json`. Contents: per arm (`m0`, `m0_named`, `m1_pairs`, `m1_docs`, selected), accuracy and 90% CI; the selected-minus-each-baseline differences with CIs; accuracy by `tag` and by `author_position`; accuracy with and without still-flagged pairs; the contamination gap (`m0_named - m0`); `n_pairs`, `n_groups`, `cutoff`, model ids, `CODE_VERSION`, `cost_usd`.
  - CLI: `python3 -m autoresearch.taste.track_eval {gate,select,e2,final} --researcher SLUG --cutoff ...`. `final` fits the selected method on all pairs, saves `data/researchers/<slug>/usermodel.json` and runs `usermodel_store push`.

- [ ] **Step 1: Write the failing tests** with fake models:
  - `test_pair_counts_only_when_both_orders_are_right`: a model that always picks position 0 scores 0.
  - `test_cluster_ci_resamples_groups_not_pairs`: one group of 10 all-correct pairs plus one group of 1 wrong pair → the interval's low end is ≤ 10/11 and its high end is 1.0. (Pair-level resampling would give a much narrower interval.)
  - `test_docs_arm_sees_no_document_from_after_cutoff`.
  - `test_named_m0_mentions_the_name_and_plain_m0_does_not`.
  - `test_gate_regenerates_only_when_flagged_share_exceeds_threshold`: 8 of 10 flagged → regenerated; 7 of 10 → untouched.
  - `test_select_method_never_sees_heldout_pairs`.
  - `test_e2_report_has_every_arm_and_the_contamination_gap`.

- [ ] **Step 2: Run them to see them fail.** Expected: FAIL.

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Run the full suite.** Expected: OK.

- [ ] **Step 5: Commit.**

### Task 8: Review before the paid run

**Files:** none (a review gate).

- [ ] **Step 1: Run the whole-branch review** of Tasks 1–7 against the spec. It covers the existing `timesplit.py` leakage code and `usermodel_store.push`, which the run depends on. Fix what it finds before Task 9.
- [ ] **Step 2: Offline dry run** over a two-document fixture corpus, with `OfflineLLM` and a fake Exa client, through every CLI subcommand. Expected: each stage writes its file and E2 writes a report marked offline.

### Task 9: Live run, results and the extraction doc

**Files:**
- Create: `data/researchers/marius_hobbhahn/CONSENT.md`, the corpus, the extraction files, the pairs files, `usermodel.json`
- Create: `results/prereg/E2_S.json`, `results/track_s/E2_marius_hobbhahn.json`, `docs/track-s-extraction.md`
- Modify: `docs/superpowers/specs/2026-11-14-track-s-extraction-design.md` (file names → `*_timesplit.jsonl`)

- [ ] **Step 1: Blockers.** `[ -n "$EXA_API_KEY" ] && echo ok` prints `ok`; if not, stop and ask Ethan. Look up Sonnet 5.5's training cutoff on Anthropic's models overview page, and set T = that minus 3 months. Record the page URL in the prereg.
- [ ] **Step 2: Claim and post.** `agentctl claim real-researcher` and `agentctl claim exa-live-run`, then post the start of a costly run (rule 5).
- [ ] **Step 3: Write `CONSENT.md`:** Ethan reported Marius's written consent in the Claude Code session on 2026-11-14. Scope: committing his texts, including X posts, to this private repo, and pushing a model of him to past.dev.
- [ ] **Step 4: Summary-coverage smoke.** Run `extract` on his two longest papers. Note whether Exa's decisions cite quotes from the last third of each paper; this goes in the extraction doc.
- [ ] **Step 5: Run the stages in order:** `harvest`, `extract`, `check`, `distract`, `pairs`. After each one, record its counts and its spend (Exa cost plus `Budget.cost_usd`). Stop if the running total would pass $200.
- [ ] **Step 6: Held-out floor.** If there are fewer than 40 held-out pairs from at least 10 documents, delete the pairs files, move T back three months, rerun `pairs`, and record why.
- [ ] **Step 7: Run `track_eval gate`, then `track_eval select` (unless WS A has selected a method by then; check `docs/user-models/handoff.md`).** Commit `results/prereg/E2_S.json`: arms, T, n, the success rule (the selected method beats both M1 arms, each 90% CI excluding 0), and the gate result.
- [ ] **Step 8: Run `track_eval e2`, then `track_eval final`.** Commit the results and the researcher directory.
- [ ] **Step 9: Write `docs/track-s-extraction.md`.** One section per stage: what it does, the exact prompt versions, the real counts (kept and dropped by reason, decisions by tag, distractors by source, pairs that failed checks, gate before/after) and the cost. Update the spec's file names.
- [ ] **Step 10: Board.** Post to WS D (`history_text` should read `history_timesplit.jsonl`, so R1-S-prompt sees the same pairs) and to WS A (`Researcher.build_profile` should skip text rows). Then `agentctl done real-researcher` and `agentctl done exa-live-run` with the summary and result paths, and unlock.
