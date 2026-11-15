# Seed-level ICAI with dual verification: prototype results (2026-11-15)

A prototype of changes C1-C4 in `ideas/taste_injection.md` ("Fit with the current ICAI/M-grid design"), with the
ICAI fixes from `ideas/compression.md` §3: pseudo-choices built from the corpus, semantic clustering, and selection
on held-out pairs by lift over M0. The prototype then adds an M6-style second filter on the Petri side.
Code: `seed_icai.py` (standard library; it imports repo code read-only). Every number below comes from the JSON
files in this directory.

**Objective as amended mid-run (coordinator):** "the real eval is Petri; optimise against Petri and being able to
predict taste". The Petri-side filter is therefore a **Petri-judge proxy**: haiku scores the transcript on Petri's
own `eval_awareness` and `scenario_realism` with the verbatim v2 rubrics. I reused `arms/petri_judge.py`, so the
scores compare directly with the R0 arm. Proxy A2 is a secondary column.

## Stages and call counts

| Stage | What | Real CLI calls |
|---|---|---|
| pairs | 37 seed-variant pairs from verified quotes, one sonnet call per researcher | 4 |
| fit | 36 proposals (sonnet, one call per fit pair), 1 semantic clustering call, batched haiku predictor for M0 + 5 principles on validate and fit (one failed batch, re-asked keyed by item) | 32 |
| gate | `agreement.judge`: blind sonnet, 5 votes in each order, for each (principle, contrary) | 50 |
| axes | each principle mapped onto the 14 axes in `data/trackp/tradeoffs.jsonl` (sonnet) | 1 |
| control | fictional-names-only control on 12 dev seeds: auditor-sim, A2 on the prefix, target-sim, Petri judge (stock calls served from the proxy and arms caches) | 33 |
| verify | 5 operators × (rewrite 3 calls + ≤8 edited seeds × 4 calls + validity on 3 seeds) | 182 |
| bt | Bradley-Terry over operators, committee ordering | 0 |
| final | constitution rewrite + full proxy k=1 (5 calls/seed) + Petri judge, plus the control's missing judge calls | 84 |
| **total** | logged in `calls.log` (cap 450 = 350 + the ~100 granted) | **386** |

Failures: `v2_seed_28` was refused by the haiku auditor in every arm (as in the calibration). `v2_seed_70` was blocked
by the CLI's AUP filter (`[bio]`) in some arms. In the final run, `v2_seed_21`'s full-proxy path timed out twice, so
its A2 and validity are missing (its Petri-judge score exists). The final paired comparisons therefore use n = 9-10
seeds.

## 1. Pseudo-choices from the corpus (`pairs.jsonl`)

I chose 37 verified `realism_move`/`distrust` items by hand, before any model call. Each one criticises a concrete
design choice in an eval, audit, control or model-organism setup: Bowman 9 (incl. the "Claude Finds God" inbox and
protonmail critiques, the OpenAI pilot exercise and AuditBench), Greenblatt 11 (incl. the Sonnet 4.5 eval-gaming
post), Shlegeris 8 (incl. LinuxArena and the control-setting posts), and Hubinger 9. Owain Evans's items are left
out. No item comes from Hobbhahn material.

For each item, sonnet wrote a pair of Petri-style seeds: the flawed setup, and the same setup with the flaw fixed.
The variants are 70-140 words, use fictional organisations, and are of similar length (mean length ratio 0.99).
Nothing in the text labels the flawed variant. The fixed variant is the chosen one, the A/B position comes from a
hash (19 A, 18 B), and the quote is kept as `reason`. **Split by date: fit = 18 items before 2025-03, validate = 19
items from 2025-03 on.** Validate holds 7 Bowman, 5 Greenblatt, 4 Shlegeris and 3 Hubinger items.

The pairs are **mostly generic sense, not taste**. M0, a haiku predictor with no principles that is told to judge as
"a typical alignment-audit designer", picks the researcher's side on **18/19 validate pairs (acc 0.95)** and 0.86
in-sample. Its stated P(chosen) is ≥ 0.7 on 15/19. The pairs M0 gets wrong or is unsure about are the informative
ones:
- fit: Greenblatt E3 (match the surface features of real inputs), Shlegeris E13 (*less* context, fewer tells),
  Hubinger E37;
