# Profile compression methods and a representativeness test

Ideation note, 2026-11-15. Nothing here has been run; 0 LLM calls were made writing it.

Inputs read: `experiments/taste_petri/BRIEF.md`, PLAN.md §3.1 and §6, `autoresearch/taste/` (`profile.py`,
`usermodel.py`, `choices.py`, `timesplit.py`, `tradeoffs.py`, `textsim.py`, `methods/` M2-M7), `data/researchers/evan_hubinger/`
(manifest, corpus front matter) and `experiments/taste_petri/profiles/` (README, Hubinger cards, `evidence.jsonl`).

## 0. Problem statement

A profile `P = C(D_<T)` compresses a researcher's dated work before a cutoff T. It is good when:

1. **Representative**: it carries what is *specific* to this researcher. A profile that also fits the other four
   researchers is field-level boilerplate.
2. **Small**: it fits a proposer or rewriter prompt (target ≤250 words, about the size of the current (e) card).
3. **Predictive**: it predicts choices the researcher made *after* T.

The quantity to maximise is the information about the researcher's future choices per injected token. One way to
measure it is a rate-distortion curve: x = profile tokens, y = held-out accuracy (§2). Two facts about the local
data shape every design below:

- **The existing cards (a)-(e) leak.** They were reduced from evidence dated up to 2026, so any time-split test
  that uses them as-is is a recall test. `evidence.jsonl` carries a date per item, so pre-T profiles can be
  rebuilt by filtering on date. Pre-T evidence counts at T = 2025-04-01: Hubinger 148, Bowman 129,
  Greenblatt 121, Shlegeris 60, Evans 46.
- **Our five researchers are each other's distractors.** They work on the same problems in the same period,
  which is exactly PLAN §6.3's "contemporaneous" distractor class, and it costs no Exa calls. Post-T docs with a
  unique URL and a lead position (solo/first/last) at T = 2025-04-01: Hubinger 11, Bowman 5, Evans 21,
  Greenblatt 41, Shlegeris 30. Bowman is the binding constraint at 5. Hubinger has no `*_timesplit.jsonl`
  pairs yet, so the timesplit pipeline cannot be the test tonight.

**Topic vs taste.** Discriminating Evans (emergent misalignment, fine-tuning) from Greenblatt (control) is easy,
and it shows *interests* (D1), not eval-design taste (D2-D6). The hard, informative pairs are
Greenblatt↔Shlegeris (same org, same agenda) and Hubinger↔Bowman (same org, both alignment auditing). Every
measure below should report those two pairs separately, and the protocol runs a method-only, topic-blind
variant.

## 1. Methods (20)

Each entry gives what the method keeps, its size knob, and the cheapest way to measure whether it is
representative. Measurement codes are defined in §2.

