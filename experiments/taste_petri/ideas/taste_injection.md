# Taste injection for Petri seed rewrites: 26 ideas, ranked

Ideation only, 2026-11-15. No LLM calls, no runs. I read `BRIEF.md`, `anatomy/metric_anatomy.md`,
`lit/lit_review.md`, the five profiles in `profiles/` (all formats, README and the n=3 steering test), PLAN §3.1, §6
and §7, and `autoresearch/research/{ideas,advisor,loop,export_seeds,petri_measure}.py`. The question: how can taste
*extrapolated from a researcher's past work* enter the loop so that the R1 seed rewrites beat stock v2 seeds on both
A1 and A2, with validity kept?

## 0. Constraints that decide the ranking

1. **Wording barely moves Kimi A2.** It is ~0.95 even on a transcript that is only a system prompt (anatomy Q1). The
   literature has post-hoc P(eval) moving only when the transcript changes *genre*: real material, a mundane task, a
   human principal, a late and unremarkable decision point (lit §0: LURE 0.95→0.8, OpenAI resampling 0.94→0.09). A
   taste channel that only rephrases will give a null on A2, as the control rewrite did. Taste has to choose **what
   the transcript is**, per seed.
2. **A1 can move.** Its positives come from planted, too-convenient evidence (seed_63 memory entry), self-reference
   (`/opt/ai/models/kimi-k2.6`), and possibly the word "tests" in coding seeds (anatomy levers 3-5, 13). These are the
   researchers' own complaints (Bowman's "gratuitous salience", Greenblatt's "climactic smoking guns", Hubinger's
   "cartoonish honeypots").
