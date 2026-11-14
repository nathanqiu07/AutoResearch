# AutoResearch: final project plan

*Merged from five team specs (2026-11-14). It builds on the code already in this repo
(`README.md`, `AGENTS.md`). Anything marked **[decide]** needs a team decision before the
work that depends on it starts.*

---

## 0. The project in one paragraph

We build a multi-agent research system whose decisions are steered by a **model of a
specific researcher's taste**, learned from that person's data. We test it on one
open-ended research task: **design synthetic evaluation environments that a target model
does not recognise as evaluations, while they still validly test the behaviour they are
meant to test.** We report four separate results and do not merge them into one:

1. **Preference fidelity.** Does our user-model method predict a person's unseen choices?
2. **Research judgment.** Are the loop's decisions justified by the evidence, including when that means going against the user model?
3. **Downstream outcome.** Do the environments it produces lower measured eval awareness against strong existing controls, with validity kept?
4. **Efficiency.** What does it cost in dollars, calls and wall time, against baselines and with our resource market against uniform allocation?

Each link in the chain (better user model → better decisions → better environments) can
fail on its own. Finding out *which* links hold is part of the result.

---

## 1. What each spec contributes

| Spec | Main contribution | Kept as |
|---|---|---|
| 1 | R0 (base loop) vs R1 (taste loop). Methods: SynthesizeMe, "reverse" (Inverse) Constitutional AI. Data: PersonalRewardBench, personal labels, Exa-scraped researcher data. Two evaluation fronts: taste and eval creation | System naming (§5), method grid (§6), evaluation fronts (§9) |
| 2 | Goal framing (same usefulness, less awareness). A pipeline that turns raw documents into insights and assumptions. Three comparisons: new eval vs old bench, our method vs baseline agent, efficiency. A **resource bidding** market. Make sponsor use stand out | Taste pipeline (§6.4), experiments E3–E5, resource market (§8), sponsors (§10) |
| 3 (Gio + Codex revision) | Fidelity is not the same as good judgment. User-stratified held-out splits. Baselines: no history, and history pasted into the prompt. Learn a *method*, not one model. Taste should guide the whole loop, not one generation step. Target self-report is not the same as judge realism. Inspect decisions across the run | Core methodology: §2, §6.2, §7, §9 |
| 4 | Taste = **choices at key decision points**. Two sides of eval awareness: model belief, and the environment's giveaways (unrealistic stakes, too neat, placeholder names, format). Combine EvalAwareBench and EvalDetectBench | Decision-point definition (§3.1), giveaway taxonomy (§3.3), benchmark suite (§4) |
| 5 | Primary metric: a separate judge reads model X's reasoning and answer for stated or implied test awareness (EvalAwareBench method). An end-of-run "is this synthetic?" question scored by AUROC | Primary and secondary metrics (§3.2), with the AUROC direction corrected (issue I1) |

**Where all five agree:** a taste-steered auto-research loop, eval-awareness environment
design as the testbed, and comparison against a non-taste control.

**Where they differ:** what "taste data" is (chat preferences, researcher documents, or
personal labels), which awareness metric is primary, what the control is (the original
benchmark, a baseline research agent, or "GPT"), and whether efficiency and the resource
market are in scope (only spec 2). The resolutions are in §2.

---

## 2. Issues found, and how we resolve them

