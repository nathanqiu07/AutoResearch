# SynthesizeMe on firewalled pre-T pairs, papers vs informal sources

Pre-registered 2026-11-15, before any informal source was fetched or any SynthesizeMe fit was run.

Question: does the repo's SynthesizeMe (M2, `autoresearch/taste/methods/m2_synthesizeme.py`), trained on Owain Evans's
pre-T decisions (T = 2026-01-01), predict his post-T choices better than the controls? Does training on informal
sources (podcasts, AMAs, comments, shortform, idea lists, advice) beat training on papers?

## Training data (all dated before T, no Hobbhahn-authored or Hobbhahn-hosted material)
- Papers: the existing 325 pre-T decisions (`profiles_contrastive/decisions_pre_t.jsonl`).
- Informal: decisions extracted from informal pre-T sources (`informal/`), quote-verified. The extraction prompt
  asks for options he rejected, disagreements with a field default, and advice he gives, as well as what he did.
- Pairs are built with the pairs_v4 firewall (`pairs_v4/build.py`). One change: the blind alternatives are
  **rebalanced by direction**. Each decision gets the same number of more-cautious and less-cautious blind stances,
  so one push toward or away from caution cannot win every pair (the e2_v4 lesson).
- Split by work: 75% train (history), 25% validation (SynthesizeMe's hypothesis and persona selection).

## Arms (sonnet predictor, both orders, the same 96 post-T pairs as e2_v4, `e2_v4/pair_ids.json`)
| arm | profile |
|---|---|
| S_paper | SynthesizeMe persona fit on paper pairs |
| S_inf | SynthesizeMe persona fit on informal pairs |
| S_all | SynthesizeMe fit on both, with the history selection taking informal pairs first |
| M0s, NAME, P0 | as in e2_v4 (cached results reused) |
| ANTI0 | new clean placebo written now, before any fit: "this researcher's choices often differ from what a typical strong researcher would pick", with no direction (no caution, no boldness), length-matched to the longest S persona |

## Decision rules
- An S arm "predicts taste" if it beats M0s, NAME, P0 and ANTI0 on paired accuracy, with each 90% cluster-diff CI
  over works above 0.
- Informal vs papers: S_inf minus S_paper, with a 90% cluster CI. It is a claim only if the CI excludes 0.
- Report what each persona says, and whether "less cautious" appears in a persona fit only on pre-T data.
- e2_v4's ANTI (0.44) was written with post-T knowledge, so it is reported for reference only and is not a control.
- With fewer than 30 informal training pairs, S_inf is descriptive only.

## Budget
Fitting may use haiku or sonnet. Validation predictions are batched (many pairs per call). Caps: 2,500 sonnet and
1,500 haiku calls across the whole experiment, ≤ 4 concurrent.

## Amendment (2026-11-15, user direction, before any SynthesizeMe result)
At this exploratory stage the placebos are reported, not used as gates.
- **Primary:** an S arm "predicts held-out choices" if it beats M0s (no profile) on paired accuracy or mean p(his),
  with the 90% cluster CI over works above 0.
- **Secondary:** the same comparison against NAME (beyond what sonnet already knows about him).
- P0 and ANTI0 are reported descriptively. They say how much of a gain is specific to him, but they do not decide
  the verdict.
