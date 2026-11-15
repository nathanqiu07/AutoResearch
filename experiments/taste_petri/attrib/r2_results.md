# Attribution round 2: template re-abstraction and leak gates

Pre-registered as PROTOCOL.md "Amendment: round 2".

**Outcome: the leak survives fixed-template abstraction, so the profile arms were not run.**

| gate | value [90% CI over Owain works] | threshold | result |
|---|---|---|---|
| 1. Bag-of-words naive Bayes, his Owain work held out (free) | **0.686** [0.627, 0.768] | ≤ 0.65 | **fail** |
| 2. Sonnet NAME alone, both orders | **0.616** [0.506, 0.708] | ≤ 0.65 | pass |

Both gates had to pass for the arms to run. Gate 1 failed, so per the amendment I stopped. Gate 2 ran anyway because
the amendment's run order puts it second and the controller asked for both values.

## Pipeline and call counts
- **`r2_abstract.py abstract`.** All 356 post-T decisions (Owain 106, Barnes 66, Marks 65, Carlini 62,
  Steinhardt 57; no Hobbhahn) were re-rendered by sonnet in 12-item batches, with researchers mixed in each batch.
  - The fixed template is situation / options considered / choice ("Chose ...") / reason ("No reason stated." if none).
  - The banned list has 111 words: the top 40 discriminative words for each side of round 1's bag-of-words model
    (smoothed doc-frequency log ratio, df ≥ 3) plus 39 genre words. It is stored in `r2_leak.json`.
  - The leak check flags any banned word (or a genre stem such as evaluat-, generali-, transfer-, perform-, publish-),
    a title 3-gram, or ≥ 2 stoplist terms, using round 1's stoplists.
- **`r2_abstract.py pairs`.** Pairing and trimming are the same as round 1, with TF-IDF on `situation`. That gives 86
  pairs over 10 Owain works, all from the first pairing pass. Opponents: Barnes 28, Marks 22, Carlini 20,
  Steinhardt 16. Gate 1 results are in `r2_gate_bow.json`.
- **`run.py --pairs r2_pairs.jsonl --subset in_name --sonnet NAME --line r2_name --out r2_name_`.** This is the same
  predictor as round 1. Output is in `r2_name_results.json` and `r2_name_results_tables.md`.

**Calls:** 45 sonnet for abstraction (cap 45) and 172 sonnet for NAME (cap 220). No arm calls (cap 700, unused).
0 errors, $4.30. Everything is cached and logged in `calls.log` under the `r2_abstract` and `r2_name` lines.

## Leak check (lexical)

| round | flagged | banned word | ≥ 2 stoplist terms | title 3-gram |
|---|---|---|---|---|
| 0 | 182 / 356 | 70 | 137 | 0 |
| 1 (180 re-rendered with their terms forbidden) | 60 | 34 | 32 | 0 |

The budget ran out after round 1. The 60 items still flagged were excluded: Owain 20, Steinhardt 16, Marks 9,
Barnes 9, Carlini 6. That leaves 86 of his 106 decisions.

## Gate details
- **The bag-of-words leak shrank but did not go away:** 0.878 in round 1, 0.686 now.
  - Words still leaning to Owain: condition, hypothesis, wishes, property, odd, belief, explanation.
  - Words leaning to the others: problems, judge, people, weakness, aids, approach, deciding, items, checking.
  - The genre difference survives the template: his items study a property of a system, theirs build or judge an
    approach.
- **Sonnet NAME fell from 0.756 to 0.616** (mean p(his) 0.564).
  - By opponent: Barnes 0.750, Carlini 0.700, Steinhardt 0.500, Marks 0.455.
  - 38 of 172 NAME replies still name "emergent misalignment".

## Deviations and caveats
- **Re-render budget.** Round 0 left 182 items flagged, but the budget covered only 180 re-renders in a single round (the plan allowed two).
  The 2 items not re-rendered are among the 60 excluded.
- **Uneven exclusion.** Excluding flagged items removes Owain's decisions at a higher rate (19%) than the others'
  (16%). The items most likely to leak may be exactly the ones dropped, so the gates may slightly understate the leak
  on the full set.
- **Barnes pairs still leak to sonnet** (0.75). Her post-T decisions are often organisational choices.
- **No profile arm ran, so no taste claim is possible from round 2.**
- **One way forward** is to match pairs on the bag-of-words score, picking opponent decisions that the classifier
  rates as Owain-like, instead of abstracting harder. That would need a new amendment.
