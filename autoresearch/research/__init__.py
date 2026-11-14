"""Open-ended research loop (v2).

v1 (`autoresearch/loop.py`) searches a fixed grid of design knobs against a
simulator; it is the testbed for ablating taste, memory and drift control.
v2 is the loop meant to produce real findings:
  * hypotheses are free-form environment-design interventions proposed by a
    model, steered by the researcher's taste, past findings, and the web;
  * eval-awareness is measured on a *separate target model* by three
    independent signals, not estimated by the generator grading itself;
  * changes are accepted only on statistical evidence and re-confirmed on
    fresh samples before they become findings;
  * taste is a prior whose weight is learned from whether it predicts what
    actually works.
"""