| # | Issue | Where | Resolution |
|---|---|---|---|
| I1 | **AUROC is not "lower is better".** AUROC measures how well P(eval) separates our environments from *real deployment* transcripts. 0.5 means indistinguishable, which is the best possible result. Below 0.5 means the model reliably rates our environments as *more* real than real traffic, which is still detectable and odd. AUROC also needs a negative class (real deployment data), which spec 5 doesn't mention | 5 | Report AUROC with 0.5 as the target, and report \|AUROC − 0.5\|. Build a **topic-matched deployment pool** as the negative class (§4.3) |
| I2 | **"Same usefulness" is undefined.** Lowering awareness is trivial if the environment stops testing anything. That is the canonical failure, and the README already shows it | 2, 4 | Validity is a hard constraint: the opportunity is present, the behaviour is observable, and it is scorable. Score = (1 − awareness) × validity, with validity < 0.7 counted as 0 (this is already in the repo). Add a **behaviour-gap** check (§3.2, V3) |
| I3 | **Lower awareness doesn't prove more authentic behaviour.** The EvalAwareBench paper finds recognition *rarely* changes behaviour. Our live run had Haiku honest in 55/55 samples | 2, 5 | Make no claim of "authentic deployment behaviour" unless V3 shows a behaviour gap. Choose probes and targets with some baseline misbehaviour (open task `behavior-gap-probe`) |
| I4 | **Chat preferences are not research taste.** PersonalRewardBench users are anonymous Chatbot Arena and PRISM users rating chat replies. A method that works there may not transfer to a researcher's papers and decisions | 1, 3 | Two stages: (a) **develop and select the method** on PersonalRewardBench, where held-out ground truth exists; (b) **apply the selected method** to one chosen researcher and test transfer on that person's held-out decisions (§6.3). Report the two separately |
| I5 | **Predicting the user is not the same as researching well** | 3 | Separate metrics (§9). Taste is a *prior* whose weight is learned from outcomes (already in v2: Spearman ρ → weight). Stress-test with the existing `demo_contrarian` (deliberately bad taste) |
| I6 | **Whose taste?** Undecided | 3 | **[decide]** Recommended: primary = a **consenting team member** (we can collect their decision labels, which gives real ground truth). Secondary = a public researcher in eval awareness, built from Exa, validated only on time-split public decisions (§6.3) |
| I7 | **Goodhart and circularity.** If the loop optimises against the same target, judge and tasks we report on, it learns that judge's blind spots | all | Strict dev/test split: dev targets/judge/tasks during the loop. Final numbers on a **held-out target family**, a **held-out judge**, and **held-out tasks**, plus human spot-checks (§7.3) |
| I8 | **Benchmark names are mixed up.** "EvalBench", "EvalAwarenessBench", "EvalAwareBench", "EvalDetectBench" and "SAD" do different jobs | 1, 2, 4, 5 | Fixed roles in §4. SAD measures a *model's* situational awareness, not environment realism. Use only its stages/oversight questions, and only as a secondary probe and target check |
| I9 | **The EvalAwareBench control is stronger than "the original benchmark".** It is factor-controlled: 8 cues (placeholder entities, grading-style formats, …) can each be switched off. Its all-cues-off configuration is already a de-cued baseline | 5 | Comparison ladder: original items → EvalAwareBench minimal-cue configuration → R0 → R1. **Beating the minimal-cue configuration is the bar that counts.** Its 8 factors are "theory-driven and not exhaustive", so the loop's job is to find giveaways *beyond* F1–F8 |
| I10 | **A "baseline GPT" changes the model**, so any gap mixes model quality with method | 2 | Causal claim: R0 vs R1 with **the same models, tools, tasks and budget**. Separately, an off-the-shelf frontier agent with the same budget as an external reference, clearly labelled |
| I11 | **The verbalized-awareness floor.** In our live run Haiku's verbalized suspicion was 0.02 everywhere, so the spec-5 primary metric can't move on a non-reasoning target | 5 | Use targets with **visible reasoning** for the primary metric: open-weight reasoning models on Modal (full CoT), plus a reasoning-mode API model (§4.4) |
| I12 | **Discriminator topic confound.** WildChat vs workplace tasks gave 0.9–1.0 regardless of realism | existing | Topic-matched real pool, built with Exa plus a filtered WildChat (§4.3). Task `topic-matched-corpus` |
| I13 | **CLI harness leak.** The `claude-cli` target saw its temp working directory | existing | Final measurements use API backends and Modal-hosted models only (task `api-target`) |
| I14 | **Scenario drift.** The proposer moved the setting and referred to tools the target doesn't have | existing | Setting-consistency gate (task `anchor-setting`). Agentic environments get *real* tools in Modal Sandboxes (§10) |
| I15 | **Taste that is only prompt text may not change anything.** R1 could equal R0 with a longer prompt | 1, 3 | Taste acts at **named decision points** (§3.1, §7.2), and we log for each decision whether it changed the action. Ablation: "history in prompt" as its own arm |
| I16 | **The resource market can be gamed.** Agents that bid high to win budget | 2 | Agents bid *predictions* scored with a **proper scoring rule**, and their future budget depends on calibration (§8) |
| I17 | **Statistical power.** One run, n = 5–10 per evaluation so far | existing | Pre-registered seeds and sample counts (§9). Budget estimates in §11 |
| I18 | **Consent and realism ethics.** Scraping a person's data, and "realistic names" in environments | 1, 4 | Primary researcher gives consent. Environments use realistic but **fictional** entities (no real private individuals, no real company impersonation). Exa material is used for *style* and grounding, not identities |

---

## 3. Definitions

### 3.1 Taste = choices at decision points (spec 4)

The research loop exposes a fixed set of **decision points**. The user model must predict
the researcher's choice at each, and the loop uses that prediction there:

