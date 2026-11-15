# Compression eval: post-T lineup (run 2026-11-15)

This implements and runs the protocol pre-registered in `ideas/compression.md` §4. The file was copied unchanged to
`prereg/compression.md` before any call (sha256 `064b96d7…f3457`, identical to the source). Deviations are listed
below.

**Setup.** Cutoff T = 2025-04-01. The five researchers serve as each other's distractors. There are 25 held-out
post-T docs, 5 per researcher (`heldout/docs.jsonl`). Profiles are capped at 250 words and built from pre-T
evidence only (`profiles/<slug>/<ARM>.md`). The judge is `claude -p --model haiku`, which also built and
summarised. Chance is 0.20 on every metric.

**Calls: 98 real CLI calls** against a hard cap of 100 (`calls.log`). They break down as 20 build, 6 neutralize
(1 retry) and 72 lineup (2 parse retries, both in NAMES). With the cache in `cache/`, a re-run costs 0 calls.

## Results

L1 shows the full summaries (topic visible). L2 shows the method-only summaries (topic-blind). Top-1 gives fractional
credit when the max is tied. The CI is a 95% percentile bootstrap over the 25 docs (10k resamples). p is the
one-sided binomial test against 0.20. G↔S and H↔B are hard-pair accuracies: the share of that pair's 10 docs
where p(true) > p(other member of the pair), with mean p(true)/(p(G)+p(S)) in brackets. Collapse is the
largest share of picks that went to one profile.

| Run | Arm | Top-1 (of 25) | 95% CI | p vs chance | Mean p(true) | Log-loss | G↔S acc [ratio] | H↔B acc [ratio] | Collapse |
|---|---|---|---|---|---|---|---|---|---|
| L1 | NAMES | **0.46** (11.5) | 0.28–0.66 | **0.002** | **0.400** | 1.18 | 0.4 [0.55] | 0.6 [0.54] | 0.26 |
| L1 | EX | **0.39** (9.7) | 0.23–0.56 | **0.017** | 0.308 | 1.42 | 0.4 [0.46] | 0.4 [0.59] | 0.35 |
| L1 | M3 | 0.25 (6.2) | 0.10–0.41 | 0.38 | 0.232 | 1.72 | 0.4 [0.51] | 0.4 [0.60] | 0.41 |
| L1 | A_pre | 0.16 (4.0) | 0.04–0.30 | 0.77 | 0.200 | 1.73 | 0.5 [0.51] | 0.1 [0.40] | 0.38 |
| L1 | A_full | 0.24 (6.0) | 0.10–0.40 | 0.38 | 0.241 | 1.63 | 0.4 [0.49] | 0.4 [0.52] | 0.50 |
| L1 | E_pre | 0.14 (3.4) | 0.02–0.27 | 0.90 | 0.168 | 1.86 | 0.2 [0.47] | 0.2 [0.45] | 0.28 |
| L1 | E_full | 0.28 (6.9) | 0.14–0.43 | 0.22 | 0.216 | 1.60 | 0.2 [0.49] | 0.4 [0.55] | 0.28 |
| L1 | DIFF | 0.20 (5.0) | 0.04–0.36 | 0.58 | 0.235 | 1.69 | 0.2 [0.49] | 0.3 [0.53] | 0.34 |
| L2 | NAMES | 0.30 (7.5) | 0.16–0.45 | 0.11 | 0.257 | 1.48 | 0.2 [0.47] | 0.4 [0.55] | 0.28 |
| L2 | M3 | 0.32 (8.0) | 0.16–0.50 | 0.11 | 0.215 | 1.87 | 0.3 [0.44] | 0.7 [0.62] | 0.36 |
| L2 | A_pre | 0.29 (7.2) | 0.12–0.46 | 0.22 | 0.271 | 1.49 | 0.3 [0.55] | 0.4 [0.55] | 0.39 |
| L2 | E_pre | 0.30 (7.4) | 0.14–0.47 | 0.22 | 0.219 | 1.67 | 0.3 [0.46] | 0.5 [0.52] | 0.38 |
| L2 | DIFF | 0.32 (8.0) | 0.16–0.50 | 0.11 | 0.250 | 1.65 | 0.4 [0.51] | 0.5 [0.56] | 0.28 |
| L3 | A_pre (repeat) | 0.28 (7.0) | 0.12–0.48 | 0.22 | 0.259 | 1.55 | 0.5 [0.51] | 0.6 [0.56] | 0.40 |