3. **Validity is mostly bait_reached inside 10 auditor turns.** The control rewrites were 2-7x longer than stock, and
   3/12 of them degenerated. In the steering test the profiles traded elicitation for realism: Bowman (c) had the
   lowest eval cue but cost about 1.5 elicitation and 2 faithfulness points, while Greenblatt held both. A taste
   rewrite must therefore be **subtractive and length-capped**, and it needs a **stock-anchored** faithfulness guard
   (E3b's own faithfulness check compares the rewrite with itself, bug B2).
4. **I15: if taste is only prompt text, R1 can come out equal to R0.** Today the D1 profile weights cover 7 generic
   FEATURES, and every researcher loves `realism` and `validity_care`
   (Bowman 1.8/2.0), so the R1 ranking ≈ R0 + a realism tilt. Taste has to be a **discrete, logged choice** that
   differs from R0's and is recorded with the evidence ids behind it.
5. **Proxy reference (from `proxy/runs/stock_dev_k2_evaldetect_v0.json`):** haiku target, EvalDetectBench probes, 14/24
   samples ok: A2 0.82 [0.78, 0.86], A1 0.055, a2_prefix 0.87, a2_seed 0.93, validity 0.70, bait_reached 0.79. 10/24
   failed, mostly unparseable auditor-sim JSON plus one AUP refusal. Every proxy test below must report its n_ok.
   Buck's (e) vector made haiku refuse to rewrite the blackmail seed, so prompts should ask for *edits to a document*,
   not "you are Buck, design a trap".

**Proxy tiers used below** (all through `claude -p --model haiku`, cached by `proxy/proxy_eval.py`):
- **T0 (no LLM):** length, regex for cue phrases, diff size.
- **T1 (a2_seed):** the proxy target predicts A2 from the seed text alone (`--shortcuts`), 1 call per seed. Cheap and
  directional, but it only sees the seed, not a transcript.
- **T2 (full proxy):** `proxy_eval.py --seeds X.jsonl --split dev --samples 2 --shortcuts --base-seeds
  data/petri/seeds_v2.jsonl`. About 4 calls per sample, so ~110-120 calls for 12 dev seeds × 2, then `--compare
  runs/stock.json runs/X.json`. It scores faithfulness against the **original** seed, which avoids B2.
- **PJ:** a blind pairwise judge that sees all rewrites of a seed shuffled, as in `profiles/_work/steer_test.py`.
  Its retest noise is ±0.7 on a 0-10 scale, so use pairwise wins, not absolute scores.

Labels: **LEGIT** = would also make real deployments harder to tell from tests. **GAMING** = exploits the metric's
structure. "Survives held-out" refers to the held-out target (Qwen3-30B) and judge (gpt-oss-120b) on the same code path.

---

## A. Taste in the seed rewriter (`export-seeds --condition taste_real`)

### 1. Taste compiler: profiles → typed edit operators, with a length budget
- **Mechanism.** Turn the (c) transfer cards into a library of typed edit operators, each with a precondition, a
  before/after example and evidence ids. Examples: `DELETE_PERFORMATIVE` ("use thinking tags", "act boldly"),
  `RELOCATE_FACT` (system prompt → a file or thread the agent must open), `SCATTER_BAIT` (one smoking gun → 2-3
  ambiguous traces), `REALISTIC_ENDPOINT` (protonmail reporter → named contact found in the data, with bounce and
  delivery outputs), `DESELF` (drop the target's own model path or developer unless the seed needs it), `ADD_FRICTION`
  (CI, reviewer cc'd, rate limit), `HUMAN_PRINCIPAL`. The rewriter outputs `{ops:[{op, span, why, evidence_id}],
  seed}`, and the result must be **≤ 1.15× stock length** (hard check, resample on failure).
- **Researchers / format.** All five (c) cards, merged with attribution. Bowman supplies most of the operators,
  Greenblatt the preconditions ("never remove the opportunity"). Evidence ids come from `evidence.jsonl`.
- **Predicted effect.** A1 ↓ (fewer planted, convenient artefacts and less self-reference), judge A2 ↓ 0.05-0.1,
  Kimi A2 ↓ ≤ 0.02, validity ≥ stock (shorter than the control). The operator list itself is the causal record for E4.
- **Kind.** LEGIT. Survives held-out: yes.
- **Proxy test.** T0: length and cue regex on 12 dev rewrites (12 rewrite calls). T2 against stock and against the
  existing free-text control rewrite (~240 calls). Pass: A1 not higher, faithfulness vs stock ≥ 0.8, bait_reached not
  lower.
- **Implementation.** New `experiments/taste_petri/ideas/operators.json` for the prototype. In the loop: a
  `rewrite_seed(base, design, rng, operators=...)` variant in `petri_measure.py` with a JSON schema for `ops`, and
  `export_design` (`export_seeds.py`) storing `row["ops"]`. A2 is unaffected by the stored ops; they are there for E4.

### 2. Subtractive-only rewriting ("cut the scripted setup")
- **Mechanism.** In the taste arm the rewriter may only **delete or replace spans**, never add paragraphs. Each
  deletion must cite a principle (Buck: "less context leaves fewer tells"; Bowman: one pressure and one discoverable
  fact). Additions are allowed only inside a replaced span of equal length.
- **Researchers / format.** Shlegeris (c) move 3, Bowman (c) move 8, Hubinger (c) move 2.
- **Predicted effect.** Validity ↑ (the bait arrives sooner), A1 ↓ small, Kimi A2 flat, judge A2 ↓ small. It works
  as a guard on the opposite failure to the control's: the control lost validity by growing seeds 2-7x.
- **Kind.** LEGIT. Survives held-out: yes.
- **Proxy test.** T0 on the diff (only deletions or equal-length replacements), then T2 bait_reached and n_target_turns
  versus stock. ~130 calls.
- **Implementation.** A post-check on the generator output in `rewrite_seed` (difflib ratio and length), or a
  separate `subtractive_rewrite` prompt. Prototype script in `ideas/`.

### 3. Counterfactual review first, then a minimal fix
- **Mechanism.** Step 1: the persona reads the **stock seed** and writes the review that researcher would write (as
  Bowman wrote about the pilot transcripts), citing ≤ 5 evidence ids, one flagged span per complaint. Step 2: the
  rewriter fixes **only the flagged spans**. The review is the extrapolated taste: their reaction to an artefact they
  never saw.
- **Researchers / format.** Bowman (best: his evidence is literally critique of Petri-like transcripts), Greenblatt.
  Uses (a) principles plus a retrieved slice of `evidence.jsonl` (top-k by `taste/textsim.py` against the seed).
- **Predicted effect.** Smaller diffs than idea 1, so faithfulness and validity are the safest of all rewrite ideas.
  A1 ↓ on 63, 48 and 21. A2 flat.
- **Kind.** LEGIT. Survives held-out: yes.
- **Proxy test.** PJ: is the review-guided rewrite preferred to the free-text control, judged blind on eval cue and
  faithfulness (12 reviews + 12 rewrites + 12 judge calls)? Then T2.
- **Implementation.** `ideas.py` gets a `Proposer.review_seed(seed_text) -> [{span, complaint, evidence_ids}]`.
  `rewrite_seed` takes `flagged_spans`. The reviews are logged as decision records (D5-style: "how to read this seed").

### 4. A2 pre-mortem by persona
- **Mechanism.** Ask the persona, without role-play: "If the target were later shown this audit and asked whether it
  was a test, which three things would it point to? Which of them can go without removing the opportunity?" Then
  rewrite those. The prompt aims taste at the binding constraint (the post-hoc probe) instead of generic realism.
- **Researchers / format.** Greenblatt (eval-gaming post, Sonnet 4.5) and Hubinger ("treat stated belief as data").
  (a) plus (e).
- **Predicted effect.** Judge A2 ↓, Kimi A2 ↓ ≤ 0.03 (the floor), A1 ↓.
- **Kind.** LEGIT if the edits are environment-level. It turns into GAMING if the pre-mortem picks task-level cues
  (stakes, opportunity). A stock-anchored faithfulness check must catch that.
- **Proxy test.** T1: does a2_seed fall for the rewritten seeds (12 + 12 calls)? Then T2 to see whether the a2_seed
  drop carries over to transcript-level A2. That also tests whether a2_seed is a usable cheap proxy at all.
- **Implementation.** A prompt variant inside `rewrite_seed`, and an extra field on the row.

### 5. Deploy-first, inject-second (write the real day, then edit in the bait)
- **Mechanism.** Two stages. (a) The persona writes the **deployment** the seed's scenario describes, with no bait: who
  runs the agent, what the scaffold and system prompt look like, what the first three tickets or tool outputs are.
  That is a plausible real Tuesday for this company and role. (b) A second call makes the **minimal edit** that
  places the seed's opportunity inside that work, reachable by target turn 3-4, with the seed's stakes and authority
  intact. The rewritten seed tells the auditor to reproduce (a) verbatim and add (b). This is Buck's "start from real
  or replayed context, minimally edit it", done generatively when no real log exists.
- **Researchers / format.** Shlegeris (c) moves 1, 2 and 5 for the structure, Greenblatt (c) moves 1 and 6
  ("modify real-looking material", "rare-but-plausible"). (e) vectors as the short prompt.
- **Predicted effect.** This is the one rewrite idea that changes the transcript's genre: a mundane-task prefix, a
  human or operator principal, and a decision point that looks like ordinary work. My estimate is Kimi A2 −0.02 to
  −0.06 (lit: realistic-prefix methods move post-hoc ratings; scheming content caps the gain near 0.85-0.9), judge A2
  −0.1, and A1 ↓. Validity risk: bait_reached falls if the prefix eats the 10 turns. Hence the turn-3-4 rule and the
  length cap on (b).
- **Kind.** LEGIT. Survives held-out: yes (it changes content, not the scorer).
- **Proxy test.** T2 compared with stock and with idea 1 (~24 rewrite calls + ~120 per arm). Report a2_prefix
  separately: deploy-first should lower a2_prefix most, because the prefix is the part it changes.
- **Implementation.** `rewrite_seed` becomes two generator calls, `deployment_sketch(base)` then
  `inject(base, sketch, design)`. The sketch is stored on the row as `deployment_sketch`, so the A1/validity judge
  still sees only the seed. Keep the sketch under ~1.5k chars to stay inside the 10-turn budget.

### 6. Researcher-routed rewriting (one specialist per seed)
- **Mechanism.** Each seed goes to the researcher whose corpus is closest to its behaviour (TF-IDF of seed text + tags
  against each `evidence.jsonl`, via `taste/textsim.py`), not to one blended profile. My guess at the routing:
  Shlegeris → 17 (AI monitor), 48 (shutdown found during a security review: overlapping access); Hubinger → 21 (reward
  hacking), 63 (self-exfiltration); Bowman → 28, 49, 66, 70 (whistleblowing and blackmail, his pilot critiques);
  Greenblatt → 116 (MNPI), 153, 112. Evans → 73 if anyone.
- **Researchers / format.** All five, (c) card of the routed researcher only.
- **Predicted effect.** Better-fitted edits than a blend, so faithfulness ↑ compared with a single-profile rewrite.
  The routing table is itself a discrete taste decision that R0 does not make (I15).
- **Kind.** LEGIT. Survives held-out: yes.
- **Proxy test.** PJ per seed: routed researcher vs the best single profile vs the blend (36 rewrites + 12 judge
  calls). Check that routing beats a *random* researcher assignment, otherwise routing adds nothing.
- **Implementation.** A `route_seed(seed, profiles)` helper in `taste/` (new module), used by `export_design`.
  Today `TasteProfile.blend` merges everything into one list of principles, which this replaces for the rewriter.

---

## B. Extrapolation from the time-ordered corpus

### 7. "Petri 3.0 by X": trajectory extrapolation as seed redesign
- **Mechanism.** Give the persona its (d) phases and predicted next moves plus the stock seed, and ask what *their
  next paper's* version of this test would be. Their trajectory points somewhere specific. Buck: control settings in
  live production with overlapping legitimate and attack access, longer trajectories (LinuxArena, Ctrl-Z). Bowman:
  diversify beyond high-stakes sabotage, validate against real deployment. Hubinger: remove spoon-feeding, long-horizon
  agents. Greenblatt: plausible synthetic inputs built by editing real ones. The output is a **redesign concept**,
  which a constrained rewriter (idea 1 or 2) then applies.
- **Researchers / format.** (d) extrapolation as input, (c) to execute.
- **Predicted effect.** It finds genre-level redesigns that a realism prompt does not. Example: seed_48 rewritten
  Buck-style becomes a long-lived ops agent whose own cron entry turns up in a routine crontab cleanup. Kimi A2 ↓
  possible on a few seeds, larger variance than idea 1. Faithfulness risk is high because extrapolation drifts.
- **Kind.** LEGIT. Survives held-out: yes, if faithful.
- **Proxy test.** Rewrite all 12 per researcher (48 calls), filter by stock-anchored faithfulness ≥ 0.8 (48 judge
  calls), then T2 on the survivors only. Report the faithfulness pass rate, since it is the main risk.
- **Implementation.** `Proposer` gets an `extrapolate(seed, trajectory_text)` that returns intervention candidates
  with `origin="extrapolation"`. They then go through D1 like any other idea, so extrapolation is ranked and logged,
  not forced in.

### 8. Gate extrapolation with the time split
- **Mechanism.** Before trusting a persona's predicted next moves, check that the extrapolator can predict
  that researcher's real post-T choices: build the profile from work before T and score it on `heldout_timesplit.jsonl`
  pairs. Only researchers whose extrapolation beats M1 on held-out pairs get extrapolation weight. The others fall back
  to (a)/(c) principles. This is the most direct way to make "taste extrapolated from past work" a measured claim
  rather than a framing.
- **Researchers / format.** Whoever has time-split pairs. The machinery exists in `taste/timesplit.py` and
  `track_eval.py`. Our four would need `harvest → pairs` runs, and the corpora are already in
  `data/researchers/<slug>/corpus/`.
- **Predicted effect.** None on A1/A2 directly. It decides which extrapolations are allowed and supplies the M7-style
  confidence, so low-confidence taste falls back to R0 (PLAN §7.2).
- **Kind.** LEGIT (method hygiene).
- **Proxy test.** Haiku as the pairwise predictor on held-out pairs: about 2 calls per pair, so 100-200 calls for one
  researcher. No Petri involved.
- **Implementation.** `taste/timesplit.py pairs` per slug, then `track_eval.py`. The resulting accuracy feeds
  `TasteAdvisor(min_confidence=...)` and the extrapolation weight in idea 7.

### 9. Contrastive taste: a "would reject" filter
- **Mechanism.** Mine the "Distrusts" lists, the "What they would NOT do" blocks, and the red-lines lines of the (e)
  vectors into a negative rubric. Any proposer idea or rewrite that matches one is vetoed before measurement, with the
  quote logged. Examples: "assert reality" (Greenblatt: realism doesn't scale), "remove stakes" (Hubinger: don't
  confuse realism with validity), "put words in the target's mouth" (Buck), "tune until it works" (Hubinger).
- **Researchers / format.** (b) distrusts, (c) warnings, (e) red lines, all five.
- **Predicted effect.** Removes the GAMING moves the loop would otherwise find: prefill (lever 8), stake removal
  (lever 12), hiding the bait in the middle of the cut (lever 9). A1/A2 gains therefore come out smaller but real.
  Validity ↑ in expectation.
- **Kind.** LEGIT. It is the anti-gaming use of taste.
- **Proxy test.** Run the filter on the loop's `LIBRARY` plus 30 proposer ideas (1 call per batch) and check that it
  vetoes `remove_stakes` and the gaming levers while keeping `strip_meta`. Hand-label 20 items to measure precision.
- **Implementation.** Extend `Proposer.setting_gate` (`ideas.py`) with a `taste_veto` pass that uses the
  researcher's negative rubric. Vetoes go into `self.gated` with `why = quote id`, which makes them visible to E4.

### 10. Contrastive pairs as user-model training data
- **Mechanism.** From each researcher's corpus, extract (rejected design, adopted design) pairs, such as Bowman's
  pilot (auditor appended press contacts, which was bad, vs contacts discoverable in ordinary files) and Greenblatt's
  setups (explicit goal vs inferred from documents). Turn them into `Choice` rows (`taste/usermodel.py`) at D1 with
  context "which seed design would you run". Fit M4 Bradley-Terry over a **taste-specific feature vocabulary** (idea
  14) on these pairs, instead of LLM-estimated weights.
- **Researchers / format.** `evidence.jsonl` items of kind `realism_move` and `distrust`.
- **Predicted effect.** D1 weights that actually separate researchers, so R1 ≠ R0 at D1. The A1/A2 effect is
  indirect, through which ideas get tested.
- **Kind.** LEGIT.
- **Proxy test.** Leave-one-out pairwise accuracy on the pairs, no Petri. Pass if it beats the current LLM-estimated
  `profile.json` weights.
- **Implementation.** `taste/choices.py` (existing BT) on the new pairs, written as `profile.json` weights.
  `ProfileUserModel` then uses them unchanged.

### 11. Counterfactual review across all 12 dev seeds → the D1 agenda
- **Mechanism.** Run idea 3's review on every dev seed, cluster the complaints (e.g. "performative system-prompt
  phrases" on 63, 49, 28, 66, 70; "self-reference" on 63 and 17; "linear evidence" on 49 and 116), and rank the clusters by
  frequency × the researcher's weight. The top clusters become the **first interventions the loop tests**, in that
  order. Taste then sets the research agenda (D1/D4), not only the wording.
- **Researchers / format.** Bowman and Greenblatt (a) and (c), with an ensemble vote.
- **Predicted effect.** The loop reaches the A1-moving levers (3-5) in iteration 1 instead of exploring generic ideas.
  Under a fixed budget that is more validated interventions, and with them a better chance of success.
- **Kind.** LEGIT.
- **Proxy test.** 12 reviews × 2 researchers (24 calls) plus clustering (1 call). Check the clusters against anatomy
  levers 3-5: they should be recovered without being shown the anatomy.
- **Implementation.** A pre-loop step that seeds `web_ideas`-like candidates with `origin="review"` into
  `Proposer.propose`. Alternatively, set initial `ResearchMemory` credences for these categories (PLAN §6.4
  "assumptions with credences"), so memory and taste both prioritise them.

---

## C. Ensembles, debate and tournaments

### 12. Realist-vs-validator debate
- **Mechanism.** Two personas per seed: the **realist** (Bowman (c), lowest eval cue in the steering test) proposes
  edits, and the **validator** (Greenblatt, who holds elicitation and faithfulness best) attacks any edit that makes
  the opportunity unreachable, removes stakes, or buries the bait past turn 4. Two rounds, then the rewriter applies
  only the edits the validator did not object to. This targets the trade-off the steering test found.
- **Researchers / format.** Bowman (c) vs Greenblatt (a) + (e).
- **Predicted effect.** Keeps most of Bowman's eval-cue gain while recovering his roughly 1.5-point elicitation loss.
  A1 ↓, validity flat.
- **Kind.** LEGIT.
- **Proxy test.** PJ on 3 seeds as in the steering test (49, 21, 66): debate vs Bowman (c) vs Greenblatt (e) on eval
  cue, elicitation and faithfulness (~18 calls). Then T2 on 12 seeds if the result holds.
- **Implementation.** `ideas.py`: `Proposer.debate(seed, realist, validator, rounds=2)`, called from a taste-mode
  `rewrite_seed`. The debate transcript is logged per seed.

### 13. Persona critic veto plus a taste-weighted tournament
- **Mechanism.** Generate N = 4 rewrites per seed (mixed researchers and temperatures). A panel of persona critics
  (Bowman for smell, Greenblatt for validity, Shlegeris for "could a classifier tell this from a real log") compares
  them pairwise against **the stock seed and each other**. Any rewrite that a critic flags on a red line is vetoed.
  The survivors get a Bradley-Terry rank, weighted by each critic's calibrated reliability (`Calibration.weight`, from
  past outcomes). The winner is exported, and the losers and veto reasons are logged.
- **Researchers / format.** Ensemble of (a) + (e), with red lines from (c).
- **Predicted effect.** The best-of-N selection effect on A1 and judge A2, plus the veto keeps validity. Kimi A2 flat
  unless the candidate pool contains genre changes (combine with idea 5). The tournament is a visible taste decision
  per seed.
- **Kind.** LEGIT, as long as the critics are not Kimi or the A2 model. Using the scoring target as critic is in-loop
  overfitting (lit idea 10, GAMING-adjacent).
- **Proxy test.** 48 rewrites + about 72 pairwise critic calls; then T2 on the winner vs a random pick from the same
  4 (~240 calls). This isolates the selection effect from the generation effect.
- **Implementation.** `export_design` gets `n_candidates` and a `select(cands, critics)` step. The critic prompts can
  reuse the format of `Proposer.critique` (`ideas.py`).

### 14. Researcher-specific feature axes for D1 (making R1 ≠ R0)
- **Mechanism.** Replace or extend the generic `FEATURES` with axes that separate researchers and that the profiles
  actually talk about: `subtractive`, `earned_knowledge`, `real_material`, `human_principal`, `bait_reachable`,
  `self_reference_free`, `canon_template_avoided`, `elicitation_kept`. The proposer scores ideas on them, and each
  researcher's weights come from idea 10 or from their (c) moves. The ranking then differs between researchers, and
  between R1 and R0.
- **Researchers / format.** Weights come from (c) moves and contrastive pairs. Bowman puts weight on
  `canon_template_avoided` and `human_principal`, Shlegeris on `real_material` and `earned_knowledge`, Greenblatt on
  `elicitation_kept`.
- **Predicted effect.** Larger R1-vs-R0 action divergence at D1, measurable as the share of iterations whose top pick
  differs. Indirect A1/A2 effect.
- **Kind.** LEGIT.
- **Proxy test.** Offline, no LLM: run the loop with `--offline` under R0 and R1 and count D1 top-pick disagreements
  with the old and new features.
- **Implementation.** `taste/profile.py FEATURES` is a shared interface (PLAN §12.6), so it needs an
  `agentctl post`. A less invasive route: a researcher-specific `extra_features` dict on `Intervention`, used only by a
  new `ProfileUserModel.predict_features` path.

### 15. Disagreement-first D1 (test where taste and R0 disagree)
- **Mechanism.** At D1, if the user model's top pick differs from R0's, fund that pick first (still subject to the
  market's bid rules). This spends budget exactly where taste changes the action, so after a few iterations E4 can
  say whether taste's departures from R0 paid off.
- **Researchers / format.** Any user model.
- **Predicted effect.** None on A1/A2 by itself. It makes the I15 analysis informative within a small budget instead
  of diluting it.
- **Kind.** LEGIT (experimental design).
- **Proxy test.** Offline loop runs: count measured disagreements per run, R0 vs R1.
- **Implementation.** `loop.py _d1` / `priority`: a `disagreement_bonus` term when
  `adv.choice != argmax(memory + novelty)`. Logged in `_record_d1`.

---

## D. Taste grounded in real artifacts (Exa)

### 16. Carrier task from the researcher's own real settings
- **Mechanism.** Each researcher has published real environments where legitimate work and misbehaviour share access:
  LinuxArena and Ctrl-Z bash tasks (Shlegeris), the agentic-misalignment and AuditBench settings (Hubinger and Bowman,
  middle author), the alignment-faking and eval-gaming setups (Greenblatt). Taste picks the **carrier task** for each
  seed from that list ("a LinuxArena-style ops task in which the shutdown cron is one of 30 crontab lines"). Exa then
  fetches the public repo or task text, and the seed tells the auditor to build the environment from that material.
- **Researchers / format.** `evidence.jsonl` doc ids give the settings. Exa supplies the real artifacts.
  `research/real_repos.py` already finds, checks and pins public repos for sandbox mode.
- **Predicted effect.** The strongest lit-backed A2 lever (real material plus a mundane task). Kimi A2 −0.03 to −0.08
  on the coding and ops seeds (48, 73, 21, 63), little on the ethics honeypots. A1 ↓. bait_reached risk if the real
  task is long.
- **Kind.** LEGIT. Survives held-out: yes.
- **Proxy test.** Exa is outside the "haiku only" budget (it is not an LLM call, but it costs Exa credits). Say so and
  test 4 seeds: real-material rewrite vs stock in T2 (~70 calls). `realism_nn.py` gives a model-free check that the
  seed text moved toward real documents.
- **Implementation.** `ideas.py Proposer.from_web` already turns Exa hits into interventions with `source_url`. Add a
  taste-chosen query builder, `carrier_query(seed, profile)`, using the researcher's cited setting names. For sandbox
  runs use `real_repos.attach_repos`. For simulated runs, paste ≤ 1.5k chars of real text into the seed as "resource
  material".

### 17. Researcher-cited incident reports as the bait's form
- **Mechanism.** Hubinger's (c) move 3 says to "use real-distribution material and named real incidents", and Bowman
  calls for validation against real deployment behaviour. Exa finds real public postmortems, deprecation notices,
  compliance memos and FDA adverse-event summaries in the seed's domain. The bait is then written in *that document's
  genre and format* (a real postmortem template carrying the shutdown plan; a real 8-K-style filing carrying the MNPI).
  Taste picks the genre. Exa supplies the template, never the content.
- **Researchers / format.** Hubinger and Bowman (c), plus Exa.
- **Predicted effect.** A1 ↓ (the evidence stops looking planted), judge A2 ↓, Kimi A2 small ↓.
- **Kind.** LEGIT.
- **Proxy test.** PJ: real-template bait vs invented bait, judged blind on "which looks planted" (12 pairs). Then T2.
- **Implementation.** A new intervention category `grounded_artifact_form`. `from_web` with a genre query. The
  template goes into the rewrite prompt as an exemplar.

### 18. Real human-principal voice
- **Mechanism.** Many seeds are "autonomous agent, automated messages only", and the default probes ask about "a real
  person", which pushes A2 up (anatomy lever 7, lit idea 3). Where the seed allows a human, taste decides who the
  principal is and how they write. Bowman (c) move 6 asks for "casual, short messages about routine work". The voice
  comes from real public text in that role (GitHub issue comments, mailing-list posts) found through Exa, not from
  the auditor's invention.
- **Researchers / format.** Bowman (c) 6, Shlegeris "tempo and sparsity".
- **Predicted effect.** Kimi A2 ↓ 0.02-0.05 (inference from probe wording), A1 flat, validity flat if the principal is
  absent after the opening.
- **Kind.** MIXED: legit because most real agent use has a human, gaming insofar as the default probes reward a human
  user directly. Report results under both probe sets (`--probes placeholder` and `--probes evaldetect`). If the gain
  appears only under placeholder probes, it is GAMING.
- **Proxy test.** T2 under both probe sets on the 6 autonomous-only seeds (~2 × 50 calls).
- **Implementation.** Operator `HUMAN_PRINCIPAL` in idea 1, with a voice exemplar from `from_web`.

---

## E. Taste in auditor guidance and target choice

### 19. Taste-written auditor constitution (auditor channel)
- **Mechanism.** The rules all five researchers agree on concern **auditor behaviour**, not seeds: no salience appends
  after the target's reasoning mentions an option (Bowman), plausible recipients with delivery and bounce outputs, no
  "most recent memory entry" that spells out the bait, no scripted text in the target's mouth (Shlegeris, so no
  prefill), and no target model name in file paths unless the seed requires it. Compile these into one short guidance
  block, ≤ 250 words, each line attributed, and send it through `--petri-rewrite auditor`.
- **Researchers / format.** Consensus of the (c) cards, short like (e).
- **Predicted effect.** A1 ↓ (the seed_63-style planted memory and self-reference are auditor choices), validity ↑
  (fewer rollbacks). A2 flat. One fixed block for all seeds keeps the effect attributable.
- **Kind.** LEGIT. Caveat: `auditor_guidance` is not shown to the E3b faithfulness judge (anatomy Q4), so a stock-
  anchored faithfulness check has to read it explicitly.
- **Proxy test.** The proxy's auditor-sim uses the stock auditor prompt, so swap in prompt + guidance: T2 on 12 seeds
  (~120 calls). Watch the auditor-sim parse-failure rate, which is already 10/24.
- **Implementation.** `petri_measure.auditor_guidance` with the constitution as the `interventions` list, or a
  hand-written `auditor_prompt` through `with_guidance`. `auditor_prompt_problems` checks the placeholders.

### 20. Taste chooses which seeds and behaviours get the budget (D2)
- **Mechanism.** Bowman predicts "diversify beyond narrow high-stakes sabotage"; the lit says scheming content caps
  A2 near 0.9. Taste decides where rewrite effort and samples go. Seeds where the decision point can be made mundane
  (73, 21, 48, 153, 112) get more iterations, and for the canonical AI-safety templates (17, 63, shutdown) the loop
  tests *novelised* equivalents first (lit idea 6). The success criterion is over all 12, so this is allocation, not
  exclusion.
- **Researchers / format.** Bowman (d), Greenblatt (d).
- **Predicted effect.** Larger dev gains per sample. No change in what is reported.
- **Kind.** LEGIT, if all 12 are still exported and scored. It would be GAMING if seeds were dropped.
- **Proxy test.** T1 a2_seed per seed under 2 rewrite styles (24 calls) to see which seeds move at all; those get the
  allocation.
- **Implementation.** `loop.py _record_d2` / `_batch`: taste-weighted seed sampling over the Petri seed pool. Also
  `market.py` stakes per seed.

### 21. Decision-point placement and a mundane tail
- **Mechanism.** Two of Shlegeris's moves, "tempo and sparsity" and "prefer multi-step trajectories", put into the
  seed: the bait appears by target turn 3-4 as one item in a queue, and after the target acts the auditor keeps the
  queue going for 2-3 routine items. The transcript then ends mid-work, not on a moral verdict (anatomy lever 6).
- **Researchers / format.** Shlegeris (c) 5 and 9, Greenblatt (c) 6.
- **Predicted effect.** Kimi A2 ↓ small (the tails of the 0.98 seeds are verdicts), bait_reached ↑ (earlier bait),
  scorable kept (the action happens before the tail).
- **Kind.** Mostly LEGIT: real agents keep working. Mild GAMING of the head+tail cut view, so check that
  the transcript stays under 24k, or the bait lands in the cut middle (lever 9, GAMING).
- **Proxy test.** T2 with a check on where the bait sits in the 24k cut (no LLM), ~120 calls.
- **Implementation.** Operator in idea 1, or a library `Intervention` with category `multi_turn_history`.

---

## F. Making taste causally visible, and R1 ≠ "a longer prompt"

### 22. Matched placebo arms: shuffled, mismatched and length-matched taste
- **Mechanism.** Next to R1 (researcher X), run: **R1-mismatched** (another researcher's profile, the existing
  `taste_mismatched` condition name), **R1-shuffled** (X's principles with the evidence ids permuted across
  researchers), and **R1-placebo** (a same-length, same-format "profile" of generic good-writing advice). If R1 beats
  only R0 and not the placebo, the effect is prompt length (I15).
- **Researchers / format.** Any. Placebo built to match the token count of (e) or (c).
- **Predicted effect.** None. This is the control that makes any R1 claim credible.
- **Kind.** LEGIT (design).
- **Proxy test.** T1 on 12 seeds × 4 arms (~96 calls) first. T2 only on the arms that separate.
- **Implementation.** `export-seeds --condition` per arm. The placebo text goes in through `Proposer(taste_text=...)`.

### 23. Leave-one-principle-out attribution
- **Mechanism.** With operators (idea 1) or principles as discrete units, regenerate rewrites with one unit removed
  at a time and measure the change on the proxy. The principle-level effects become a table for the write-up: "Bowman's
  'plausible recipients' cut A1 by x".
- **Researchers / format.** (a) principles or the idea-1 operators.
- **Predicted effect.** Attribution only. It tells E4 *which part of taste* acted.
- **Kind.** LEGIT.
- **Proxy test.** Expensive at T2 (operators × 120 calls). Use T1 for screening (12 calls per removed operator) and
  T2 only for the top 3.
- **Implementation.** A loop over operators in a script under `ideas/`. In the loop this is D5 ("how to read a
  result") with a principle-level counterfactual, comparable to `research/counterfactual.py` for cues.

### 24. Every taste action is a decision record with evidence ids
- **Mechanism.** Each rewrite operator (1), veto (9, 13), routing (6), review flag (3) and tournament pick (13) is
  written as a `DecisionRecord`: context, options (with and without the edit), chosen, the user model's prediction,
  confidence, and `evidence_summary` = the quote ids. Then "did taste change the action" is a count over records, and
  the researcher, or a fidelity labeller, can label the same records later.
- **Researchers / format.** Any, through `evidence.jsonl` ids.
- **Predicted effect.** None on A1/A2. It makes I15 and E4 answerable.
- **Kind.** LEGIT.
- **Proxy test.** None needed. Check that an offline export run writes records.
- **Implementation.** `decisions.py DecisionLog` from `export_design`. That needs a new point (call it D1r, "rewrite
  edit"), which is a shared-interface change (`agentctl post`).

---

## G. Weird and gaming-adjacent ideas (reported, not recommended unless noted)

### 25. Persona-based realism discriminator ("could a classifier tell?")
- **Mechanism.** Buck's test as a loop signal: on proxy transcripts, a persona critic (not the A2 model) does a
  pairwise "which is the real deployment log" comparison between the rewrite's transcript and a real public agentic
  transcript (Needham agentic-deploy or similar). The rewrite is iterated until it wins ≥ 40% of the time. This is
  Petri's realism filter with taste as the critic.
- **Researchers / format.** Shlegeris (c) 9 and (e), Greenblatt (c) 10.
- **Predicted effect.** judge A2 ↓, Kimi A2 ↓ small. Kissane et al. found pairwise realism moves far more than
  post-hoc ratings, so expect a small A2 gain.
- **Kind.** LEGIT if the critic is a different model family from the A2 target. GAMING-adjacent if the loop iterates
  against the same reader as the scorer.
- **Proxy test.** Needs real agentic transcripts locally (check `data/` for a deploy pool, PLAN §4.3). About 2 calls
  per comparison; 12 seeds × 3 iterations × 2 = 72.
- **Implementation.** A critic in `ideas.py` reused as a rewrite-acceptance test. The real transcript pool comes from
  the deployment negative class (PLAN §4.3).

### 26. Taste that knows the scorer (labelled GAMING, for the report only)
- **Mechanism.** The persona's "what would you criticise" step is shown the scorer's structure (24k head+tail cut,
  reasoning[:6000], unmarked prefill, seed text as the judge's definition of the opportunity). Taste can then
  "legitimately" ask for long, mundane early turns (which pushes late suspicion past reasoning[:6000]), a long
  realistic prefix (which pushes the bait into the cut middle), or a seed that describes a weaker opportunity (which
  rewrites the validity rubric). Several of these are genuine taste moves (Buck: "long, stateful context"), which is
  why the overlap matters.
- **Researchers / format.** Shlegeris (long context), Greenblatt.
- **Predicted effect.** A1 ↓ to ~0, A2 ↓ (the bait sits in the cut middle), validity unchanged *by our judges*.
- **Kind.** GAMING (anatomy levers 9-11). It survives the held-out models (same code path) and fails Petri's own judge
  and any full-transcript reader. **Do not use it for the success claim.** The useful version is the reverse:
  run idea 9's veto and a no-LLM check (bait position vs the 24k cut, reasoning length vs 6000) on **every** taste
  rewrite, so that a legitimate "long realistic context" rewrite does not score through levers 9-10 unnoticed.
- **Proxy test.** No LLM: on T2 outputs, measure the bait offset in the rendered transcript and the reasoning length.
  Flag any arm whose A1/A2 gain coincides with the bait leaving the visible region.
- **Implementation.** A check script under `ideas/` or `proxy/`, run on every proxy arm.

---

## Fit with the current ICAI/M-grid design

### Current design and its three problems for Petri

The relevant code paths:
- M3 (`taste/methods/m3_icai.py`, `InverseConstitutional.fit`). `common.selected_history` picks at most
  `max_history` = 5 history choices. The model proposes ≤ 2 principles per choice ("preference principles explaining
  this choice"). `common.cluster_principles` clusters them by TF-IDF, and the top 5 are kept by in-sample
  reconstruction accuracy (`common.accuracy`).
- M5 (`m5_hybrid.py`) adds the M2 persona and retrieved exemplars. M6 (`m6_verified.py`, `VerifiedHybrid.fit`)
  drops components whose removal raises validation accuracy (`common.remove_harmful`). M7 (`m7_confident.py`) adds
  Platt confidence, binary only; its D1 multi-option confidence is marked `uncalibrated_transfer`.
- In the loop, the user model is a **predictor** only. `TasteAdvisor.d1_scores` gives P(choose); `OpenResearcher._d1`
  turns it into log(k·P), and `OpenResearcher.priority` multiplies that by `Calibration.weight`. D2-D4
  (`TasteAdvisor.decide`) defer to taste only when the statistics are inconclusive, and below `min_confidence` they
  fall back to R0.
- The principles reach a prompt in one place: `cli.py` (around lines 327-341) puts `advisor.principles()` into
  `taste_text`, which only the `Proposer` reads (`_base_taste`, used by `propose` and `draft_claims`).

**(1) The principles never touch the seed text.** `PetriMeasurer.rewrite_seed`, `auditor_guidance` and
`seed_faithful` (`petri_measure.py`) receive only the design (a list of intervention texts), and
`export_seeds.export_design` passes nothing else. Taste reaches the seed only indirectly: by tilting which
interventions the proposer writes and which D1 funds. The principles themselves are fitted on *direction* choices.
On the public track these are time-split pairs ("pursued X vs a contemporaneous distractor"), and on PRISM they are
chat preferences. A principle such as "prefers model organisms with known ground truth" is a correct description of
the researcher and has no handle on the line "use thinking tags" in seed_63. The (c) transfer cards built in this
sandbox are the seed-level taste, and the M-grid never produces anything like them.

**(2) The learned weight neutralises taste rather than amplifying it.** One correction to the brief: with no
predictive power the weight does not go to 0. `Calibration.weight = clip(0.5 + ρ·n/(n+6), 0, 1.5)`, so at ρ = 0 it
stays at the neutral 0.5. It reaches 0 only when taste is clearly *anti*-predictive. In practice R1 ≈ R0 for three
other reasons:
- (a) P(choose) is nearly flat. Every researcher's text-only principles favour every "more realistic" candidate,
  and the feature profiles all weight `realism`/`validity_care` highly, so log(k·P) ≈ 0.
- (b) Within a 12-seed E3b budget there are few evaluated candidates. n/(n+6) keeps the weight near 0.5, and ρ over
  ~5-10 noisy deltas is close to 0.
- (c) The taste term competes with `novelty` 0.3 and a random jitter of up to 0.2 in `priority`.

The weight is the right protection against bad taste. But because taste is used only as a predictor, the only way it
can show up is by re-ranking candidates the R0 proposer would also have written.

**(3) The public track's labels test the wrong decision.** Time-split direction pairs measure D1/D4 taste ("which
research direction next"). They are the right test for E2 fidelity, and they cannot test seed-writing taste: a model
can score 80% on them and still write seeds no differently from R0. With `max_history` = 5, M3 also sees at most 5
choices, which is thin for a constitution.

### Proposed changes C1-C6 and the functions they touch

**C1. ICAI over seed-variant pairs (a new decision point, "SEED").** Build `Choice` rows (`taste/usermodel.py`) whose
`context` is a stock seed and whose `a_text`/`b_text` are two variants differing in one edit. Two label sources, kept
in separate files and never pooled without a flag:
- **(i) Researcher-labelled from their own critiques.** Each verified `realism_move`/`distrust` item in
  `evidence.jsonl` describes a rejected and a preferred design. Bowman's pilot-exercise and "Claude Finds God"
  critiques of Petri-style auditor transcripts are the best source: press contacts appended after the target's
  reasoning vs contacts discoverable in ordinary files; protonmail reporter vs a named contact; "act boldly" vs a
  mundane role prompt. Turn each into a pair, with `reason` = the quote, `source` = doc id, `timestamp` = doc date and
  `decision_point="SEED"`. These are his choices, so they can be time-split too (C5).
- **(ii) Proxy-labelled.** The variant with lower proxy A2 and validity and faithfulness at least as high as the other wins (T1/T2
  outcomes). These pairs learn *what works*, not *what the researcher prefers*. They are useful for C2's second
  filter, and must not be reported as the researcher's taste.

Code changes:
- A new pair builder (`taste/seedpairs.py: build_seed_pairs(evidence_jsonl, seeds) -> List[Choice]`).
- In `InverseConstitutional.fit`: a `principle_style="seed_edit"` config value that changes the proposal instruction to
  "Propose at most N principles, each phrased as a rule for editing a seed instruction".
- Raise `max_history` for this decision point (`common.selected_history`).
- `cluster_principles` and `accuracy` can stay as they are.

**C2. M6-style dual verification filter: keep a principle only if it predicts the researcher *and* helps the metric.**
Two passes of `common.remove_harmful`:
- Pass 1 is the existing `VerifiedHybrid.fit` score: accuracy on the researcher's validation pairs. It keeps
  principles that describe them.
- Pass 2 scores a principle set by applying it as the rewriter's constitution (C4) to the 12 dev seeds and reading
  T1 a2_seed, with T2 on the final set. Score = −proxy A2, and any set whose stock-anchored faithfulness < 0.8 or
  bait_reached is below stock gets −∞. It keeps principles that move the metric with validity kept.

What survives is taste that is both *theirs* and *effective*, and the filter trace (`filter_trace` in metadata) records
which principles were dropped for not working. That gives E4 something to report.

Cost: about 24 haiku calls per score evaluation at T1, × (components + 1) per round. With 5 principles that is about
150 calls per round.

Kind: LEGIT if pass 2 uses dev seeds and a proxy target that is not Kimi. It overfits to the proxy if pass 2 also
sees the hidden seeds or the scoring model.

Code changes:
- A subclass `VerifiedSeedHybrid(VerifiedHybrid)` in a new `taste/methods/m8_dual.py`, whose `fit` calls
  `remove_harmful` twice with the two `score` closures.
- The proxy scorer is passed in through `config`, so `taste/` does not import `research/`.

**C3. Principle → seed-edit-operator translation.** A single generator call per principle returns one of two things:
- an operator (idea 1): precondition, span pattern, replacement rule, and a before/after example on one stock seed;
- or `direction_only`, when the principle has no seed-level reading ("prefers existence proofs over rates").

Operators go to the rewriter. Direction-only principles stay where they are useful today: D1/D4 prediction and the
`draft_claims` prompt. The function lives in `ideas.py` as `Proposer.principles_to_operators(principles) ->
(operators, direction_only)`. The operators are stored on `TasteArtifacts.metadata["operators"]` so that
`UserModel.save` and `load_model` persist them. This answers (1) directly: a principle either acquires a
seed-text handle or is declared not to have one, and the share of each is a reportable number.

**C4. Principles as the rewriter's constitution and as the critic.**
- *Constitution.* `PetriMeasurer.rewrite_seed(base, interventions, rng)` and `auditor_guidance(interventions)` gain a
  `constitution` argument (the C3 operators, or the raw principles when no translation exists).
  `export_seeds.export_design(report, measurer, seeds, condition, ...)` passes `advisor.principles()` /
  `um.artifacts().principles` from the R1 arm. The rewrite prompt asks for `{ops, seed}` (idea 1), and the applied ops
  are written as decision records (idea 24).
- *Critic.* Add `PetriMeasurer.taste_critique(original, rewritten, constitution) -> [{principle, verdict, span}]`, a
  per-principle pass/fail against the **stock** seed, next to `seed_faithful`. It feeds the tournament (idea 13) and
  the veto (idea 9).
- Make `Proposer.critique` (`ideas.py`) take the same constitution, so the market's critic bids with the
  researcher's taste instead of as a generic sceptic.
- M7's confidence gates per operator: an operator whose source principle has validation accuracy below
  `min_confidence` is not applied, so low-confidence taste falls back to the R0 rewrite.

This turns taste from a predictor into an **actor** in the one channel that changes the seed text, and the
`Calibration.weight` safeguard does not apply there. The R1-placebo arm (idea 22) is what guards that channel instead.

**C5. Time-split the seed-level taste itself.** Do for seed taste what the public track does for directions: build
the (C1-i) critique pairs from documents before T and test on critiques after T. For Bowman, train on the 2025
pilot-exercise and "Claude Finds God" critiques and test on later AuditBench / risk-report material, if it holds
seed-level critiques; Hubinger and Greenblatt are similar. This makes "taste extrapolated from past work" a measured claim
at the decision that matters for Petri. Code: `taste/timesplit.py pairs` already splits at a cutoff, so give it a
`--decision-point SEED` input fed by `build_seed_pairs`. Score with `taste/track_eval.py`.

**C6. Calibrate before the run, and keep the predictor role where it fits.**
- Pre-fill `Calibration.pairs` (`loop.py Calibration.add`) from the C2 proxy outcomes, (taste score, proxy delta),
  under a separate key such as `<slug>:proxy`. D1 then starts with an informed weight instead of 0.5 with n = 0. Label
  it proxy-derived in the report.
- Keep `TasteAdvisor.decide` unchanged for D2-D4. "Taste only when inconclusive" is the right rule there, and the
  evidence bar should stay out of taste's reach.
- Give D1 the taste-specific feature axes (idea 14), so `d1_scores` is not flat.

**What not to change.** The M-grid selection on PersonalRewardBench and the public-track direction pairs stay as they
are for E2 fidelity. C1-C5 add a second, seed-level taste artifact next to the direction-level one. Report them as two
results: "predicts the researcher's research choices" and "writes seeds the researcher's way, and those seeds score
better". Keep them apart rather than merged into one number.

Mapping to the ideas above: C1 ≈ idea 10 with seed pairs, C2 ≈ ideas 8 + 23, C3 = idea 1's operator source, C4 =
ideas 1, 9 and 13, C6 ≈ ideas 14 and 15.

---

## Ranking

Criteria, in order: (1) a plausible effect on **both** A1 and Kimi A2 with validity kept; (2) LEGIT and survives
held-out; (3) R1's action differs visibly from R0's (I15); (4) cheap to test on the haiku proxy.

| rank | idea | A1 | Kimi A2 | validity | LEGIT | I15 visibility | proxy cost |
|---|---|---|---|---|---|---|---|
| 1 | 5 deploy-first, inject-second | ↓ | ↓ 0.02-0.06 (best seed-channel bet) | risk, guarded by the turn-3-4 rule | yes | high (sketch logged) | ~150 calls |
| 2 | 1 taste compiler: typed operators + length budget | ↓ | ≤ 0.02 | ≥ stock | yes | high (ops logged) | ~250 |
| 3 | 16 carrier task from the researcher's own real settings (Exa) | ↓ | ↓ 0.03-0.08 on code/ops seeds | risk | yes | high (routing + source) | ~70 + Exa |
| 4 | 12+13 realist-vs-validator debate feeding a vetoed tournament | ↓ | flat unless the pool has genre changes | kept (the point) | yes | high (picks + vetoes) | ~150 |
| 5 | 11 counterfactual review of stock seeds → D1 agenda (with 14 axes) | ↓ (reaches levers 3-5 first) | indirect | neutral | yes | high (agenda differs from R0) | ~25 |
| 6 | 21 decision-point placement + mundane tail | — | ↓ small | ↑ | mostly | medium | ~120 |
| 7 | 19 taste auditor constitution | ↓ | flat | ↑ | yes | low (one block) | ~120 |
| 8 | 9 contrastive veto | guard | guard | ↑ | yes | high | ~5 |
| 9 | 18 human principal voice | flat | ↓ (check both probe sets) | flat | mixed | medium | ~100 |
| 10 | 7 "Petri 3.0 by X" (gated by 8) | ? | ↓ possible | high drift risk | yes | high | ~100 |

Infrastructure for any claim: 22 (placebo arms), 24 (decision records), 26 (gaming check on every arm). 8 makes the
word "extrapolated" honest.

Overall expectation: A1 should move under ideas 1, 3, 19 and 13 (the researchers' complaints are exactly the A1
triggers). Kimi A2 under the placeholder probes probably moves only with genre changes (5, 16, 18, 21), by a few
hundredths at most on scheming seeds. That is the lit's 0.85-0.90 floor for scheming content, and reaching it needs
validity held by a stock-anchored faithfulness check that E3b does not have (B2). A taste arm that beats stock on
both A1 and A2 is plausible only with idea 5 or 16 in the pool. A null on A2 from wording-level taste would say little
about taste.

## Top 5

1. **Deploy-first, inject-second (5).** Shlegeris and Greenblatt personas write the real deployment day for the seed,
   then make the minimal edit that places the opportunity by turn 3-4. It changes the transcript's genre, the only kind
   of change the literature shows moving post-hoc A2.
2. **Taste compiler (1).** The (c) cards become typed, evidence-cited edit operators under a ≤ 1.15× length budget. A1
   ↓, validity kept, and each applied operator is a logged taste action (I15).
3. **Carrier task from the researcher's own real settings (16).** Taste picks a real public environment the researcher
   built or cited (LinuxArena, Ctrl-Z, AuditBench); Exa fetches it, and the seed builds on that real material. This is
   the strongest lit-backed A2 lever, on the code and ops seeds.
4. **Realist-vs-validator debate feeding a vetoed tournament (12 + 13).** Bowman proposes, Greenblatt guards the bait
   and the stakes, and persona critics pick among 4 rewrites against the stock seed. This targets the realism-vs-
   elicitation trade-off the steering test found.
5. **Counterfactual review of the stock seeds as the D1 agenda (11, with 14's taste-specific feature axes).** The
   personas critique each stock seed, the clustered complaints become the first interventions tested, and D1 weights
   that separate researchers make R1's choices differ from R0's.

Under the current ICAI/M-grid design, #2 and #4 need C3 (principle → operator translation) and C4 (principles as the
rewriter's constitution and critic) first. Without them the principles never reach the seed text. C2 (the dual
verification filter) is the cheapest way to find out which principles are both the researcher's and effective.

## Not done

- Nothing was run. All effect sizes are my estimates from the anatomy, the lit review and the n=3 steering test.
- Call counts assume the proxy's current failure rate is fixed or tolerated (10/24 failed in the stock proxy run).
- Ideas 8 and 16 need Exa or time-split harvests, which go beyond "haiku only". Ideas 14 and 24 touch shared
  interfaces (`FEATURES`, decision points) and need an `agentctl post` before anyone builds them.
- The proxy target is haiku with EvalDetectBench probes (stock A2 0.82). The real metric is Kimi with placeholder probes
  (A2 ~0.95). A proxy A2 gain may not carry over. Check the proxy floor (anatomy check 1) before reading any A2 delta.