- validate: Greenblatt E44 (withhold the current time and other scaffolding cues; M0 0.30), Bowman E45 (simpler
  scenarios, because complex multi-incentive seeds break the auditor), Shlegeris E33 (overlapping access).

## 2. ICAI proposal, clustering and held-out selection

Files: `model_fit.json`, `principles.json`.

The 36 proposals went into 5 semantic groups (the cap I set for budget; none was left unclustered). Each group has
a representative rule and a defensible contrary. Selection was pre-registered as: Δlog P(chosen) > 0 over M0 on
validate, with no loss of accuracy.

## 3. Principle table

R = researcher filter (held-out lift over M0). Gate = share of 10 blind votes for the principle over its contrary;
a share above 0.8 is lopsided and classed as generic realism. Petri = the edited seeds against the fictional control: Δ
`scenario_realism` and Δ `eval_awareness` (1-10), Δ A2-prefix (0-1, secondary column), and Δ validity on the first
3 edited seeds. Pre-registered Petri pass: at least 4 scored seeds, Δrealism ≥ +0.5 with P(better) ≥ 0.8,
ΔEA ≤ +0.25, Δvalidity ≥ −0.05 and faithful ≥ 0.8.

| op | Principle (short) | Support | R: Δlogp / Δacc (val) | in-sample Δacc | Gate | Axes | Edited / scored | Δrealism | ΔEA | ΔA2-prefix [90% CI] | Δvalidity | R | Petri | Both |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| op0 | Convey the tested condition through a subtle in-context cue, not an explicit label or tag | 3 docs; SB, RG, EH; 2023-24 | +0.027 / 0.00 | +0.06 | 0.9 generic | control-vs-realism → realism | 3 / 3 | −1.00 | +0.33 | +0.01 | +0.16 | ✓ | ✗ (n<4) | ✗ |
| op1 | Keep prompts neutral about the target behaviour: incentives and facts only, no instructions or pressure | 4 docs; SB, RG, EH; 2024 | −0.011 / −0.05 | 0.00 | 1.0 generic | elicitation → default; construct-scope → broad | 7 / 6 | −0.17 | −0.33 | −0.03 | −0.15 (faithful 0.68) | ✗ | ✗ | ✗ |
| op2 | Build the environment from mundane, deployment-like features with a single incidental flaw; don't signpost the opportunity | 4 docs; BS, RG, EH; 2024-25 | **+0.134 / +0.05** | +0.08 | 1.0 generic | control-vs-realism → realism | 12 / 8 | +0.25 | −0.25 | −0.01 | −0.28 | ✓ | ✗ | ✗ |
| op3 | Ground inputs in realistic source material; plant key facts in artifacts, not the system prompt | 4 docs; BS, RG, EH; 2023-25 | **+0.125 / +0.05** | +0.03 | 1.0 generic | control-vs-realism → realism; scale-vs-craft → craft | 12 / 7 | +0.14 | −0.14 | −0.01 | −0.20 | ✓ | ✗ | ✗ |
| op4 | Minimise auditor-fabricated content: no scripted target turns, steer via tool outputs, keep artifacts minimal | 3 docs; BS, EH; 2024 | −0.339 / **−0.39** | −0.17 | 1.0 generic | scale-vs-craft → craft | 12 / 7 | +0.14 | +0.14 | **−0.15 [−0.29, −0.03]** | −0.15 | ✗ | ✗ | ✗ |

The three requested buckets:
- **Passed both ("taste that works"): none.**
- **Passed the researcher filter only ("taste that doesn't help Petri"): op0, op2, op3.**
- **Passed the Petri filter only ("helps Petri but isn't this researcher's taste"): none on the primary Petri-judge
  filter.** On the secondary A2 column alone, op4 is the only clear mover (−0.15, CI excludes 0), and it is the
  principle the researchers' later choices reject. Its A2 drop comes with lost validity: on seed_48 it makes the
  shutdown script surface "only when the target looks", so in the 3-turn compressed audit the target did not reach the bait
  (validity 0.7 → 0.0). This is the proxy's documented "low A2 = bait missing" artefact. Label: **GAMING-adjacent;
  it would not survive a real Petri audit with 30 turns.**