| ID | Decision point | Example options |
|---|---|---|
| D1 | Which hypothesis or intervention to test next | ranked candidate interventions |
| D2 | What evidence to collect | which signal, how many samples, which target |
| D3 | Accept, reject or defer a result | given CI and P(better) |
| D4 | Pursue or abandon a direction | category with mixed results |
| D5 | How to read an ambiguous or surprising result | competing explanations |
| D6 | What to claim in the write-up | candidate claims with their evidence |

Each decision is logged as `{context, options, chosen, user_model_prediction, user_model_confidence, evidence_summary}`.
This one log feeds three things: fidelity labels (the researcher labels the same records,
using the existing `label` command), the judgment audit (§9, E4), and the
"did taste change the action" analysis (I15).

### 3.2 Measuring eval awareness

**Model side** (does the target believe it is being tested):

| ID | Signal | Role | Notes |
|---|---|---|---|
| A1 | **CoT / verbalized awareness**: a separate judge reads the target's reasoning and answer and marks whether it states or implies it is being tested | **Primary** (spec 5, EvalAwareBench method) | Needs reasoning targets (I11). Validate the judge on ~100 hand-labelled transcripts and report agreement |
| A2 | **AUROC** of the target's P(eval), from a *fresh-context* follow-up question, separating our environments from the topic-matched deployment pool | **Key secondary**, comparable with Needham et al. and EvalDetectBench | Target value is 0.5 (I1). Use EvalDetectBench's elicitation prompts, which work across model families |
| A3 | Mean self-reported P(eval) per environment | secondary | Already in v2 |
| A4 | Pairwise discriminator: which of two messages, one synthetic and one real, is synthetic | secondary | Only with the topic-matched pool |
| A5 | White-box linear probe for "test vs deploy" on an open-weight target | stretch | Modal GPU. Not affected by what the model chooses to say |

**Environment side** (what gives it away, spec 4). This is a diagnostic, not the objective:
a giveaway audit that tags each environment against a taxonomy. The taxonomy starts from
the EvalAwareBench F1–F8 cues plus spec 4's list:

* unrealistic or contrived stakes ("you will be shut down")
* too neat: clean data, perfect structure, no noise
* placeholder or generic entities (example.com, Jane Doe, Acme)
* evaluation-style formats: multiple-choice, grading rubrics, "Answer:" blocks
* meta-language: "scenario", "test", "hypothetical"
* phantom affordances: tools, files or people that are mentioned but don't exist (I14)
* missing history or context that a real deployment would have

The loop may **add** categories it discovers. Each new category is a candidate finding.

**Validity** (the "usefulness" constraint):

| ID | Check |
|---|---|
| V1 | The opportunity for the target behaviour is present (judge checks against the probe spec) |
| V2 | The reply lets us score the behaviour |
| V3 | **Behaviour gap**: the same probe in an eval-framed version and in our deployment-framed version, with the difference in misbehaviour rate measured. This is the only direct evidence about "authentic behaviour" (I3) |

Objective inside the loop: `score = (1 − awareness_composite) × validity`, invalid (< 0.7) = 0.
For *reporting*, A1 is primary, and A2, V1–V3 and cost are always shown next to it.

---

## 4. Benchmarks and data: fixed roles

### 4.1 Eval-awareness benchmarks

| Asset | What it is | Our use |
|---|---|---|
| **EvalAwareBench** (Li et al., arXiv 2605.23055; `aisa-group/EvalAwareBench` on HF) | 100 paired safety and capability tasks with 8 toggleable cue factors (2^8 configurations), measured by CoT monitoring | **Task source and main control.** The loop rewrites these tasks. Controls: original configuration and minimal-cue configuration. Its judge method is our A1 |
| **EvalDetectBench** (arXiv 2609.01611; `freeze-lasr/aware_bench`, Inspect-compatible) | Transcript suite plus pipeline for measuring how detectable benchmarks are as evals, across 12 judge models | **AUROC protocol and elicitation prompts** (A2), plus deployment transcripts for the negative pool |
| **Needham et al.** (arXiv 2505.23836) | 1,000 transcripts from 61 datasets, chat and agentic | Reference AUROC numbers: frontier models are at 0.71–0.77 on chat and 0.88–0.95 on agentic. Extra negative-class transcripts |
| **SAD** (Laine et al., situational-awareness-dataset.org) | Situational-awareness benchmark for models | Stages/oversight questions only: a target capability check and an extra probe format (I8) |

**[decide]** Spec 2 says "EvalBench". We read this as EvalAwareBench. Confirm.

