# Approved history-only filtering

Scope: 373 Hobbhahn history pairs, no held-out inference or refit. Preserve originals.
Use Sonnet 5.5 via OpenRouter pinned Anthropic, no fallback. Ten independent
blind votes (five each order) plus one blind quality assessment per pair.
Quality categories: valid_tradeoff, dominated, answer_leak, incoherent.
Reject defective comparisons separately from >8/10 generic agreement. Missing
or invalid judgments remain pending. One quality assessment is fallible and
reviewable; vote share is not calibrated confidence or human preference truth.

Implementation plan: standalone Gio script, append-only request ledger with
pre-request reservations and raw responses, resume completed calls, $15 cap,
16 concurrent pairs. Export kept/rejected/pending copies and review Markdown.
Hash source and held-out files before/after, preserving original split IDs.
Check order mapping, strict >80% rule, missing-vote handling, label blindness,
resumption and budget reservations offline before live use. No teammate edits.

Execution notes:
- Sonnet 5.5 endpoint rejects reasoning=none. Use reasoning effort low, with
  max_tokens=4096 including reasoning, provider default sampling. This differs
  from the personal-track code's requested temperature=1 (not listed as supported
  by this endpoint). Ten calls are repeated model samples, not independent judges.
- Initial rejected calls are retained in runs 01/02; $0.10 reserved for them.
  Main run cap $14.90, aggregate filtering allowance <=$15.
- Parse a unique JSON object even when preceded by prose; retain raw response.
  Recovered answers use no additional inference. Never infer a vote from prose.
- Quality assessment uses one original-order presentation, so its order bias is
  not measured; only the ten-vote stage is order balanced.
- Generic agreement exclusion selects a harder dataset and can favor incorrect
  source labels. It does not establish genuine personal taste or source accuracy.
- Filtering covers the old learning/validation/dev portions of history. Any later
  scores on that filtered subset are conditional on this screen, not comparable
  without qualification to the old unfiltered accuracy. No refit in this task.
