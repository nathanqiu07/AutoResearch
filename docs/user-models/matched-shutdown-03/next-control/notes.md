# Candidate generic control for a later comparison

This is a proposed next-batch artifact. It is not part of the first frozen packet at source commit `09d3ba15774dd7dcf8bdf060d6121196494d2996`. No runtime file, frozen packet, model, setting, seed, or live result was changed for this work. No model calls were made.

`generic-context.json` is authored domain-general research and environment-design guidance. Its persona and every example explicitly identify themselves as instructional inventions. None is an observed user choice, researcher label, source quotation, or empirical result. No content was copied from the Hobbhahn profile or its examples. No held-out or private corpus was read.

Artifact SHA-256: `3dc3ad8e882ed05660dd70b2fed0840bcbed8ae38c7629919c600b792b8c5076`.

## What is matched

- The same top-level fields: `persona` and `past_choices`.
- Eight examples, each containing `id`, `context`, `a_text`, `b_text`, `chosen`, and `rationale`.
- Two plausible alternatives per example, with conditional rationales explaining when the other choice would be useful.
- The same six-A/two-B selected-option presentation as the frozen profile. Reordering alternatives changes no authored recommendation.
- Raw JSON length: **11,103 UTF-8 bytes**, compared with **10,366 bytes** for the frozen profile context including its terminal newline: **7.1% longer**, within the requested 10% bound. This is a byte comparison, not a verified token match. The short generic control in the first packet is a different artifact.

The examples cover tool-state fidelity versus task coverage, background context, repetitions versus breadth, ambiguity, operational consistency, judge validation, separating a repair from a prompt intervention, and efficient observable tool use. They were written to convey useful tradeoffs; there is no repeated filler added solely to meet a length target.

## How a later run should use it

Freeze this file, its hash, the complete wrapper and the resulting rendered auditor prompt before viewing that later batch's results. Give it the same context wrapper, placement, opportunity to influence the auditor and shared setup constraints as the researcher context. A neutral wrapper must accurately identify each source type without calling these fictional choices researcher evidence. Record total rendered input tokens for each arm, not just this file's byte length. The actual target and judge should not receive the control or researcher identities.

Do not replace the first batch's short generic control in place or combine those results as if the interventions matched. Use a new packet/version and disclose the change. Do not tune these examples against the first batch's favorable or unfavorable outcomes. This candidate was authored without inspecting first-batch results.

## What this still does not establish

A comparison would test one particular researcher-derived context against one particular authored generic context. It is not a perfect test of personal specificity. The generic examples are more directly about environment design than many of the researcher's selected examples; authorship, domain relevance, detail, wording and content still differ. Matching structure and approximate length removes some simple explanations, but cannot make all those features identical.

The researcher choices themselves are AI-inferred and their rationales generated. The generic choices are deliberately authored illustrations. Neither collection is direct evidence of the named researcher's actual decisions. A good outcome under the generic control could reflect useful task instructions; a better outcome under the researcher context would not alone prove faithful personal taste or generalization. Report scenario validity, concrete behavior and failures separately before interpreting utility.