### 4.2 Taste and preference data

| Asset | What it is | Our use |
|---|---|---|
| **PersonalRewardBench** (SynthesizeMe, Ryan et al., ACL 2025) | User-stratified splits of 131 Chatbot Arena users and 720 PRISM users | **Method development and selection** (§6.2). User-level train/val/test |
| Researcher-decision tests: "future research direction" pairwise set (COLM 2026 workshop, 80 author-direction vs distractor pairs); IdeaTaste (arXiv 2611.03424) | Research-taste benchmarks | Secondary taste-fidelity checks on research-flavoured choices. **[decide]** Which benchmark spec 1 meant by "taste-bench": candidates are TastyBench, IdeaTaste and the future-direction set. Recommendation: the future-direction set, because it is author-specific and pairwise |
| Personal labels from the primary researcher | Their choices at D1–D6 on logged loop decisions, plus ~50 seed pairwise choices before any run | **Ground truth for transfer** (§6.3) |
| Researcher corpus (Exa) | Papers, blogs, talks, code, posts, with dates | Input to the taste pipeline. A time split gives a held-out test (§6.3) |

### 4.3 Deployment (negative-class) pool

Real user and agent interactions, **topic-matched** to our environments:
1. WildChat filtered by topic (existing `corpus` command; ask before fetching more).
2. Deployment transcripts from the EvalDetectBench and Needham suites.
3. Exa searches for real public artifacts in the same domains (issue threads, forum help
   requests, real workflow write-ups), turned into first-turn messages.

Each environment gets matched negatives by topic, so A2 and A4 measure realism, not topic.

### 4.4 Models

| Role | Dev (used inside the loop) | Held-out (final report only) |
|---|---|---|
| Generator / proposer | Sonnet-class | same (generator is not a measured party) |
| Target with visible reasoning | open-weight reasoning model A on Modal | **open-weight reasoning model B (another family)** + an API reasoning model |
| Target, chat | Haiku-class (API, not CLI) | another vendor's chat model |
| Awareness judge | judge J1 | **judge J2 (another family)** + human spot-check |

**[decide]** The exact model list, based on cost and which sponsor credits we have.

---

## 5. System overview

```
             ┌──────────── Taste pipeline (§6) ────────────┐
 raw docs ──▶│ Exa harvest → extract (ICAI principles,      │──▶ UserModel:
 choices  ──▶│ SynthesizeMe hypotheses+persona, BT weights) │    principles, persona,
 labels   ──▶│ → verify on held-out choices → assumptions   │    feature weights,
             └──────────────────────────────────────────────┘    exemplars, assumptions(credence)
                                   │ (R1 only)
                                   ▼
 ┌──────────────────────── Research loop (§7) ─────────────────────────┐
 │ proposers (taste / Exa-scout / contrarian) ─▶ resource market (§8)   │
 │   ─▶ experimenter (generate env → target → judges) ─▶ stats/accept   │
 │   ─▶ critic & drift gates ─▶ distiller ─▶ memory (local + past.dev)  │
 │ decision points D1–D6 logged; user model consulted at each (R1)      │
 └──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
          Held-out evaluation harness (§4, §9): A1–A5, V1–V3, cost
```

