# Personal track: a trade-off questionnaire for eval-design taste

Date: 2026-11-14. Workstream B (personal track, `autoresearch/taste/trackp.py`).

## Intent

The personal-track seed questionnaire (`trackp seed-pairs`) should measure a researcher's
eval-design **taste**: where they sit on trade-offs that good researchers resolve differently.
Today every seed pair asks one D1 question ("which intervention would you test first?") over
two options from `ideas.LIBRARY`, and some of those pairs have a near-correct answer, so they
partly measure knowledge of the field. The user model also gets no seed data for D2–D6.

The new questionnaire is built around the design questions in published eval-design primers,
each recast as a trade-off axis with two defensible poles, and each asked two ways:

* **Stance item:** the axis in general ("in general, more items or more samples per item?").
* **Scenario item:** the same axis inside one EvalAwareBench item ("for this environment,
  5× more variants, or 5 samples per variant?").

Asking both shows the person's general position and whether it holds in concrete cases.

## Goals

* Every pair is a trade-off: both options are defensible to a competent evals researcher.
* Cover the primer themes and all of the loop's decision points D1–D6.
* Scenario items come from two sources: templates written with the axis (A) and LLM-written
  item-specific pairs generated from the axis definition (B).
* A balance check flags pairs that look one-sided, so correctness doesn't creep back in.

## Non-goals

* No change to `Choice`, `UserModel.fit`, the hold-out rule, labels, recheck or the loop.
* No graded-strength answers; answers stay a forced choice plus an optional reason.

## Anti-goals

* **No Hobbhahn material in any item.** He is one of the testers. Nothing he wrote or said
  is a source: not Apollo's "We need a science of evals" or "A Starter Guide For Evals", and
  not notes of his talks. Every axis cites a non-Hobbhahn source.
* No pair where one option is plainly better; that pair measures knowledge, not taste.

## Sources (all non-Hobbhahn)

* Bean et al., "Measuring what Matters: Construct Validity in LLM Benchmarks", NeurIPS 2025,
  arXiv 2511.04703.
* Reuel et al., "BetterBench", NeurIPS 2024, arXiv 2411.12990.
* Ganguli et al. (Anthropic), "Challenges in evaluating AI systems", 2023.
* Miller, "Adding Error Bars to Evals", arXiv 2411.00640, 2024.
* Anthropic, "Demystifying evals for AI agents", 2026.
* METR, "Guidelines for capability elicitation", 2024.

## The axes

One row per axis in a hand-written bank. Poles are written so neither is the "right" answer.

| Axis | Pole 1 | Pole 2 | Decision point | Source |
|---|---|---|---|---|
| construct-scope | narrow operational definition, one sub-component | broad coverage of the phenomenon | D1 | Bean |
| purpose | inform a concrete deployment decision | build scientific understanding | D1 | BetterBench |
| control-vs-realism | controlled synthetic setup, one variable changed | messy realistic setup, many cues at once | D1 | Bean; Anthropic 2026 |
| scale-vs-craft | many generated items | a few hand-built environments | D2 | Ganguli 2023 |
| elicitation | maximum effort (scaffold, best prompt) | default deployed behaviour | D2 | METR |
| grading | LLM judge over many items | human or rule-based grading over fewer | D2 | Bean; Anthropic 2026 |
| awareness-signal | ask the model directly whether it is in an eval | infer awareness from behaviour and reasoning only | D2 | PLAN §A1–A2 |
| items-vs-samples | more distinct items | more samples per item | D2 | Miller |
| evidence-bar | accept on a modest, pre-registered effect | hold out for a large or replicated effect | D3 | Miller |
| breadth-vs-depth | drop a mixed direction, try a new one | stay and find out why it is mixed | D4 | Bean (failure modes) |
| reading | read transcripts in depth | trust aggregate metrics, spot-check | D5 | Anthropic 2026; Bean |
| claim-scope | a narrow claim tied to this setup | a broader claim the evidence suggests | D6 | Bean; BetterBench |
| openness | private held-out data | public, reproducible data | D6 | Bean; BetterBench |

Each bank row holds: `axis`, `decision_point`, `sources`, the stance `question` with
`pole_1`/`pole_2`, and a scenario `template` (question plus two option texts that read
against an item's context).

## Approaches considered

* **A. Hand-written bank, template scenarios.** Every option reviewed; scenarios formulaic.
* **B. Hand-written stances, LLM-written scenarios.** Richer item-specific scenarios; an LLM
  tends to write one option as the better one, so the balance check matters more.
* **C. Tag the existing intervention pairs by axis.** Smallest change, stays D1-only, keeps
  pairs with a clear winner. Dropped.

**Chosen: A and B together** (the user's call). Stance items and template scenarios come from
the bank (A); `--llm-scenarios K` adds K LLM-written scenario pairs per item from the axis
definitions (B). Both kinds of scenario go through the balance check.

## Generation, recording and the balance check

* `trackp seed-pairs` writes stance items (one per axis, item-free context) and scenario
  items (axis × EvalAwareBench dev items, round-robin as today) to `seed_pairs.jsonl`. Each
  row gains `axis`, `form` (`stance` | `scenario`), `origin` (`bank` | `llm`),
  `decision_point`, and `a_pole`/`b_pole` (1 or 2) so stance-vs-scenario consistency can be
  computed later. The consistency report itself is out of scope for this build (my call). The
  intervention-pair generator stops being the default; `ideas.LIBRARY` still feeds the loop.
* Recording an answer writes a `Choice` with `decision_point` from the bank row (not a fixed
  `"D1"`). The axis stays on the pair row and is not used as `group_id`: `UserModel.fit`
  refuses a `group_id` that spans history and val (my call, after the builder check).
* **LLM scenarios (B).** The prompt gets the item context and the axis row and must return two
  options, one per pole, of similar length and specificity. Paid: off by default; the runbook
  already says to ask the user before paid calls.
* **Balance check** (my calls). The checker is the no-history user model (`m0`, method
  `base`), reusing `predict` and its probabilities on each pair in both orders; a pair it
  gives the same pole ≥ 0.8 in both orders is flagged `one_sided`. Flags and review decisions
  go to a sidecar `balance.jsonl`, so `seed_pairs.jsonl` stays append-only. LLM-written pairs
  are not pending until checked and not flagged (or approved); bank pairs are pending without a
  check, because each was reviewed when written. Reviewing is `trackp review`, done by someone
  who is not the person answering (Ethan, who is not a taste source): approve or drop.
* WS A is told through `agentctl post` that D1 seed pairs are no longer intervention pairs,
  in case a feature-based method relies on them. PLAN §12.2's seed-choices text is updated.

## Constraints

* `trackp.py` is WS B's file. Tests run with `python3 -m unittest discover -s tests -t .`.
* Pair ids stay stable hashes; the 20% hold-out is fixed by hashing them. The split is
  uniform per pair, with no grouping of a stance item and its scenarios (the user's call).
* No answers are collected yet, so replacing the default generator loses nothing.

## Left to the builder

* The exact wording of each axis's stance question, poles and template, within the table.
* The split between stance and scenario items for the default `--n`.
* The prompt for LLM-written scenarios.
