# Contrastive pre-T profiles of Owain Evans

Built 2026-11-15 by a claude-tastepetri worker. Why: every earlier profile encoded field consensus ("be realistic, don't overclaim"), so a predictor with no
profile already matched it (REPORT.md). These profiles are built to say where he departs from a typical
strong ML-safety researcher, from evidence dated before T = 2026-01-01 only.

## Entry point

```python
import importlib.util
spec = importlib.util.spec_from_file_location("pc_arms", "experiments/taste_petri/profiles_contrastive/arms.py")
arms = importlib.util.module_from_spec(spec); spec.loader.exec_module(arms)
text = arms.get_profile_text("P1+P3", context)   # arm in arms.ARMS; k=5 retrieved decisions by default
```

| arm | file | words | what |
|---|---|---|---|
| P0 | `P0.md` | ~1220 | consensus placebo: the 8 claims the gate called lopsided toward him, same format as P1 |
| P1 | `P1.md` | ~630 | contrast card: the 4 claims that are not consensus under the gate, default vs his choice, 2 verified quotes each |
| P2 | `P2.md` | ~1000 | 12 of 14 bank axes with a pole (2 had no evidence) + 5 induced axes, 1 verified quote each |
| P3 | `retrieve.py` | ~450 at k=5 | his k most similar pre-T decisions to `context` (TF-IDF, `autoresearch/taste/textsim.py`) |
| P4 | `P4.md` | 244 | decision-style vector written by sonnet from P1 + P2 only, "When generic research sense says X, he does Y" |
| P1+P3 | | ~1080 | P1 followed by P3 |

P0 is about twice P1's length (8 vs 4 claims). An evaluator that wants a length-matched placebo should note this.

## Pipeline (`build.py STAGE`)

1. **Select**: corpus docs with `publishedDate` < 2026-01-01 (48), minus the 3 with Hobbhahn as an author
   (CoT monitorability, SAD, evaluations-based safety cases), minus 3 not about his research choices
   (two history essays; BIG-bench, a 450-author paper). 42 docs mapped.
2. **map** (42 sonnet): per doc, `prompts/map.txt` asks for contrasts (field default, his choice, reason,
   verbatim quote, distinctiveness, own/team attribution), evidence on the 14 axes, and candidate new axes.
   It tells the model consensus items are useless. One reply had a stray `,"` that broke JSON; it was repaired by
   hand from the cached reply (`harmless_reward_hacks...`), no new call.
3. **verify**: quotes checked verbatim against the doc with `profiles/_work/verify.py`'s `norm`/`found`.
   449 kept, 9 dropped (194 contrasts, 179 axis items, 76 new-axis items) -> `evidence.jsonl`.
4. **reduce** (1 sonnet, `prompts/reduce_p1.txt`): 12 claims, each with a neutral context, his option and the
   field-default option written in the same tone and length -> `claims.json`. Evidence by id only; the renderer
   swaps in verified quotes, so no model-typed quote reaches a card.
5. **gate** (120 haiku): `agreement.votes` with `agreement.PROMPT`, 5 votes per order (10 per claim), haiku instead
   of the module's sonnet. Verdicts on share of votes for his option: >0.8 consensus, <0.2 contrarian, else
   taste -> `gate.jsonl`.
6. **axes** (1 sonnet, `prompts/axes.txt`): axis evidence + new-axis candidates + all 325 pre-T decisions ->
   positions on the 14 axes and 5 induced axes -> `axes.json`. **gate_axes** (50 haiku) runs the same gate on
   the induced axes (his pole vs the other) to label them -> `gate_axes.jsonl`; nothing is dropped.
7. **render**: `P0.md`, `P1.md`, `P2.md`. **vector** (1 sonnet): `P4.md`, cut from the end to 250 words
   (the prompt orders habits by predictive weight; the 323-word reply lost its last 3 habits).
8. **leak**: `leak_check.json` (below). `retrieve.py build` writes the P3 bank `decisions_pre_t.jsonl`.

### Deviation from the brief
The brief says drop claims with >0.8 share. Lopsided toward his option means consensus, so those go to P0.
Three claims were lopsided the other way (the blind judge picked the field default 9-10 times of 10). They are
the opposite of consensus: exactly where a no-profile predictor goes wrong. They stay in P1. A strict reading
leaves P1 with one claim (K4), which is too thin to be a card.

## Gate result

12 claims: 8 consensus (share 0.9-1.0), 1 taste (K4, 0.4; the judge picked whichever option came first),
3 contrarian (K2 0.1, K7 0.0, K12 0.0). Strict pass rate (not lopsided) 1/12; not consensus 4/12.
Induced axes: phenomenon-first question selection 0.0 and fast early release 0.0 (contrarian);
behavioural-over-mechanistic 0.6, synthetic finetuning 0.6, frontier-API-first 0.8 (taste). None consensus.

## Leakage check (`build.py leak`)

- Provenance: all 42 mapped docs, all 194+179+76 evidence items and all 325 bank decisions come from docs dated
  < T with no Hobbhahn authorship. Latest evidence date 2025-12-19; latest bank date 2025-12-17.
- Text: 0 eight-word runs from any post-T doc (not also in a pre-T doc), and 0 post-T title 3-grams, in P0, P1,
  P2, P4, claims.json, axes.json and the decision bank. Bigrams found only in post-T docs were read by eye: all
  generic phrasing ("the finding", "wait for", "a matched").
- A grep for post-T topics and models (consciousness cluster, conditional misalignment, negation neglect, secret
  loyalties, value leakage, story imprinting, homeopathic, Opus 4, GPT-5) finds nothing in the cards. Hits for
  "owls", "2026" and "Apollo" in evidence/bank are pre-T content (subliminal learning 2025-07; 2026 as a backdoor
  trigger year in a 2025 paper; Apollo named as an org).
- Residual risk: sonnet's knowledge of his post-T work could shape claim wording or the axis reduce, which no
  text check catches. Every claim and axis cites pre-T evidence only.

## Calls

Logged in `calls.log`, cached in `cache/` by prompt hash: sonnet 45 of 70 (42 map, 1 reduce, 1 axes, 1 vector),
haiku 240 of 300 (120 claim gate, 50 axis gate, 70 sanity check). No failed calls.

## Sanity check on the old e2_owain pairs (`sanity_e2.py`)

The 7 old pairs where e2_owain's 4 blind votes were not all for his option (5 works). Contrastive arms
ran through the same persona slot as e2_owain's E_pre (haiku, one sample per order); M0 and E_pre are
e2_owain's recorded predictions. Results in `sanity_e2.json`.

| arm | paired correct (of 7) | mean p(his) |
|---|---|---|
| M0 | 1 | 0.35 |
| E_pre (old) | 1 | 0.44 |
| P0 | 1 | 0.37 |
| P1 | 1 | 0.37 |
| P2 | 2 | 0.43 |
| P4 | 2 | 0.42 |
| P1+P3 | 2 | 0.40 |

P2, P4 and P1+P3 each gain the same one pair (a "three half-baked ideas" item from 2026-11). P1 does
not beat the placebo P0. With 7 pairs from 5 works and one sample each, this shows the arms run end to end in
the predictor and nothing more. The real test is e2_v2 on pairs_v2.