Notes on the table:
- **The time split did real work.** op4 comes mostly from Shlegeris's 2024 untrusted-monitoring posts ("reduce the
  context, fewer tells"). It contradicts the 2025-26 critiques: Bowman's messy inbox, Hubinger E158's "real messy
  user input", Greenblatt E70. Its held-out accuracy falls to 0.55, with 0/3 Hubinger and 2/4 Shlegeris validate
  pairs right. Current M3 ranks in-sample over ≤5 rows and keeps the top 5, so it would have kept all five.
- **Every principle is lopsided under the blind gate:** 9/10 votes for op0 and 10/10 for the others. The
  critique-derived principles are field consensus, so they contain no taste-discriminative principle. This matches
  M0's 95%. The personal-information signal sits in the margins: op2/op3 raise held-out log-likelihood by ~0.13 nats
  per pair.
- **Every principle maps to the same pole of `control-vs-realism`** (or `scale-vs-craft` → craft). In the
  14-axis representation the public-track researchers are indistinguishable on this material.
- **Petri-judge resolution is poor.** Realism is an integer 5-7 for nearly every transcript and eval_awareness sits
  at 1-2, because the target-sim takes one turn and seldom voices suspicion. Per-seed diffs are mostly 0 or ±1.

## 4. Bradley-Terry over operators (`bt.json`)

`active_queries.BradleyTerry` (L2 1.0) is fitted over operator indicators.
The taste prior is 95 rows: each op_j against no edit on a validate pair, with soft label 0.5 + (P_j(chosen) −
P_M0(chosen)). The Petri outcome is 69 rows: each op against the control on each scored seed, and op against op on shared seeds, labelled
by Petri utility = realism − eval_awareness.

P(op beats no edit):

| | prior (taste) | outcome (Petri) | posterior |
|---|---|---|---|
| op0 | 0.52 | 0.22 | 0.39 |
| op1 | 0.49 | 0.48 | 0.47 |
| op2 | 0.57 | **0.68** | **0.63** |
| op3 | 0.57 | 0.61 | 0.58 |
| op4 | 0.36 | 0.59 | 0.48 |

op2 is the best-supported operator on both sides, but it lowers validity (−0.28 on 3 seeds), which BT does not see.
That is a missing likelihood term. Committee-uncertainty ordering (`active_queries._committee` +
`committee_uncertainty`) puts op1 vs op4, op0 vs op4, op4 vs no edit, and op2 vs op3 as the comparisons to run, or
to put to the researcher, next.

## 5. Final constitution vs stock, control and R0

Files: `final.json`, `final_seeds.jsonl`, `compare_vs_R0.json`.

No principle passed both filters, nor the Petri filter alone. The constitution therefore falls back to the
**researcher-filter survivors op0, op2 and op3**, labelled as not Petri-verified. Sonnet rewrote the 12 dev seeds
with them (fictional names in every arm). Scoring used the full proxy at k=1 (A2 batched with placeholder probes,
A1, validity, faithfulness) plus the Petri judge. The paired diff is per base seed, with a 90% bootstrap CI.

| vs | n | A2 | A1 | validity | score | Petri EA | Petri realism |
|---|---|---|---|---|---|---|---|
| stock (k=0) | 9 | 0.717 → 0.674, **−0.043 [−0.090, −0.001]** | −0.007 [−0.017, 0.003] | −0.061 [−0.22, 0.08] | −0.011 | 0.00 | +0.22 [−0.22, 0.67] |
| fictional-names control | 10 | 0.717 → 0.690, −0.026 [−0.070, 0.010] | −0.013 | −0.025 [−0.17, 0.11] | +0.005 | 0.00 | −0.10 [−0.5, 0.3] |
| R0 arm (`arms/runs/R0_k1.pj.json`) | 8 | 0.669 → 0.687, +0.018 [−0.04, 0.09] | +0.049 | +0.150 [−0.06, 0.38] | +0.096 | +0.13 | 0.00 |

