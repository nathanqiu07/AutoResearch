# judge_transfer: do tonight's findings hold for a non-Claude judge? (pre-registered)

Written 2026-11-15 19:20 UTC by devin-tastepetri, before any call. Motivation: every Petri-judge number tonight comes
from haiku, the same model family that played auditor and target. The real held-out judge is from a different
family. This re-judges the **stored** transcripts (no new audits) with Petri's own judge prompt and rubrics
(`arms/petri_judge.py`, verbatim), using **GPT-6 Sol** (medium thinking) via devin-cli.

Arms re-judged: petri_taste R0, TT2, TB2, TC2; surgery ID, SOFT, NB (all ok samples, k=0-2).

Claims checked (paired per seed, 90% bootstrap over seeds), each with the haiku-judge result:
| claim | haiku judge | transfers if, under GPT |
|---|---|---|
| C1 bait presence is a tell: NB − ID realism | +0.8 [+0.4, +1.1] | > 0, CI above 0 |
| C2 presentation is not: SOFT − ID realism | +0.1 [−0.3, +0.6] | CI includes 0 |
| C3 judge feedback raises realism: TT2 − R0 | +0.6 [+0.3, +1.0] | > 0, CI above 0 |
| C4 taste null: TB2 − TT2 and TB2 − TC2 realism | −0.1, −0.1 | both CIs include 0 |
Same for eval_awareness (secondary). Also reported: per-sample Spearman between the haiku and GPT realism scores.

Budget: about 200 devin-cli calls (GPT-6 Sol medium). No Claude plan use.