**Noise floor.** L1-A_pre and L3-A_pre ran the same arm on the same summaries with a new batch composition and
label order. The top-1 pick changed on **13/25 docs (flip rate 0.52)**, and top-1 accuracy moved from 0.16 to 0.28.
By the pre-registered rule, any gap below 0.52 counts as noise. That covers every gap in this table.

**Pre-registered comparisons.** The sign test is exact. "x/y only" counts docs where exactly one arm was right;
tied picks are excluded.

| Comparison | Run | Top-1 gap | x only / y only | Sign p | Mean p(true) gap |
|---|---|---|---|---|---|
| M3 − A_pre | L1 / L2 | +0.09 / +0.03 | 4/2 , 4/4 | 0.69 / 1.0 | +0.03 / −0.06 |
| A_pre − E_pre | L1 / L2 | +0.02 / −0.01 | 1/2 , 4/4 | 1.0 / 1.0 | +0.03 / +0.05 |
| **Leakage gap** A_full − A_pre | L1 | +0.08 | 3/1 | 0.63 | +0.04 |
| **Leakage gap** E_full − E_pre | L1 | +0.14 | 4/1 | 0.38 | +0.05 |
| EX − NAMES | L1 | −0.07 | 4/2 | 0.69 | −0.09 |
| A_pre − NAMES | L1 / L2 | −0.30 / −0.01 | 1/8 , 1/1 | **0.039** / 1.0 | −0.20 / +0.01 |
| E_pre − NAMES | L1 / L2 | −0.32 / −0.00 | 1/8 , 4/3 | **0.039** / 1.0 | −0.23 / −0.04 |
| M3 − NAMES | L1 / L2 | −0.21 / +0.02 | 5/9 , 3/2 | 0.42 / 1.0 | −0.17 / −0.04 |
| DIFF − NAMES | L1 / L2 | −0.26 / +0.02 | 3/9 , 3/3 | 0.15 / 1.0 | −0.17 / −0.01 |

- **Value over the prior** means beating NAMES on both L1 and L2. **No arm does this.** On L1 every
  compressed arm is below NAMES, and two of them (A_pre, E_pre) are significantly below at an uncorrected
  p = 0.039. Those p-values come from many comparisons, so treat them as suggestive.
- **Ranking** of the clean arms plus A_pre by mean(L1, L2) top-1: M3 0.28 > DIFF 0.26 > A_pre 0.22 > E_pre 0.22.
  All are within noise, so this is a tie. EX has no L2 run in the protocol. On L1 it is the only profile arm
  above chance (p = 0.017).
- **M3 vs A_pre:** a tie. The pre-registered expectation M3 < A_pre is not supported.
- **A_pre vs E_pre:** a tie. Nothing shows the expected "principles beat persona".
- **Leakage:** the full cards score above their pre-T versions by +0.08 (A) and +0.14 (E). Both gaps point the
  expected way, both are inside the noise floor, and neither is significant.
- **L2 vs L1:** topic-blind accuracy is about 0.30 for every arm, NAMES included. That is not above chance
  (best p = 0.11). No arm shows that it carries eval-design taste that haiku can match to later method choices.

## Leakage check (name-masked profiles and summaries)

- **Mask** (`mask.json`) contains the following:
  - the `banned`, name and exclude_text entries from all five `identity.json` files;
  - the first names and handles of the five researchers;
  - 1,085 co-author full names and 743 co-author surnames from all five corpora's front matter (≥4 letters,
    with common English words excluded);
  - `X et al.` citations;
  - 40 org names and 19 model-name stems (with version suffixes);
  - 48 coined paper and project names (case-sensitive, so lowercase topic phrases stay);
  - Hobbhahn and Apollo.
- **Summaries:** 0 regex hits across 50 summary texts (25 full plus 25 method-only). The check covered the
  mask plus 4-grams of each held-out doc's own title (`heldout/summaries.jsonl` `leak_hits`). Before
  summarising, I removed every input line that contained a mask string, then capped each doc at 6,000
  characters (`heldout/neutralize_input_stats.json`).