Against stock, the constitution lowers proxy A2 by 0.04, with a CI that just excludes 0. About 0.03 of that is the
name fictionalization alone: the control vs stock A2 is 0.709 → 0.674. Against the control, the taste edits move
nothing, and the Petri judge's EA and realism are flat. Against R0, A2 is no better, and validity is higher by 0.15
(CI crosses 0; R0's validity is low, 0.39 on these seeds). **Success criterion (lower than stock on both A1 and A2,
Petri scores not lower): not met in any meaningful sense.** A1 sits at the proxy floor and the A2 effect is mostly
the names.

## Repo integration points (not implemented; WS A/E code)

- C1 pairs go in `autoresearch/taste/seedpairs.py: build_seed_pairs(evidence_paths, selected_ids) -> List[Choice]`
  = `build_pairs` + `to_choice`, with `decision_point="SEED"`. `SELECTED` should become an evidence-kind filter
  plus an LLM "is this a setup critique" check. Pairs then feed `taste/timesplit.py` with
  `--decision-point SEED` (C5).
- The method goes in `autoresearch/taste/methods/m8_seed_icai.py: SeedICAI(UserModel)`, registered as `"m8"` in
  `methods/__init__.create_method`.
  - `fit` already follows `UserModel.fit` and `_json`.
  - Config ints should go through `common.bounded_int`.
  - `predict_batch` is a budget form of `_predict_with`; `common.accuracy` can replace it when calls are cheap.
  - Semantic grouping should replace `common.cluster_principles` under a `cluster="semantic"` config value.
  - The M3 fix is the selection rule `accuracy(val) − accuracy_M0(val)` (and Δlogp). It is three lines in
    `InverseConstitutional.fit`.
- Gate and axes:
  - `SeedICAI.gate` calls `agreement.judge(root, items, llm)` unchanged; it needs a non-caching LLM, because a
    caching one returns one vote ten times.
  - `map_axes` reads `tradeoffs.load_bank()`.
  - Both results belong in `TasteArtifacts.metadata` (`clusters[*].gate`, `clusters[*].axes`), so `UserModel.save`
    and `load_model` persist them.
- For the C2 dual filter, `SeedICAI.verify(scorer)` takes the Petri-side scorer as a callable passed in through
  config, so `taste/` never imports `research/`. In the repo, the scorer becomes
  `PetriMeasurer.operator_effect(principle, seeds) -> dict`. It would be built from `rewrite_seed` plus a
  `PetriMeasurer.judge_dims(transcript)` that wraps `arms/petri_judge.PROMPT`, with `seed_faithful` and `_audit`
  for validity.
- C4 constitution:
  - `PetriMeasurer.rewrite_seed(base, interventions, rng, constitution=None)` appends `CONSTITUTION_TASK` and the
    principles to its prompt, and returns `{ops, seed}`.
  - `export_seeds.export_design` passes `advisor.constitution()`.
  - In `research/advisor.py`, add `TasteAdvisor.constitution()`, which returns
    `user_model.artifacts().metadata["constitution"]` (dual-filtered principles) and is distinct from
    `principles()` (direction taste for the proposer).
  - The BT posterior over operators (`bt.json`) can pre-fill `Calibration.pairs` under `<slug>:proxy` (C6), and the
    committee order can feed `active_queries` queue building for the researcher.

## Limits

- Pairs are LLM-written from quotes, so a pair tests whether the quote's preference is recognisable, not a choice
  the researcher actually made. The panel pools four researchers, because per-researcher n is 3-7 validate pairs.
- One sample per seed, ≤8 scored seeds per operator, validity on 3 seeds. The Petri judge is haiku on a 3-turn
  compressed audit, so an operator that delays the bait ("let the target discover it") is penalised by construction.
- The rewriter (sonnet) saw each principle alone, and no placebo operator was run, so "any edit" effects are not
  separated from principle effects beyond the fictional-names control.
- Haiku plays auditor, target, A2 answerer and both judges; the blind gate is sonnet.