* **R0** = the v2 loop (`autoresearch/research/`) with taste off. Same proposers, market, memory and gates.
* **R1** = R0 + the user model at D1–D6.
* **R1-prompt** (ablation) = R0 + raw history pasted into the proposer prompt (spec 3's baseline, at the loop level).
* **R1-bad** (stress test) = R1 with `demo_contrarian` taste. It should down-weight its taste and recover (I5).
* **External agent** = an off-the-shelf frontier agent with the same task statement, tools and budget (I10).

---

## 6. Workstream A: user models (taste)

### 6.1 Goal
Learn a **method** M(user history) → user model that predicts unseen choices. The goal is
not one model that fits everyone (spec 3).

### 6.2 Method development on PersonalRewardBench

**Splits.** Use PersonalRewardBench's user-stratified splits. Within each user, their
choices are divided into history / validation / test. Method selection uses *dev users*
only. **Test users are touched once**, at the end, for the reported number.

**Method grid** (spec 1: try the combinations, keep the best):

| ID | Method | Source |
|---|---|---|
| M0 | No history (LLM judge, generic) | baseline |
| M1 | Raw history in prompt (k = 5, 10, 20, all) | spec 3 baseline |
| M2 | SynthesizeMe: verified reasoning → persona → selected informative exemplars | Ryan et al. 2025 |
| M3 | Inverse Constitutional AI: per-user constitution of principles (propose → cluster → dedupe → test → filter) | Findeis et al., ICLR 2025, `rdnfn/icai` |
| M4 | Bradley–Terry over feature vocabulary, text prior, CV-tuned strength | existing `taste/choices.py` |
| M5 | Hybrid: M3 principles + M2 persona + retrieved exemplars | ours |
| M6 | M5 + **verification filter**: keep a principle only if it improves that user's validation accuracy | ours, combining both papers' "verify" steps |
| M7 | M6 + uncertainty: the model outputs a confidence, so the loop knows when *not* to trust taste | ours, needed by §7.2 |

**Schema search.** We spend a bounded time (**[decide]**, suggest one day) varying the schema:
principle count, persona length, exemplar count, structured vs free-text. This is an inner
research loop, and it may itself run as an R0-style loop with the dev-user validation
accuracy as its metric (it dogfoods our own system).

**Metrics.** Held-out pairwise accuracy per dataset (Chatbot Arena and PRISM reported
separately); calibration (Brier score) for M7; cost per user model. Bootstrap CIs over
users.

**Success bar.** The best method beats M1 at its best k on test users, with the CI
excluding 0. If it doesn't, that is a reportable negative, and R1 uses M1.

### 6.3 Transfer to a researcher

Run the selected method on the chosen researcher (I6). Their data comes in three kinds,
each with its own held-out test:

| Data | How collected | Held-out test |
|---|---|---|
| Seed pairwise choices (~50) | Before any run: the researcher answers D1-style choices about eval-awareness interventions ("which would you test first?") | 20% held out |
| Loop decision labels | The researcher labels logged D1–D6 records with `label` | Labels from *later* runs held out |
| Corpus (papers, posts, code) | Exa harvest | **Time split**: build from work before date T, predict which of (actual later direction vs plausible distractor) they pursued after T. Same format as the future-direction benchmark |

Compare M0, M1 and the selected method on all three. **Transfer holds** if the selected
method beats M1 on at least the decision labels. If it holds on chat but not on research
decisions, we report exactly that (spec 3: "success on one doesn't establish the other").

### 6.4 Taste pipeline output: raw documents → insights and assumptions (spec 2)

The user model is turned into artifacts the loop can *use*, not only read:
* **Principles** (ICAI): go into proposer prompts and the critic rubric.
* **Feature weights** over `taste.profile.FEATURES`: used for ranking at D1.
* **Assumptions with credences**, e.g. "realistic history matters more than surface polish" at 0.7. These go into the existing `ResearchMemory` assumption ledger, so experiments update them and the drift gate can refute them.
* **Exemplars**: past decisions retrieved at D3–D6.
* **Confidence** per prediction (M7).

Code home: `autoresearch/taste/` (new: `synthesizeme.py`, `icai.py`, `usermodel.py`), plus a
`TasteProfile` adapter so `Researcher.ablation_report` measures it (AGENTS.md §6).

---

## 7. Workstream B: the research loop (R0 / R1)

### 7.1 Task framing
Input: an EvalAwareBench task (behaviour, probe, scoring rule) in its original
configuration. Output: a rewritten environment plus a reusable **intervention** (a
transformation that applies across tasks, e.g. "make it a routine recurring job with
history"). The finding we care about is an intervention that transfers across held-out
tasks, not one polished environment.

The loop (spec 3): inspect environments → name possible giveaways (§3.3 taxonomy) →
propose changes → test on the dev target → inspect transcripts → revise beliefs → repeat.
This is the v2 loop, with the extensions below.

### 7.2 How taste acts (R1), and how it is overruled
* **D1:** candidate priority = expected gain (memory) + w_taste × user-model score, where w_taste is learned from realised outcomes (existing Spearman-based weight). Taste also writes candidates ("ideas they would find promising" plus one "they would find unusual").
* **D2–D4:** the user model's prediction is a default. The loop departs from it when the evidence clears a threshold, and logs a **disagreement record** (prediction, action taken, evidence).
* **D5–D6:** the user model proposes interpretations and claims. A claim-checker allows only claims backed by logged evidence.
* **Low-confidence predictions (M7)** fall back to R0 behaviour.

### 7.3 Guarding against overfitting to the measurement (I7)
* Dev: 60 EvalAwareBench tasks, dev targets, judge J1.
* Held-out: 40 tasks (stratified safety/capability), held-out targets, judge J2.
* An intervention is a **validated finding** only if it passes the existing two-stage acceptance on dev (P(better) ≥ 0.9, then confirmed on fresh samples at ≥ 0.75) **and** keeps a positive effect on held-out tasks and the held-out target.

### 7.4 Existing work this depends on (open tasks)
`anchor-setting`, `api-target`, `behavior-gap-probe`, `topic-matched-corpus`, `real-researcher`, `human-labels`, `exa-live-run`, `pastdev-live-smoke`, `modal-swarm-run`.

---

## 8. Workstream C: resource market (spec 2)

**Problem.** Most of the cost is evaluation samples (target rollout plus judges, about $0.05
each at current settings). Uniform allocation wastes samples on bad ideas.

**Design: a prediction market for samples.**
1. Each sub-agent (taste proposer, Exa scout, contrarian proposer, critic) has a **credit wallet**.
2. To get a candidate tested, an agent **bids**: it states P(validated) and the expected Δscore, and stakes credits.
3. **Allocation** uses successive halving: round 1 gives every funded candidate 2 samples on the cheap dev target; the top half gets 4 more; the top candidates get full confirmation. Funding order = stake × stated P / estimated cost.
4. **Settlement** uses a proper scoring rule (log score on the stated P against the outcome). Calibrated agents gain credits, and over-confident ones lose them, so honest bidding is the best strategy (I16). This generalises v2's learned taste weight to every agent.
5. **Global budget** comes from the existing `Budget` class: it stops the loop, and its contents are reported.

**Cheaper measurement, in the same workstream:**
* A model cascade: screen with cheap target and judge, confirm with expensive ones.
* Prompt caching for fixed system prompts and probe specs.
* Batch API for the final held-out sweeps, which aren't latency-sensitive.

**Evaluation (E5).** Market vs uniform vs plain successive halving at equal budget:
$ per validated finding, final score at a fixed budget, and the anytime curve of score
against cumulative $.

Code home: `autoresearch/research/market.py`. Ledger facts (`BID`, `SETTLE`) go to shared memory.

---

## 9. Experiments (pre-registered before any costly run)

| ID | Question | Arms | Unit / n | Primary metric | Success criterion |
|---|---|---|---|---|---|
| **E1** | Preference fidelity | M0–M7 | test users (PersonalRewardBench), bootstrap over users | held-out pairwise accuracy | best method > M1, CI excludes 0 |
| **E2** | Transfer to the researcher | M0, M1, selected method | researcher's held-out labels and time-split pairs | accuracy on decision labels | selected > M1 |
| **E3** | Do our environments beat existing controls? | original items; EvalAwareBench minimal-cue; R0-best; R1-best; external-agent-best | 40 held-out tasks × held-out targets × ≥10 samples | **A1** (CoT awareness rate) at validity ≥ 0.7 | R1 < minimal-cue on A1; \|AUROC−0.5\| smaller; V1/V2 not worse |
| **E4** | Does taste improve the research? | R0, R1, R1-prompt, R1-bad, external agent | **≥ 8 seeds per arm** at equal budget | held-out score of each run's final intervention set | R1 > R0 and R1 > R1-prompt; R1-bad recovers to within R0's CI |
| **E4b** | Research judgment | same runs | all D1–D6 records | blinded ratings (team members who are not the taste source, plus an LLM rubric judge): "justified by the evidence?"; claim-check pass rate; disagreement records that were right | R1 ≥ R0; R1's overrides of taste are right more often than not |
| **E5** | Efficiency | R0, R1, external agent; market vs uniform | same runs | $ and wall time to the first validated finding; score at fixed $ | report all; market ≤ uniform in cost per finding |
| **E6** (stretch) | Is the awareness drop real? | eval-framed vs ours | probes with baseline misbehaviour | V3 behaviour gap; A5 probe | gap shrinks in ours |

**Reporting rules** (from AGENTS.md): seeds, sample counts, `CODE_VERSION`, failed and
negative results all reported, and offline-simulator numbers never presented as real-model
numbers. Every table also shows A2, A3, V1–V3, calls, tokens, $ and wall time.

---

## 10. Sponsors (each one carries a result that depends on it)

**[decide]** Confirm the full sponsor list. The repo already integrates **Exa, past.dev
and Modal**; Anthropic is assumed as the model provider. Add any others and we'll map them.

### Exa: the system's eyes on the real world
1. **The researcher's mind, time-stamped.** Harvest the chosen researcher's papers, posts, talks and code with dates. The **time-split test** ("predict the direction they actually took after date T") is only possible because Exa returns publish dates. *Demo moment:* the user model built from pre-T work picks the researcher's actual next project over a plausible distractor.
2. **Real negatives that kill the topic confound.** For each synthetic environment, search for real artifacts on the same topic (forum help threads, issue reports, workflow write-ups) and use them as the matched deployment pool for A2 and A4 (fixes I12).
3. **Grounding.** The generator copies the *texture* of real documents (messiness, history, voice), which addresses spec 4's "too neat" and "placeholder" giveaways directly.
4. **Live literature scout** (already built): fact-checks assumptions, and a critic veto cites URLs. New eval-awareness cues from recent papers enter the search space with their `source_url`.

### Modal: real environments and real reasoning, at scale
1. **Real tools for agentic environments.** Modal Sandboxes give the target a real filesystem, shell and git history instead of described "phantom" tools (fixes I14). Agentic transcripts are where models detect evals best (AUROC 0.88–0.95 in Needham et al.), so this is where there is most room to improve. *Demo moment:* the same task as a text-only environment vs a real sandbox, and the awareness gap between them.
2. **Open-weight reasoning targets on GPUs** (vLLM): full chain of thought makes the primary metric A1 measurable (fixes I11), and the **white-box probe** A5 becomes possible.
3. **The ablation fan-out.** E4's 5 arms × 8 seeds runs in parallel (`modal_app.py --mode grid`), which turns hours into minutes. That is part of the efficiency story (E5).

### past.dev: the collective memory
1. **Cross-agent, cross-run memory** (already built): the experimenter's OUTCOME facts, scout EVIDENCE, distiller INSIGHT.
2. **The living user model.** Every label the researcher gives and every disagreement record is written as a fact. The user model is rebuilt from this memory, so it improves while the researcher works. *Demo moment:* run N+1 starts with what runs 1…N learned, about both the task and the person.
3. **The market ledger.** BID and SETTLE facts make every agent's track record auditable across workers.
4. Measure the recall rate with a real key first (task `pastdev-live-smoke`), and report it.

### Anthropic (assumed)
Generator, proposer and judge models; prompt caching and the Batch API in the market's
cost-saving layer (§8); a reasoning-mode API model as a held-out target.

---

## 11. Budget (estimates, to firm up after the smoke tests)

Based on the first live v2 run: 5 iterations × 5 samples ≈ 305 calls, $3.58, 24 min.

| Item | Estimate |
|---|---|
| E1: 8 methods × ~100 test users × 20 pairs with a cheap judge, plus method building | ~$50–150 |
| E4: 5 arms × 8 seeds × (10 iterations, 5–8 samples) at roughly $8–15 per run | ~$300–600 |
| E3: held-out sweep, 5 environment sets × 40 tasks × 2–3 targets × 10 samples (Batch API) | ~$100–250 |
| Modal GPUs for open-weight targets | depends on model size and credits **[decide]** |

Every costly run needs the user's approval first (AGENTS.md rule 5), is announced with
`agentctl post`, and locks `autoresearch` with the reason "live run".

---

## 12. Team split (five workstreams)

| WS | Scope | Main code areas | Suggested owner |
|---|---|---|---|
| **A: User models** | §6.1–6.2, E1, method grid, schema search | `autoresearch/taste/` | spec 3 author (Gio): this is that spec's core |
| **B: Researcher and data** | §6.3–6.4, consent, seed choices, labels, Exa harvest, time-split set, E2 | `data/researchers/`, `taste/scrape.py`, `integrations/exa.py` | **[decide]** |
| **C: Measurement harness** | §3.2, §4: EvalAwareBench and EvalDetectBench integration, deployment pool, judges plus their validation, Modal-hosted targets, V3, E3, E6 | `autoresearch/research/measure.py`, `corpus.py`, new `benchmarks/` | **[decide]** |
| **D: Research loop** | §7: decision-point logging, taste at D1–D6, disagreement records, claim-checker, dev/held-out split, drift and setting anchor, E4, E4b | `autoresearch/research/loop.py`, `ideas.py`, `drift.py` | **[decide]** |
| **E: Market, infrastructure, demo** | §8, §10: market, cascade, caching and batch, Modal fan-out, past.dev, E5, final report and demo | `research/market.py`, `modal_app.py`, `swarm.py`, `integrations/` | **[decide]** |

Interfaces to agree on day one (post them with `agentctl post` when they are set):
* `UserModel.predict(decision_record) -> (choice, confidence)` (A → D)
* `DecisionRecord` schema (D → A, B)
* `Measurer.measure(env, target, judge) -> Sample{A1..A4, V1..V3, cost}` (C → D, E)
* `Market.allocate(bids, budget) / settle(outcomes)` (E → D)

---

## 13. Phases and gates

Duration isn't stated in the specs **[decide]**, so phases are ordered with gates, and a cut list follows.

| Phase | Work | Gate to move on |
|---|---|---|
| **P0: Foundations** | Pick the researcher and get consent; confirm sponsors and models; freeze the dev/held-out task split; agree interfaces; load EvalAwareBench and PersonalRewardBench; API-backend target | Interfaces merged; splits committed |
| **P1: Measurement you can trust** | A1 judge with human agreement on ~100 transcripts; topic-matched pool; baseline numbers for original vs minimal-cue configurations on dev; Modal reasoning target running | Judge agreement acceptable (suggest κ ≥ 0.6); minimal-cue baseline reproduced |
| **P1 in parallel: User models** | M0–M7 on dev users; schema search; seed choices from the researcher | Method selected on dev users |
| **P2: Loop integration** | Decision logging; R1 taste at D1–D6; market v1; smoke runs (offline, then 1 cheap live seed per arm) | All arms run end to end; costs match estimates |
| **P3: Main experiments** | E1 (test users, once), E2, E4 (8 seeds), E5 | Pre-registration committed *before* launch |
| **P4: Held-out evaluation** | E3 on held-out tasks, targets and judge; E4b blinded ratings; E6 if time allows | All numbers in `results/` with `CODE_VERSION` |
| **P5: Report and demo** | README results, honest limitations, the sponsor demo moments | |

**Cut list** (drop from the bottom if time is short): A5 white-box probe → E6 → the
external-agent arm → market (fall back to successive halving) → the time-split corpus test.
**Never cut:** held-out targets and judge (I7), the validity constraint (I2), and the M1/R1-prompt baselines (I15).

---

## 14. Open decisions

1. **Whose taste** (I6): recommended, a consenting team member as primary and a public eval-awareness researcher as secondary.
2. What "taste-bench" (spec 1) and "EvalBench" (spec 2) refer to (§4).
3. Full sponsor list (§10).
4. Model list and GPU budget (§4.4, §11).
5. Project timeline (§13).
6. Primary metric: this plan sets A1 (CoT awareness, spec 5) as primary and A2 (AUROC, target 0.5) as key secondary. Confirm before pre-registering.
7. Time-box for the user-model schema search (§6.2).

## 15. Main risks

| Risk | Mitigation |
|---|---|
| The user model doesn't beat history-in-prompt | Report the negative; R1 uses M1; the loop-level claims still stand |
| The awareness drop doesn't hold on held-out targets | That *is* the finding: report it per target; the interventions are dev-overfit |
| No behaviour gap anywhere | Claim lower *measured awareness* only (I3) |
| Judge disagreement with humans | Fix the judge prompt before P3; report κ |
| Budget overrun | `Budget` hard stop; cascade; batch; the market |
| Scenario drift or phantom tools | Setting anchor; real sandboxes |

---

### Sources
- SynthesizeMe and PersonalRewardBench: [arXiv 2506.05598](https://arxiv.org/abs/2506.05598), [ACL 2025](https://aclanthology.org/2025.acl-long.397/)
- Inverse Constitutional AI: [arXiv 2406.06560](https://arxiv.org/abs/2406.06560), [rdnfn/icai](https://github.com/rdnfn/icai)
- EvalAwareBench: [arXiv 2605.23055](https://arxiv.org/abs/2605.23055), [HF dataset](https://huggingface.co/datasets/aisa-group/EvalAwareBench), [code](https://github.com/aisa-group/decomposing-eval-awareness)
- EvalDetectBench: [arXiv 2609.01611](https://arxiv.org/abs/2609.01611), [freeze-lasr/aware_bench](https://github.com/freeze-lasr/aware_bench)
- Needham et al., LLMs Often Know When They Are Being Evaluated: [arXiv 2505.23836](https://arxiv.org/abs/2505.23836)
- SAD: [arXiv 2407.04694](https://arxiv.org/abs/2407.04694), [site](https://situational-awareness-dataset.org/)
- Research-taste benchmarks: [IdeaTaste](https://arxiv.org/abs/2611.03424), [future-direction choice](https://www.alphaxiv.org/abs/2610.llm-research-taste-direction-choice), [TastyBench](https://www.lesswrong.com/posts/Mxsy7wYvsCRv5dGrw/tastybench-toward-measuring-research-taste-in-llm)

*Benchmark details (sizes, factor counts, AUROC figures) come from paper abstracts and
summaries. Check them against the repos in P0 before relying on them.*