- **Summaries, by eye:** I read all 25. They contain no names, orgs, titles or model names. Full summaries
  still carry topic fingerprints, which the protocol allows: "archaic bird names → nineteenth century", "simulated
  to 100,000 tasks via importance sampling", "a review of a popular book arguing AI would cause extinction".
  Method-only summaries are generic. Several are near-interchangeable ("conceptual argument, no experiments,
  hedged").
- **Profiles:** 0 regex hits after masking, in all 35 non-NAMES profiles (`profiles/build_report.json`). Haiku
  outputs (M3, E_pre, DIFF) had 0 hits before masking too. Masked tokens remaining in the profiles:
  - `[PERSON]` ×5: the "the way [PERSON] would…" opener of each E_full;
  - `[ORG]` ×2 and `[MODEL]` ×1 in EX quotes.
- **Residual risk the regex can't catch:** EX quotes are verbatim, so voice and stylometry come through. Some
  profiles name a distinctive research line in plain words, for example Bowman's DIFF on hypothesis-only NLI
  baselines and annotation artifacts. Haiku can map those to a person, and NAMES shows it knows these people.

## Deviations from the pre-registration

1. Output dir is `experiments/taste_petri/compression_eval/`, not `ideas/compression_eval/` (caller's
   instruction). The results table is in this README instead of `results.md`. A bootstrap CI was added (caller's request).
2. I wrote my own `subprocess` wrapper with the same isolation flags as `profiles/_work/steer_test.py` (tools,
   MCP and settings off, empty temp cwd). I did not use `ClaudeCLILLM`, so that I could do per-call
   logging, the cap and the cache. The cap counts calls at start.
3. The mask was extended beyond the pre-registered list (see above), to cover co-authors, citations and coined work names, as
   the caller required. "Microsoft" was added after the first build pass. That changed only EX (verbatim quotes)
   and cost 0 calls, because cached prompts were unchanged.
4. D-point labels were normalised (for example "D1 (what to test)" → D1) for the M3 peer pairing and the EX tags. Without
   this, the free-text labels split each D-point.
5. For M3 pseudo-choices, the peer claim is drawn from peers' principle, heuristic and distrust rows (the same kinds
   as the target's), not from any claim. Batched propose and reconstruct calls were already a pre-registered
   deviation. `cluster_principles` (imported, not edited) gave one cluster per proposal for every researcher
   (support = 1 everywhere), as §3.2.4 predicted. `selected_history` was also imported.
6. The E_pre prompt keeps only the (e) section of `reduce_prompt.txt` and adds "do not name any person, org, paper or
   model". The DIFF and neutralize prompts got the same instruction. Haiku instead of sonnet was pre-registered.
7. Neutralize: haiku "repaired" a truncated doc id (`underm_` → `undermin_`). Doc ids are now matched on their hash
   suffix. The parse failure cost 1 retry call (the cached first answer was used). Masking is applied to
   summaries after the leak check. It was a no-op, since there were 0 hits.
8. Within a run, all arms share the same batches and label permutations. The protocol did not specify this, and
   sharing makes arm-vs-arm comparisons paired.
9. Top-1 ties get fractional credit 1/k. Tied max rows per arm out of 25: L1 E_full 10, L2 NAMES 11, others
   1–8. Sign tests skip tied docs. Hard-pair accuracy counts a 0.5 ratio as wrong. Both the accuracy and the
   pre-registered mean ratio are reported.
10. Calls: 98, against 95 planned. The 3 extra are retries: 1 neutralize and 2 NAMES lineup parse failures.

## Files

`run.py` (select/build/neutralize/lineup/score), `prompts/`, `mask.json`, `heldout/`,
`profiles/<slug>/{ARM}.md` + `m3_trace.json`, `lineup/<run>_<arm>_b<k>.json` (raw reply + parsed
probabilities), `cache/`, `calls.log`, `results.json` (all metrics, confusion matrices, per-arm word counts),
`lineup_run.out`.

## Interpretation

With n = 25 and a noise floor of 0.52 (the same arm flipped 13/25 picks between reruns), this lineup cannot
separate the compression formats. Every arm-vs-arm gap is within noise, and so are both leakage gaps. The
only clear signals are about haiku's prior:
- the bare name (0.46) and verbatim quotes (0.39) beat chance on topic-visible summaries;
- no compressed profile beats the bare name;
- nothing beats chance topic-blind.

So this test gives no evidence that these profiles encode person-specific eval-design taste that haiku can use. Before ranking
formats, the next step needs a bigger, less noisy test: more docs, a sonnet judge, and averaging over several label
orders.