| # | Method | What it keeps / size knob | Cheapest representativeness measure |
|---|---|---|---|
| 1 | **ICAI principles** (M3; card (a)) | 8-18 "prefers X over Y because Z" sentences. Knob: number of principles | LINEUP; VERIFY per principle |
| 2 | **SynthesizeMe persona** (M2) | One paragraph of persona written from reasoning traces, plus 3-5 selected exemplars. Knob: persona length, k | LINEUP; RECON (does the persona regenerate a held-in abstract better than no persona?) |
| 3 | **Exemplar retrieval** (M1/M5) | k verbatim decision quotes, picked at query time by TF-IDF (`textsim.TfIdf`) against the decision context. Knob: k | TIMESPLIT; LINEUP with static top-k. Watch for stylometry: quotes carry voice, so pair it with the topic-blind summaries |
| 4 | **Contrastive chosen-vs-rejected pairs** | "Chose A over B" from `alternatives_named` in `extraction/decisions.jsonl` (timesplit `check` stage), or from distrust items. Knob: number of pairs | TIMESPLIT (it is the native format); ADV (does it reject near-miss directions?) |
| 5 | **Decision tree over D1-D6** (card (b)) | Per decision point, 2-4 if-then rules plus a distrust list. Knob: rules per node | Per-D accuracy on TIMESPLIT pairs grouped by `decision_point`; shows which D-points a profile knows nothing about |
| 6 | **Trade-off stance vector** | A position from -2 to +2 on each of the 14 axes in `data/trackp/tradeoffs.jsonl`, with a short rationale. Knob: axes kept (drop "no evidence") | LINEUP; RW. It shares coordinates with track P (personal), so profiles from both tracks are comparable item by item |
| 7 | **Feature weights** (M4, `TasteProfile.weights`) | 7 numbers over `FEATURES`. Smallest possible. Knob: L2 prior strength | Pairwise accuracy on TIMESPLIT (`choices.prediction_accuracy`). Expect near chance on LINEUP, since 7 numbers rarely separate researchers in one field |
| 8 | **Critic rubric** | Weighted criteria a direction or seed is scored against ("is the bait reachable without leading text: 0-3"). Knob: criteria count | Rank correlation between rubric score and held-out chosen-vs-distractor; RW (do two rubrics from one researcher grade the same seed alike?) |
| 9 | **Recency-weighted profile** | Evidence weighted by exp(-age/τ) before reduction, so the profile tracks the current researcher. Knob: τ | Rolling-origin TIMESPLIT: pick τ on T1 = 2024-10-01, test at T2 = 2025-04-01. Cheap because only the evidence filter changes |
| 10 | **Trajectory vector** (card (d), done properly) | The difference between profiles of [T-24m, T-12m] and [T-12m, T], stated as "moving from X toward Y", plus 3 predicted next projects. Knob: window | FORECAST (generate next projects, compare with real post-T work by TF-IDF against peers' post-T work) |
| 11 | **Taste diff vs peers** | Only what separates this researcher from the other four: "unlike peers, ...". Built from the target's claims plus a peer sample. Knob: statements | LINEUP is its native test; hard-pair accuracy (Greenblatt↔Shlegeris) is the real check |
| 12 | **MDL principle selection** | Greedy: add a principle only if L(principle tokens)·λ + Σ −log2 p(choice \| principles) drops on held-in pairs. Knob: λ, the price per token | The rate-distortion curve itself; VERIFY on held-out pairs to check MDL did not overfit the held-in set |
| 13 | **Verification filter** (M6) | Leave-one-principle-out: keep a principle only if removing it lowers validation accuracy or LINEUP probability on the true author | VERIFY. Cost is about (#principles × validation items), so run it on 8 principles × ~10 items, not 18 × 50 |
| 14 | **Self-consistency / bootstrap core** | Rebuild the profile on k bootstrap resamples of documents; keep principles present in ≥m of k builds | STAB (Jaccard of principle sets across resamples). An unstable principle came from one document, not from the researcher |
| 15 | **Meta-taste: field prior + personal residual** | One shared "alignment-researcher prior" from all five, plus a short residual per person. Inject prior + residual | LINEUP on residual alone vs full. If the residual alone does as well, the prior is wasted tokens. Also gives the shared core every profile should not repeat |
| 16 | **Multi-resolution profile** | The same profile at 1 line / 50 / 250 / 1000 words, made by successive summarisation | Rate-distortion curve on LINEUP; pick the knee. That is the "small enough" answer, measured rather than assumed |
| 17 | **Negative-space profile** | Only what they reject (distrust list, critiques of others' setups). Knob: items | ADV and D3/D4 accuracy. Negative space may discriminate better, because researchers in one field agree on goals and disagree on what counts as evidence |
| 18 | **Simulated questionnaire answers** | The profile answers the 14 stance items and the scenario items in `tradeoffs.py` as the researcher would, with a one-line reason each | RW and LINEUP. It is directly comparable with track P (personal) answers, which gives a common metric across tracks |
| 19 | **Executable critic** | A small Python or regex scorer over seed text (flags "use thinking tags", planted affair emails, unreachable bait). Zero tokens at injection | Agreement of its seed rankings with a profile-conditioned LLM ranking. Representative only of the realism slice of taste; best used as a guard |
| 20 | **Prototype exemplars (k-medoids)** | Cluster pre-T evidence claims by TF-IDF; keep the medoid quote of each cluster. Coverage instead of top relevance. Knob: k | LINEUP vs format 3 at equal word count; tests whether coverage beats salience |

Also considered and ranked lower: a **citation-graph profile** (whom they build on; references are stripped from
the map inputs, so data is missing), a **gated mixture** (a different format per D-point; worth trying only after
per-D accuracy from 5 exists), and an **adversarially trained profile** (iterate the profile against a judge that
tries to confuse it with peers; this overfits the judge).

## 2. Measuring representativeness cheaply

| Code | Test | Calls | What it shows | Failure mode |
|---|---|---|---|---|
| **LINEUP** | Discrimination: the judge sees N anonymised profiles of one format and an unseen, neutralised post-T summary, and says whose it is | 1 per 5 summaries (batched) | Specificity plus predictiveness: post-T work identified from a pre-T profile | Topic or stylometry carries it; controlled by neutral summaries and a topic-blind variant |
| **TIMESPLIT** | `heldout_timesplit.jsonl`: chosen direction vs distractor (named, contemporaneous or generated) | 1 per pair | The PLAN §6.3 metric | Needs Exa-built pairs; distractors may be lopsided (`track_eval.style_leak`, `distractor_gate`) |
| **XDIST** | TIMESPLIT with peers' post-T work as the distractor: "did X pursue A or B", where B is a peer's project from the same months | 1 per pair | Contemporaneous distractors at zero harvest cost | A peer's project may be one X *would* have done; the label is then noisy |
| **RECON** | Given the profile and a neutral problem statement of a held-in or held-out doc, regenerate its abstract; TF-IDF cosine to the real one, minus a no-profile baseline | 1 per doc per arm | Whether the profile carries *how* they attack a problem | Rewards fluent generic abstracts; needs the baseline subtraction |
| **FORECAST** | Profile alone → 3 predicted next projects; score own-vs-peer TF-IDF similarity to real post-T summaries | 1 per researcher per arm | Trajectory and interest prediction | n = 5 researchers, so very noisy |
| **RW** | Rewrite-agreement as a multitrait-multimethod matrix: two formats of one researcher rewrite the same seed; agreement within researcher across formats (convergent) minus across researchers within format (discriminant) | 1 per seed per (researcher, format), plus a judge | Whether the formats encode the *same* person, and whether a format just imposes its own style | Haiku's rewrite style dominates; edits must be classified into a fixed edit taxonomy before comparing |
| **VERIFY** | Accuracy drop when one principle is ablated | principles × items | Which parts of the profile carry signal | Expensive; run on small sets |
| **STAB** | Jaccard of principle sets across bootstrap builds | k builds | Robustness to which documents were sampled | Haiku phrasing varies; match principles with a judge or embeddings, not strings |
| **ADV** | Accuracy on the hardest distractors: same-org peer, same topic, or "profile-bait" directions that match the profile's keywords but break one of its principles | 1 per pair | Keyword matching vs understanding | Generating good bait costs calls |

Rule for all of these: the profile is built only from evidence dated before T, every name, handle and org is
masked in profiles and test items, and a **names-only arm** ("Profile: Evan Hubinger") is run as the baseline
for haiku's parametric knowledge of these people. A compressed profile that does not beat the bare name adds
nothing for haiku.

## 3. The current ICAI pipeline: critique and upgrades

Read for this section: `autoresearch/taste/methods/{common,m2_synthesizeme,m3_icai,m5_hybrid,m6_verified,m7_confident}.py`
and `usermodel.py`.

### 3.1 What M3 does today

- **History**: `selected_history` keeps at most 5 choices (`max_history=5`), sampled with the seed.
- **Propose**: one call per choice, at most 2 principles each (`principles_per_pair=2`), so at most 10 proposals.
- **Cluster**: `common.cluster_principles`. This is lexical TF-IDF with complete linkage at cosine ≥ 0.75, plus a
  guard that keeps negated and plain statements apart. The medoid represents each cluster.
- **Rank**: each representative is scored *alone* with `accuracy(rows, ...)` on the same ≤5 rows it was proposed
  from. Ties break on support, then on proposal index. The top `max_principles=5` are kept.
- **What reads `val`**: M3's `fit` never does. M5 passes `val` to M3, but only M2 uses it. The only held-out
  check on principles is M6's leave-one-out on `val`, which removes strict harms and keeps ties.
- **Cost**: up to 5 + 10 × 5 = 55 calls per fit.

### 3.2 Problems, from the compression view

1. **It compresses choices, not the corpus.** M3 sees at most 5 rows. A public-track researcher has 120-220
   verified evidence items, and none of them reach M3 until they are turned into `Choice` rows, after which 5
   are sampled.
2. **Selection is in-sample.** A principle written to explain row r predicts row r by construction. With 5 rows,
   accuracy takes only six values (0, 0.2, ..., 1), most proposals tie near the top, and the tie-breaks decide.
   The original ICAI tests every principle on the whole dataset.
3. **There is no baseline subtraction.** A principle that encodes what any reasonable person prefers scores as
   well as a personal one. The score should be the lift over M0 (`_predict_with` with no principles): accuracy
   on the rows M0 gets wrong. For representativeness this is the difference between a field prior and a
   profile.
4. **The clustering does almost nothing.** "Prefers realistic settings" and "favours deployment-like
   environments" share almost no tokens, so at 0.75 TF-IDF cosine nearly every proposal is its own cluster.
   Support is then about 1 everywhere, and the support tie-break carries no information.
5. **k = 5 is fixed, and principles are ranked independently.** Two redundant principles can both be kept while
   a complementary one is dropped. `common.forward_select`, a joint greedy selection, already exists and is used
   by M2, not M3.
6. **Principles carry no decision point.** At D3 (accept a result), a D1 principle about which topics to pursue
   is noise in the prompt.

### 3.3 How a corpus should feed ICAI

Three routes. I recommend the third.

- **Route 1: corpus → pseudo-choices, then M3/M6 unchanged.** Sources of pairs, best label quality first:
  - (a) **The decision vs the named alternative**: `alternatives_named` in `extraction/decisions.jsonl`
    (timesplit `check` stage). It is the researcher's own rejection, so it has the cleanest label. It needs the
    Exa `extract` plus paid `check` stages, which do not exist for Hubinger yet.
  - (b) **The direction taken vs a distractor**: timesplit `pairs`. The pre-T pairs become history, and the
    post-T pairs are the test.
  - (c) **A claim vs a peer's claim at the same D-point**: from the other researchers' `evidence.jsonl`, at zero
    cost. The label is noisy where X would also endorse the peer's claim. Drop pairs that an LLM check calls
    compatible.
  - (d) **A claim vs a generated contrary claim**: the cheapest, but lopsided. M0 already gets a strawman right,
    so the pair carries no personal signal. Use it only behind the M0 filter: keep pairs M0 gets wrong or is
    unsure about.
- **Route 2: corpus → principles directly.** This is what `profiles/_work` did: map each document to typed
  items, verify each quote, then reduce. It is ICAI's propose-and-cluster with documents as the unit, but it has
  no test or filter step.
- **Route 3 (recommended): propose from documents, select on pseudo-choices.** Route 2 gives coverage across the
  corpus. Route 1 makes each principle earn its place by predicting choices.

### 3.4 Should clustering be semantic?

Yes, and it is cheap to change. One LLM grouping call per researcher over up to about 200 proposals ("group by
meaning, keep contradicting statements apart, return groups of ids") does it; reduce.py already did this
implicitly. Local embeddings would also work, but I have not checked whether an embedding model is installed,
and no API keys are set.

Keep the contradiction guard as a post-check: ask the same call to flag opposing statements within a group.

Count support as distinct documents and distinct years, not proposals. A principle backed across three years
is taste. A principle backed by one paper is a project detail.

### 3.5 Should selection be held out?

Yes. Use a rolling time split inside the pre-T window:
- **Propose** on documents dated before T−12m.
- **Select** on pseudo-choices from [T−12m, T).
- **Test** after T.

Selection then measures predictiveness, the property we want, and the "explains its own row" bias goes away.
On PersonalRewardBench the analogue is the existing history/val split. M3 should read `val` and rank by
`accuracy(val) − accuracy_M0(val)`, falling back to in-sample ranking only when `val` is empty, and record that
in `verification_status`. That change is in WS A's code, so it goes to its owner rather than being made here.

### 3.6 Is 5 principles enough? (MDL)

Five is a default, not a measured value. In MDL terms, add principle p only if the drop in validation log-loss,
in bits, exceeds λ · tokens(p). Two practical limits apply:
- **Data caps k.** Validation accuracy moves in steps of 1/n_val. With about 20 pairs, a principle must flip at
  least 2 of them to stand out from noise, which caps k at roughly n_val/4.
- **Principles interact.** Prompt dilution means selection should be joint (`forward_select`), not per
  principle.

My expectation is that corpus researchers support 8-12 principles. The (a) cards have 15-18, from 70-92
evidence items. PRISM-style users probably support 3-5. Sweep k ∈ {3, 5, 8, 12, all}: that sweep is the
rate-distortion curve (method 16).

### 3.7 Our profile formats as M2/M3/M5 artifacts

| Format (`profiles/<slug>/`) | `TasteArtifacts` slot | Usable directly? |
|---|---|---|
| (a) principles | `principles` (bold headlines only; the quotes go to `metadata`) | Yes. It is Route 2 ICAI. There are 15-18 per researcher, so either raise `max_principles` or let M6 filter them |
| (b) D1-D6 card | `principles`, tagged by D-point | Partly. `_predict_with` has no D-point argument, so put the D-point in `context` or route rules by `Choice.decision_point` |
| (c) transfer card | `exemplars`: each move becomes `Choice(context=seed snippet, a=before, b=after, chosen="b")` | For D2 seed rewriting only |
| (d) extrapolation | `assumptions` with credences ("will pursue X": 0.6), checkable by time split | Not a prediction slot |
| (e) taste vector | `persona`: 1,360-1,530 characters, under `max_persona_chars=1600` | Yes by size. It is written in the second person for seed rewriting ("You rewrite seeds the way..."), so reword it to the third person before using it for D3-D6 |
| `profile.json` weights | `weights` | Formally yes, but the weights are LLM-estimated, not fitted |
| `evidence.jsonl` | M5 `retrieval_pool` | Once converted to pseudo-choice dicts (`retrieve` reads `context`, `a_text` and `b_text`) |

An "M5-corpus" user model is therefore buildable without new method code:
- `persona` = (e) reworded to the third person;
- `principles` = (a) headlines;
- `retrieval_pool` = evidence converted to pseudo-choices;
- then M6's leave-one-out on time-split validation pairs.

Set `model._artifacts`, as `load_model` does, and `UserModel.predict` works.

**Caveats.** All five card sets were reduced from evidence dated through 2026, so they leak in any time-split
test (the (a) cards cite post-2025-04 quotes in 2-10 principles per researcher). Task-conditioned formats ((c),
(e)) project taste onto seed rewriting, where all five researchers converge on "strip eval cues". Expect them to
discriminate *worse* on LINEUP even if they steer rewrites better. That tension between representativeness and
usefulness is why the protocol below compares them directly.

## 4. Tonight's protocol: post-T lineup (95 haiku calls planned, cap 100)

**Question.** At equal size (≤250 words), which compression of pre-2025-04 work best identifies each
researcher's post-2025-04 work among five same-field peers, with topic visible and topic-blind? The arms must
include the current M3-style principles, our corpus-derived (a) principles and the (e) taste vectors.

**Cutoff.** T = 2025-04-01. "Pre-T" means `evidence.jsonl` rows with `"" < date < T` (undated rows dropped).
Test items are corpus docs dated ≥ T.

**Arms.** Each arm is one profile per researcher, at most 250 words, with names, orgs and model names masked
(except NAMES).

| Arm | What it is | Leakage | Build calls |
|---|---|---|---|
| NAMES | "Researcher: <full name>", unmasked. Measures haiku's prior knowledge | n/a | 0 |
| EX | Raw pre-T verbatim quotes (M1 at equal budget) | clean | 0 |
| M3 | The current M3 procedure on 5 pre-T pseudo-choices (§4.2 Step 1) | clean | 10 |
| A_pre | (a) headlines whose principle cites at least one pre-T quote | semi: the wording saw post-T evidence | 0 |
| A_full | (a) headlines in card order, up to 250 words | leaky | 0 |
| E_pre | (e) rebuilt by haiku from pre-T evidence with the reduce prompt's (e) instructions | clean | 5 |
| E_full | (e) as it is | leaky | 0 |
| DIFF | Taste diff vs peers, from pre-T claims (method 11) | clean | 5 |

(a) principles with a pre-T quote: Hubinger 15/17, Bowman 13/18, Greenblatt 11/16, Shlegeris 10/17, Evans 5/15.
A_pre is therefore thin for Evans; report it as such.

### 4.1 File layout (all new files under `experiments/taste_petri/ideas/compression_eval/`)

```
compression_eval/
  run.py                    one script, subcommands: select, build, neutralize, lineup, score
  prompts/                  m3_propose.txt m3_reconstruct.txt e_pre.txt diff.txt neutralize.txt lineup.txt
  mask.json                 strings to mask -> [PERSON]/[ORG]/[MODEL]: the `banned` lists from all five
                            data/researchers/<slug>/identity.json, full names, first names (Evan, Sam, Owain,
                            Ryan, Buck), Redwood, Truthful AI, Anthropic, OpenAI, AXRP, 80,000 Hours,
                            Claude, GPT, Llama, Qwen, Gemini
  heldout/docs.jsonl        25 rows {doc_id, slug, date, author_position, path}; text never copied
  heldout/summaries.jsonl   25 rows {doc_id, slug, full, method_only, leak_hits}
  profiles/<slug>/          NAMES.md EX.md M3.md A_pre.md A_full.md E_pre.md E_full.md DIFF.md (each <=250 words)
  profiles/<slug>/m3_trace.json   pseudo-choices, proposals, clusters, reconstruction matrix
  lineup/<run>_<arm>_b<k>.json    raw reply + parsed probabilities per batch (run in {L1, L2, L3})
  cache/<sha256>.json       prompt-hash cache, so a re-run costs 0 calls
  calls.log                 one line per real CLI call: time, step, arm, exit code
  results.json, results.md
```

CLI: `autoresearch.llm.ClaudeCLILLM(model="haiku")` already wraps `claude -p` with tools, MCP and settings off,
from an empty temporary directory. Or reuse the wrapper in `profiles/_work/steer_test.py`. `run.py` keeps a
global counter, refuses call 101, and logs every call. With 4 workers at about 20 s per call, the run should
take 10-15 minutes.

### 4.2 Steps

**Step 0, select (0 calls).** For each of the five slugs (`evan_hubinger samuel_bowman owain_evans
ryan_greenblatt buck_shlegeris`), list corpus docs with `publishedDate ≥ 2025-04-01` (read with
`timesplit.read_doc`) and keep a doc only if:
- its URL and its normalised title (lowercase, first 60 characters) occur in exactly one of the five corpora
  (drops co-authored papers such as Alignment Faking);
- `author_position` is not `middle`;
- the front-matter `authors` does not contain Hobbhahn;
- its title does not match `AXRP|podcast|episode|#\d+|80,000 Hours|interview` (podcasts are mostly the
  interviewer's framing);
- its body is at least 3,000 characters.

Take 5 per researcher, evenly spaced by date (indices `round(i*(n-1)/4)`, i = 0..4). Bowman has exactly 5
eligible docs before the podcast filter; if the filter leaves him with 4, use 4 and note it. Write
`heldout/docs.jsonl`.

**Step 1, build (20 calls).** Pre-T evidence comes from `experiments/taste_petri/profiles/<slug>/evidence.jsonl`,
masked with `mask.json`.

- **EX (0 calls).** Rows of kind principle, heuristic, distrust or realism_move, sorted by relevance 3 first,
  then solo/first/last before middle, then newest first. Append `- (Dk) "quote"` lines until 250 words.

- **M3 (10 calls, 2 per researcher).** This is the current procedure, batched to fit the budget.
  - *Pseudo-choices* (Route 1c, 0 calls). Take the target's pre-T rows of kind principle, heuristic or
    distrust. Pair each with a random pre-T claim by a peer at the same `dpoint` (seed 0). Context: "At decision
    point Dk, which position does this researcher hold?" a/b = the two claims in random order. Pick 5 exactly
    as `selected_history` does: sort by identity, then `random.Random(0).sample`.
  - *Call 1, propose.* "For each of these 5 choices, propose at most 2 preference principles explaining it."
    This gives at most 10 proposals. The real M3 makes 5 separate calls; batching is a deviation.
  - *Cluster (0 calls).* The real `autoresearch.taste.methods.common.cluster_principles(proposals, 0.75)`.
  - *Call 2, reconstruct.* For each representative and each of the 5 pairs, "given only this principle, which
    option?" returned as one matrix. The real M3 makes one call per cell; batching is a deviation.
  - *Select.* Accuracy on the same 5 rows (in-sample, as today), ties broken by support and then index; keep
    the top 5. Save `m3_trace.json`.

- **A_pre / A_full (0 calls).** Parse `a_principles.md` into numbered blocks, keep the bold headline text only,
  and take quote dates from `(YYYY-MM-DD;`. A_pre keeps blocks with at least one quote dated before T. Both
  arms take headlines in card order until 250 words.

- **E_pre (5 calls).** The "(e) Taste vector" paragraph of `profiles/_work/reduce_prompt.txt` with {NAME} set
  to "this researcher", fed the pre-T evidence claims. Using haiku, not sonnet, is a deviation from how (e) was
  built; note it.

- **E_full (0 calls).** The existing `e_taste_vector.md`, with its HTML comment stripped and names masked.

- **DIFF (5 calls).** Input: the target's pre-T claims, plus 60 pre-T peer claims (seed 0) labelled PEERS.
  "Write 8 statements of how TARGET differs from PEERS on how to design, run and interpret evaluations and
  alignment experiments. Each starts 'Unlike peers, ...'. Leave out anything PEERS also hold. ≤250 words."

Post-check every profile: at most 250 words (truncate at a line boundary), and 0 mask-regex hits (log any and
re-mask). Record word counts.

**Step 2, neutralize (5 calls).** Batch 5 docs per call; one batch per researcher is fine here, because the
summariser is not judging. Input: for each doc, the body after front matter, with lines containing any mask
string dropped, capped at 6,000 characters. Output JSON per doc:
- `full`: ≤90 words. The problem chosen, what was done and measured, what was concluded and how strongly.
- `method_only`: ≤70 words. The same, with the specific topic replaced by a generic phrase ("a misaligned
  behaviour", "a safety technique"), keeping only choices about evidence, setup realism, measurement,
  interpretation and claim strength (D2-D6).
- Both: plain register, no names, orgs, titles or model names ("a frontier chat model").

Run the mask regex on the outputs and record `leak_hits`. Read 5 summaries by eye before Step 3.

**Step 3, lineup (70 calls).** One call judges 5 summaries against the 5 profiles of a single arm.
- **Batching.** Shuffle the 25 summaries with the run's seed and cut them into 5 batches of 5. The composition is
  random, so a batch may hold two docs by one researcher and none by another. The prompt says so, which stops a
  one-to-one assignment from earning points.
- **Order.** Within each batch, randomly permute the profiles and label them P1-P5 (a new permutation per batch).
- **Prompt.** "Five researcher profiles describe work up to early 2025. Five anonymous summaries describe later
  work. For each summary independently, give the probability that each profile's researcher did this work.
  Several summaries may share a researcher; some researchers may have none. Return JSON
  `{"S1": {"P1": p, ..., "P5": p}, ...}`, with each row summing to 1."
- **Runs.**
  - **L1**, full summaries, seed 1: all 8 arms × 5 batches = 40 calls.
  - **L2**, method-only summaries, seed 2: NAMES, M3, A_pre, E_pre, DIFF × 5 = 25 calls.
  - **L3**, noise floor: A_pre on full summaries again, seed 3 (new batches and label order) = 5 calls.
- A parse failure is retried once, from the slack.

**Step 4, score (0 calls).** For each arm and run:
- **top-1 accuracy** over 25 docs (chance 0.20);
- **mean p(true author)** (chance 0.20) and **log-loss**;
- a **5×5 confusion matrix**, plus **hard-pair accuracy**: on the Greenblatt and Shlegeris docs, p(true) /
  (p(Greenblatt) + p(Shlegeris)), and the same for Hubinger and Bowman;
- **collapse**: the largest share of picks going to one profile (above 0.4 means the arm is just choosing the
  longest or most generic profile);
- **noise floor**: the share of docs whose top-1 pick differs between L1-A_pre and L3-A_pre.

Add word counts and pre-T evidence counts per arm and researcher. Write `results.json` and a short `results.md`.

**Budget.** 20 + 5 + 40 + 25 + 5 = 95 calls, 5 spare for retries, hard cap 100.

### 4.3 Decision rules (fixed before the run)

- **Chance.** With 25 docs, ≥10 correct beats 0.20 at p = 0.017 (one-sided binomial); 9 gives p = 0.047.
- **Arm vs arm.** An exact sign test over the docs where exactly one of the two arms is right; 8 of 9 discordant
  docs gives p = 0.04. With n = 25, only gaps of about 25 points or more will show. Smaller gaps are ties.
  Any gap below the L1-vs-L3 flip rate counts as noise.
- **Value over prior.** An arm adds value over haiku's prior only if it beats NAMES on both L1 and L2.
- **Ranking.** Rank the clean arms (EX, M3, E_pre, DIFF) and A_pre by the mean of L1 and L2. L2 (topic-blind)
  is the test of eval-design taste. If every arm is at chance on L2, these formats carry interests, not method
  taste, and that is worth knowing before the Petri rewriter relies on them.
- **The three questions the coordinator asked**, answered by these comparisons:
  - **M3 vs A_pre.** Does compressing 5 choices lose to compressing about 100 evidence items? I expect M3 < A_pre.
    If M3 ≥ A_pre, corpus coverage is not what limits representativeness.
  - **A_pre vs E_pre.** Do principles discriminate better than the task-conditioned persona? I expect yes (§3.7).
  - **A_full − A_pre and E_full − E_pre.** How much does leakage inflate the existing cards? A gap above the
    noise floor means earlier uses of the full cards as evidence of *prediction* must be downgraded.
- **Scope.** This protocol measures representativeness, not usefulness for E3b. The existing steering test showed
  profiles trading elicitation for realism, so the winning format still needs the bait-keeping guard and the
  proxy steering check before it goes into `export-seeds --condition taste_real`.

### 4.4 Known weaknesses of this protocol

- **Small n.** There are 25 docs. Bowman contributes ≤5, all from the same 12 months.
- **Shared-model bias.** Haiku is builder and judge, so it may recognise its own phrasing in M3, E_pre and DIFF,
  but not in EX or the sonnet-written A and E_full. For a second opinion, re-run only L1 with sonnet as the
  judge (40 calls) on another night.
- **M3 is batched.** The M3 arm uses the real clustering code, but batched propose and reconstruct calls, and
  peer-claim pseudo-choices (Route 1c) rather than real decisions. It approximates "current M3 on corpus-derived
  choices"; it is not the class itself.
- **Inherited lens.** Evidence items were extracted by sonnet with a realism-heavy selection (98 of about 540
  docs), so every arm inherits that lens. Evans and Shlegeris have thin pre-T evidence (46 and 60 items).
- **Neutralisation.** It may fail to strip topic in `method_only`; check by eye and count `leak_hits`.
- **Masking.** Masking "Anthropic" and model names removes a real taste signal (which models someone chooses to
  study), in exchange for blocking affiliation shortcuts.
- **Gaming check** (the brief's labels). LINEUP can be passed by keyword overlap, and a profile tuned to win it
  would bloat with topic words. That is GAMING-adjacent; L2 and later ADV-style profile-bait guard against it.
  As a representativeness measure, the lineup is LEGIT.

## 5. Follow-ups after tonight

1. **Route 3 ICAI ("M3-corpus").** Propose from documents (the existing map items), cluster semantically by
   distinct-document support, select with `forward_select` on held-out pseudo-choices by lift over M0, and pick
   k by the MDL sweep. Run the real `InverseConstitutional` class through `ClaudeCLILLM` on timesplit pairs once
   Hubinger's `heldout_timesplit.jsonl` exists, so the batched approximation is checked against the code.
2. **M5-corpus** (§3.7): persona (e, third person) + principles (A_pre) + an evidence retrieval pool, with M6
   filtering on TIMESPLIT.
3. **Rate-distortion sweep** (method 16) on the winning format: 50/250/1000 words, LINEUP only, about 45 calls.
4. **MTMM rewrite-agreement** (RW) on 3 dev seeds × 5 researchers × 2 formats (30 rewrites + 6 judge calls),
   to see whether the winning format steers rewrites in a researcher-specific way or haiku's own style swamps it.
5. **Recency weighting** (method 9) with a rolling-origin τ: T1 = 2024-10-01 to choose τ, T2 = 2025-04-01 to test.
6. **Stance vector and forecast.** The trade-off stance vector (method 6) and the FORECAST measure were cut from
   tonight's budget; add them to the next lineup.
