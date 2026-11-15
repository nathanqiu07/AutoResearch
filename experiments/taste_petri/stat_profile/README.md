# Learned statistical profile (no model calls)

`run.py` trains a multinomial naive Bayes on **pre-T decisions only**: Owain Evans's 325 (from
`profiles_contrastive/decisions_pre_t.jsonl`) against 308 from Steinhardt, Carlini, Barnes and Marks (from
`decisions_v2/`, split `pre`). It then scores the post-T attribution pairs from `attrib/`. A pair is correct when
the classifier rates his decision as more Owain-like than the opponent's. CIs are 90% bootstrap over Owain works.
This was not pre-registered: it is an exploratory follow-up to `attrib/` round 2.

| text view | pairs | NB accuracy [90% CI] | for comparison |
|---|---|---|---|
| raw (problem + choice + reason) | 104 | 0.817 [0.757, 0.871] | none |
| round-1 abstraction | 104 | 0.654 [0.591, 0.705] | sonnet NAME 0.756; best LLM profile (P1) 0.733 |
| round-2 fixed template | 86 | 0.663 [0.571, 0.723] | sonnet NAME 0.616 on the same 86 pairs |

Paired on round-2's 86 pairs, NB minus sonnet NAME is +0.047 [−0.029, +0.139], which is not significant.

Reading:
- A profile learned from his past decisions, with no LLM, does about as well as sonnet's prior knowledge of him.
  On round-1 abstraction every LLM-written profile scored at or below the bare name.
- The words it learned are mostly **topical** (trigger, backdoor, truthfulness, finetuning, introspection vs
  attack, defense, gradient, debate, forecast). Its edge comes from research-area residue that survives
  abstraction, not from decision style. This is the same leak `attrib/`'s gates flagged.
- Implication for profile generation: if attribution is the target, a classifier over many past decisions is a
  cheaper and at least as strong profile as a prose card. But with this pair design, neither can be credited
  with taste, because topic is not separated from style.

Run: `python3 stat_profile/run.py` (writes `results.json`).
