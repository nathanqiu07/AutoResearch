# Researcher full-history comparison

This corrects the earlier small pilot, not a claim to reproduce either paper's
scores or recover human research judgment. The source labels are AI-inferred.
Use only the pinned 373-row `history_timesplit.jsonl` from data commit
877dcff723c77c4525cde3fd10fc16f7a540a9d6. Never load the upstream heldout file.
The runner verifies 236 learning, 70 validation, identical 67 development IDs,
source-document separation and duplicate content. Model inputs omit stored reasons.

## Methods and deviations

M0 uses no history. M1 includes all 236 choices, with redundant metadata removed.
M2 follows SynthesizeMe's label-hidden prediction/rejection stage, persona synthesis,
and second bootstrap/search stage. All 236 rows participate in both bootstrap passes.
Each stage searches ten seeded random subsets plus the released-code controls,
scoring all 70 validation choices independently. The 64-demonstration limit is a
budget adaptation, not a paper default. A successful trace pool is cached once per
stage rather than regenerated within each candidate search. Up to four raw labeled
examples fill short demonstration sets as in the release. The persona is predicted
in one call. No max-hypotheses cap or 1,600-character truncation remains; the existing
2,048 output-token safety limit still applies per API call. Confidence is uncalibrated.

Ruling: use the paper's generic persona instruction, with evidence-only wording,
rather than the released optimized Llama prompt. That prompt explicitly inserts
unsupported personal traits. Cross-user MIPRO optimization and its demonstrations
are omitted, and no claim of exact DSPy equivalence is made.

M3 proposes two rules from each of two contrastive prompts for every learning pair
(up to 944 proposals). Semantic embeddings (text-embedding-3-small, 256 dimensions)
and seeded k-means select up to 80 candidate representatives. Each candidate votes
on all 236 history pairs in three rounds; each call scores up to 40 rules, with an
explicit irrelevant vote. Disagreement across repeats counts as irrelevant. Rules
must have more correct than incorrect votes and correct/total >=10% (the released
code's stricter implementation of the paper's relevance threshold). Rank by correct
minus incorrect; compare top five and top ten on all validation choices. Ties favor
five. The validation comparison is an extension. Optional final diversity clustering
is omitted. Embedding model and exact generation prompts differ from the paper.

Sources (audited source revisions):
- https://arxiv.org/html/2406.06560
- https://github.com/rdnfn/icai/tree/cb88e6588e9a01e8c1f216ea3cfe1b7461ddee7d
- https://arxiv.org/html/2506.05598
- https://github.com/SALT-NLP/SynthesizeMe/tree/e91f340122db42b2940c07bcfe6a264bbe554353

## Execution

Python 3.9+, no new package dependencies. From the repo root:

```bash
python scripts/taste_full_history.py prepare --source PATH/TO/history-source.jsonl --previous-manifest PATH/TO/previous-pilot/manifest.json --output runs/hobbhahn-full-paper
python scripts/taste_full_history.py offline --output runs/hobbhahn-full-paper
python scripts/taste_full_history.py live --output runs/hobbhahn-full-paper
```

Live reads OPENAI_API_KEY or a hidden terminal prompt. Output paths must be fresh;
failed outputs are never overwritten. Do not repeat live commands without counting
previous attempts against the total budget. The runner reserves $8.50 for this run,
leaving prior commitments of $0.361817 and slack below the user's $10 total.
Requests have preflight dollar reservations and no automatic network retry.
Eight concurrent isolated request workers share one budget. The two extraction
methods run sequentially; per-method usage is measured around completed batches.

Inspect `live/report.json`, `live/models/`, `live/requests.jsonl`,
`live/predictions.jsonl`, `live/m2-viewer.html`, and `live/m3-viewer.html`.
Models include all search scores and bootstrap acceptance records. Exported models
are in `live/exports/m2/usermodel.json` and `live/exports/m3/usermodel.json`.
Offline fixtures check plumbing only. One researcher does not support a meaningful
user-bootstrap confidence interval; do not interpret the report's degenerate CI
as certainty. The development set was already inspected in the old pilot, so this
comparison is development evidence, not an untouched final evaluation.

## Live format correction

The first attempt at 29c1871 was stopped during raw-history predictions because
multiple outputs contained extra text or multiple JSON objects. Failed traces
are preserved. The rerun uses API strict JSON schemas for all four methods and a
new backend identity/cache namespace. Earlier attempt spending and reservations
are passed with `--prior-attempt-budget PATH/TO/final-budget.json` and included in
the new run ledger. No prediction was salvaged by choosing a preferred JSON object.

The strict-schema attempt also returned malformed envelopes. The final parser
recovers complete objects only if all answer-bearing objects agree exactly
(excluding rationale wording); conflicting answers still fail. The raw envelopes
are retained in response-envelopes.jsonl. Valid cache entries from the strict-schema
attempt are reused; its full ledger is charged before the new attempt.

## Concurrency

Start at 16 independent requests. After a complete stage with at least 64 fresh
requests and no errors, increase to 32. Record elapsed time, request count, and
errors per stage. An error resets concurrency to 16. This changes scheduling only;
all data, prompts, candidate sets and trials remain fixed.

## Failure recovery

Attempt 04 completed with failed fits because one invalid/failed request stopped
each search. Its zero accuracies for M2/M3 represent failed execution, not
preference evidence. The continuation allows up to five attempts per logical
request, only after transport, format, or schema failures. It never retries a
valid prediction based on correctness. Every attempt is charged by the shared
backend and every failed reservation is retained. Retry events are saved.
Any retry failure backs concurrency down to 16 for the next stage. Logical-call
counts in per-method summaries exclude retries; backend usage counts all attempts.
Valid cached results retain their original predictions. All prior budget ledgers
are included when calculating the remaining global $10 allowance.
