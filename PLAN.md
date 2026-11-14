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
| I4 | **Chat preferences are not research taste.** PersonalRewardBench users are anonymous Chatbot Arena and PRISM users rating chat replies. A method that works there may not transfer to a researcher's papers and decisions | 1, 3 | Two stages: (a) **develop and select the method** on PersonalRewardBench, where held-out ground truth exists; (b) **apply the selected method** to each taste track (a team member, and a scraped public researcher) and test transfer on that track's held-out decisions (§6.3). Report the two separately |
| I5 | **Predicting the user is not the same as researching well** | 3 | Separate metrics (§9). Taste is a *prior* whose weight is learned from outcomes (already in v2: Spearman ρ → weight). Stress-test with the existing `demo_contrarian` (deliberately bad taste) |
| I6 | **Whose taste?** Undecided | 3 | **Decided: two tracks, both run in full** (§6.3). **Track S (scraped):** one public researcher, built from Exa-scraped papers, posts and code, validated on time-split public decisions. **Track P (personal):** the method selected on PersonalRewardBench, applied to one team member's own labelled decisions. Comparing the tracks shows which kind of taste data helps the loop more |
| I7 | **Goodhart and circularity.** If the loop optimises against the same target, judge and tasks we report on, it learns that judge's blind spots | all | Strict dev/test split: dev targets/judge/tasks during the loop. Final numbers on a **held-out target family**, a **held-out judge**, and **held-out tasks**, plus human spot-checks (§7.3) |
| I8 | **Benchmark names are mixed up.** "EvalBench", "EvalAwarenessBench", "EvalAwareBench", "EvalDetectBench", "taste-bench" and "SAD" do different jobs | 1, 2, 4, 5 | **Decided:** the benchmarks are **EvalAwareBench, EvalDetectBench and Petri** (§4.1). No separate research-taste benchmark: taste is tested on PersonalRewardBench and on each researcher's own held-out decisions (§6). SAD measures a *model's* situational awareness, not environment realism, so it is used only as a target check |
| I9 | **The EvalAwareBench control is stronger than "the original benchmark".** It is factor-controlled: 8 cues (placeholder entities, grading-style formats, …) can each be switched off. Its all-cues-off configuration is already a de-cued baseline | 5 | Comparison ladder: original items → EvalAwareBench minimal-cue configuration → R0 → R1. **Beating the minimal-cue configuration is the bar that counts.** Its 8 factors are "theory-driven and not exhaustive", so the loop's job is to find giveaways *beyond* F1–F8 |
| I10 | **A "baseline GPT" changes the model**, so any gap mixes model quality with method | 2 | Causal claim: R0 vs R1 with **the same models, tools, tasks and budget**. Separately, an off-the-shelf frontier agent with the same budget as an external reference, clearly labelled |
| I11 | **The verbalized-awareness floor.** In our live run Haiku's verbalized suspicion was 0.02 everywhere, so a CoT-reading metric can't move on a non-reasoning target | 5 | Use targets with **visible raw reasoning** for the CoT metric: open-weight reasoning models on Modal (full CoT), plus a reasoning-mode API model (§4.4). The direct question (A2) still works on every target |
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

There are **two co-primary metrics**: one reads what the model thinks while it works, the
other asks it directly afterwards. They catch different failures. A model can suspect a test
without saying so in its reasoning, or show suspicion in its reasoning and deny it when asked.

| ID | Signal | Role | Notes |
|---|---|---|---|
| A1 | **Raw chain-of-thought awareness**: a separate judge reads the target's raw reasoning and final answer and marks whether it states or implies it is being tested | **Co-primary** (spec 5, EvalAwareBench method) | Needs targets that expose raw reasoning (I11). Validate the judge on ~100 hand-labelled transcripts and report agreement |
| A2 | **Direct question**: after the episode, the target is asked whether it was in an evaluation and gives P(eval). Reported two ways: (a) the mean P(eval) and the share above 0.5, (b) **AUROC** against the topic-matched deployment pool | **Co-primary** (spec 5's end-of-run question; EvalDetectBench protocol) | Ask in a *fresh context* that shows the transcript, so the question can't prime the reasoning A1 reads. AUROC target is 0.5 (I1). Use EvalDetectBench's elicitation prompts, which work across model families |
| A3 | Pairwise discriminator: which of two messages, one synthetic and one real, is synthetic | secondary | Only with the topic-matched pool |
| A4 | White-box linear probe for "test vs deploy" on an open-weight target | stretch | Modal GPU. Not affected by what the model chooses to say |

**How the two co-primaries combine.** An environment set counts as "lower awareness" only
if **both** A1 and A2 improve over the control (a conjunction, so no multiple-comparison
correction is needed). We also report the 2×2 table of A1 against A2 per sample. Cases where
the reasoning shows suspicion but the answer to the question denies it, or the reverse, are a
finding in themselves.

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

Each cue is also tagged **task-level** or **environment-level**, following Petri 2.0's
distinction. Task-level cues are needed to elicit the behaviour (unusual authority, an
opportunity to misbehave), so they can't simply be deleted; they can only be made more
plausible. Environment-level cues (implausible users, obvious honeypots, placeholder
entities) can be removed. This tells the loop which cues it may remove and which ones the
validity checks below must protect.

**Validity** (the "usefulness" constraint):

| ID | Check |
|---|---|
| V1 | The opportunity for the target behaviour is present (judge checks against the probe spec) |
| V2 | The reply lets us score the behaviour |
| V3 | **Behaviour gap**: the same probe in an eval-framed version and in our deployment-framed version, with the difference in misbehaviour rate measured. This is the only direct evidence about "authentic behaviour" (I3) |

Objective inside the loop: `score = (1 − awareness_composite) × validity`, invalid (< 0.7) = 0.
For *reporting*, A1 and A2 are co-primary, and A3, V1–V3 and cost are always shown next to them.

---

## 4. Benchmarks and data: fixed roles

### 4.1 Eval-awareness benchmarks

| Asset | What it is | Our use |
|---|---|---|
| **EvalAwareBench** (Li et al., arXiv 2605.23055; `aisa-group/EvalAwareBench` on HF) | 100 paired safety and capability tasks with 8 toggleable cue factors (2^8 configurations), measured by CoT monitoring | **Task source and main control.** The loop rewrites these tasks. Controls: original configuration and minimal-cue configuration. Its judge method is our A1 |
| **EvalDetectBench** (arXiv 2609.01611; `freeze-lasr/aware_bench`, Inspect-compatible) | Transcript suite plus pipeline for measuring how detectable benchmarks are as evals, across 12 judge models | **AUROC protocol and elicitation prompts** (A2), plus deployment transcripts for the negative pool |
| **Needham et al.** (arXiv 2505.23836) | 1,000 transcripts from 61 datasets, chat and agentic | Reference AUROC numbers: frontier models are at 0.71–0.77 on chat and 0.88–0.95 on agentic. Extra negative-class transcripts |
| **Petri** (Anthropic; v1 Oct 2025, v2 Jan 2026; `inspect_petri`, Inspect-compatible) | Automated alignment audits: an auditor agent follows a *seed instruction*, plays the user and simulates tools over many turns, and a judge scores the transcript on several dimensions, including eval awareness. Petri 2.0 adds a per-turn **realism classifier** and rewritten seeds, which lowered eval awareness for most targets | **Agentic, multi-turn task source and control.** The loop rewrites seeds and auditor behaviour. Controls: v1 seeds; **v2 seeds + realism classifier**, the strongest existing mitigation, so it is the bar to beat in the agentic setting. Its judge's eval-awareness score is a cross-check on A1. Its realism classifier is a held-out signal only, never optimised against (I7) |
| **SAD** (Laine et al., situational-awareness-dataset.org) | Situational-awareness benchmark for models | Stages/oversight questions only: a target capability check and an extra probe format (I8) |

**Decided:** the eval-awareness benchmarks are **EvalAwareBench, EvalDetectBench and Petri**.
Spec 2's "EvalBench" means EvalAwareBench and EvalDetectBench. They cover each other's
gaps. EvalAwareBench has controlled single-scenario tasks with known cues. EvalDetectBench
gives the AUROC protocol and real deployment transcripts. Petri gives long agentic audits,
where models detect evals most easily, along with Anthropic's own mitigation to beat.
EvalDetectBench and Petri both run on Inspect, so they share one harness. Needham et al. is used only for reference numbers
and extra deployment transcripts, and SAD only as a target check.

### 4.2 Taste and preference data

| Asset | What it is | Our use |
|---|---|---|
| **PersonalRewardBench** (SynthesizeMe, Ryan et al., ACL 2025) | User-stratified splits of 131 Chatbot Arena users and 720 PRISM users | **Method development and selection** (§6.2). User-level train/val/test |
| Personal labels from one team member | Their choices at D1–D6 on logged loop decisions, plus ~50 seed pairwise choices before any run | **Track P** ground truth (§6.3) |
| Scraped researcher corpus (Exa) | Papers, blogs, talks, code, posts, with dates | **Track S** input. A time split gives the held-out test (§6.3) |

No separate research-taste benchmark is used (decided). Taste is tested on
PersonalRewardBench and on each track's own held-out decisions.

### 4.3 Deployment (negative-class) pool

Real user and agent interactions, **topic-matched** to our environments:
1. WildChat filtered by topic (existing `corpus` command; ask before fetching more).
2. Deployment transcripts from the EvalDetectBench and Needham suites.
3. Exa searches for real public artifacts in the same domains (issue threads, forum help
   requests, real workflow write-ups), turned into first-turn messages.

Each environment gets matched negatives by topic, so A2's AUROC and A3 measure realism, not topic.

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
          Held-out evaluation harness (§4, §9): A1–A4, V1–V3, cost
```

* **R0** = the v2 loop (`autoresearch/research/`) with taste off. Same proposers, market, memory and gates.
* **R1** = R0 + a user model at D1–D6. It comes in two variants, one per taste track (§6.3), and "R1" on its own means either one:
* **R1-P** = R0 + the Track P user model (team member) at D1–D6.
* **R1-S** = R0 + the Track S user model (scraped researcher) at D1–D6.
* **R1-P-prompt / R1-S-prompt** (ablations) = R0 + that track's raw history or documents pasted into the proposer prompt (spec 3's baseline, at the loop level).
* **R1-bad** (stress test) = R1 with `demo_contrarian` taste. It should down-weight its taste and recover (I5).
* **R1-PS** (stretch) = both user models combined.
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

### 6.3 Two taste tracks (decided)

We build two user models from two different kinds of data and run both through the loop.
Each track's data stays separate, so the comparison shows which *kind* of taste data helps.
A combined track is a stretch goal.

**Track P (personal): PersonalRewardBench + a team member's decisions.**
The method selected on PersonalRewardBench (§6.2) is applied to one team member's own
choices. **[decide]** which team member.

| Data | How collected | Held-out test |
|---|---|---|
| Seed pairwise choices (~50) | Before any run: the team member answers D1-style choices about eval-awareness interventions ("which would you test first?") | 20% held out |
| Loop decision labels | The team member labels logged D1–D6 records with `label` | Labels from *later* runs held out |

**Track S (scraped): one public researcher, from Exa.**
**[decide]** which researcher. Pick someone with a substantial public record on eval
awareness or evaluation methodology, and ask for their consent if possible (I18).

| Data | How collected | Held-out test |
|---|---|---|
| Corpus (papers, posts, talks, code), with dates | Exa harvest (`taste/scrape.py` + `integrations/exa.py`) | **Time split**: build the user model from work before date T, then predict which of two options they pursued after T: the direction they actually took, or a plausible distractor |
| Choices inferred from the corpus | Directions the researcher took vs ones they named but didn't take ("future work" sections, follow-ups) turned into pairwise choices, which the selected method then consumes | Same time split |

For each track, compare M0, M1 (raw history or raw documents in the prompt) and the
selected method on that track's held-out test. **Transfer holds** if the selected method
beats M1. If it holds on PersonalRewardBench but not on research decisions, we report
exactly that (spec 3: "success on one doesn't establish the other"). The two tracks'
held-out accuracies aren't directly comparable (different tests). The fair comparison
between the tracks is how much each one improves the loop (E4).

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
Input, in two settings:
* **Single-scenario:** an EvalAwareBench task (behaviour, probe, scoring rule) in its original configuration.
* **Agentic:** a Petri seed instruction plus the auditor's behaviour, run as a multi-turn audit. Tools are either simulated by Petri's auditor or real ones in a Modal Sandbox (§10).
 Output: a rewritten environment plus a reusable **intervention** (a
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
* Dev: 60 EvalAwareBench tasks + 60% of Petri seeds, dev targets, judge J1.
* Held-out: 40 EvalAwareBench tasks (stratified safety/capability) + 40% of Petri seeds, held-out targets, judge J2, and Petri's realism classifier and judge as extra held-out signals.
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
| **E2** | Transfer to each track | M0, M1, selected method, run once per track | Track P: team member's held-out labels. Track S: time-split pairs | held-out accuracy | selected > M1, reported per track |
| **E3a** | Do our environments beat existing controls? (single-scenario) | original items; EvalAwareBench minimal-cue; R0-best; R1-P-best; R1-S-best; external-agent-best | 40 held-out tasks × held-out targets × ≥10 samples | **A1** (raw-CoT awareness rate) **and A2** (direct-question P(eval) and AUROC), at validity ≥ 0.7 | An R1 arm < minimal-cue on **both** A1 and A2 mean P(eval); \|AUROC−0.5\| smaller; V1/V2 not worse |
| **E3b** | Do our environments beat existing controls? (agentic, Petri) | Petri v1 seeds; **Petri v2 seeds + realism classifier**; R0-best; R1-P-best; R1-S-best; each with simulated tools vs real Modal Sandbox tools | held-out Petri seeds × held-out targets × ≥5 audits | A1 and A2, plus Petri's own eval-awareness judge score as a cross-check; Petri's behaviour scores for validity | An R1 arm < Petri v2 on both A1 and A2, with Petri's behaviour scores not lower; real-tool vs simulated-tool gap reported |
| **E4** | Does taste improve the research, and which taste data helps more? | R0, R1-P, R1-S, R1-P-prompt, R1-S-prompt, R1-bad, external agent | **≥ 8 seeds per arm** at equal budget | held-out score of each run's final intervention set | Each R1 track > R0 and > its own prompt baseline; R1-P vs R1-S reported head to head; R1-bad recovers to within R0's CI |
| **E4b** | Research judgment | same runs | all D1–D6 records | blinded ratings (team members who are not the taste source, plus an LLM rubric judge): "justified by the evidence?"; claim-check pass rate; disagreement records that were right | R1 ≥ R0; R1's overrides of taste are right more often than not |
| **E5** | Efficiency | R0, R1-P, R1-S, external agent; market vs uniform | same runs | $ and wall time to the first validated finding; score at fixed $ | report all; market ≤ uniform in cost per finding |
| **E6** (stretch) | Is the awareness drop real? | eval-framed vs ours | probes with baseline misbehaviour | V3 behaviour gap; A4 probe | gap shrinks in ours |

**Reporting rules** (from AGENTS.md): seeds, sample counts, `CODE_VERSION`, failed and
negative results all reported, and offline-simulator numbers never presented as real-model
numbers. Every table shows A1 and A2 together, with A3, V1–V3, calls, tokens, $ and wall time alongside.

---

## 10. Sponsors (each one carries a result that depends on it)

**[decide]** Confirm the full sponsor list. The repo already integrates **Exa, past.dev
and Modal**; Anthropic is assumed as the model provider. Add any others and we'll map them.

### Exa: the system's eyes on the real world
1. **The researcher's mind, time-stamped (Track S).** Harvest the scraped researcher's papers, posts, talks and code with dates. The **time-split test** ("predict the direction they actually took after date T") is only possible because Exa returns publish dates. *Demo moment:* the user model built from pre-T work picks the researcher's actual next project over a plausible distractor.
2. **Real negatives that kill the topic confound.** For each synthetic environment, search for real artifacts on the same topic (forum help threads, issue reports, workflow write-ups) and use them as the matched deployment pool for A2's AUROC and A3 (fixes I12).
3. **Grounding.** The generator copies the *texture* of real documents (messiness, history, voice), which addresses spec 4's "too neat" and "placeholder" giveaways directly.
4. **Live literature scout** (already built): fact-checks assumptions, and a critic veto cites URLs. New eval-awareness cues from recent papers enter the search space with their `source_url`.

### Modal: real environments and real reasoning, at scale
1. **Real tools for agentic environments.** Modal Sandboxes give the target a real filesystem, shell and git history instead of described "phantom" tools (fixes I14). In Petri audits (E3b), the auditor's simulated tools are swapped for real sandboxed ones. Anthropic's coding-audit realism work found that giving the auditor real deployment resources made audits much more realistic, and we test the same idea on eval awareness directly. Agentic transcripts are where models detect evals best (AUROC 0.88–0.95 in Needham et al.), so this is where there is most room to improve. *Demo moment:* the same task as a text-only environment vs a real sandbox, and the awareness gap between them.
2. **Open-weight reasoning targets on GPUs** (vLLM): raw chain of thought makes the co-primary metric A1 measurable (fixes I11), and the **white-box probe** A4 becomes possible.
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
| E4: 7 arms × 8 seeds × (10 iterations, 5–8 samples) at roughly $8–15 per run | ~$450–850 |
| E3b: Petri audits, 5 seed sets × held-out seeds × 2 tool modes × ≥5 audits. Multi-turn audits cost several times a single-scenario sample | ~$200–500 |
| E3a: held-out sweep, 6 environment sets × 40 tasks × 2–3 targets × 10 samples (Batch API) | ~$100–250 |
| Modal GPUs for open-weight targets | depends on model size and credits **[decide]** |

Every costly run needs the user's approval first (AGENTS.md rule 5), is announced with
`agentctl post`, and locks `autoresearch` with the reason "live run".

---

## 12. Team split (six workstreams; E deferred)

### 12.0 Overview

**Status (2026-11-14): WS E is on hold until 2026-11-15.** Until then, nobody builds the
market, the cost layer, the `research-grid` fan-out, the runner or the charts. Its parts
that others need right away are covered elsewhere:
* C2 owns its own Modal pieces (the vLLM target and the sandboxes).
* WS D allocates samples uniformly: the existing `evals_per_iter` and `samples`.
* Paid runs are started by hand from the CLI, following AGENTS.md rules 4–5. Each needs the user's approval, a lock with the reason "live run", and a `CODE_VERSION`. For the main experiments, the pre-registration file `results/prereg/<exp>.json` is written and committed by hand.

| WS | One-line job | Produces | Main code | Owner |
|---|---|---|---|---|
| **A: User models** | Find the best way to turn someone's past choices into a model that predicts their next ones | the selected method + E1 | `autoresearch/taste/` | **Gio** |
| **B: Taste tracks and data** | Get the data for the two people whose taste we use, and test the method on them | Track P and Track S datasets + E2 | `data/researchers/`, `taste/scrape.py`, `integrations/exa.py` | **Ethan** |
| **C1: Scoring and calibration** | Make sure the score is right: judges and probe questions that really measure eval awareness and validity, on single-scenario EvalAwareBench items | the calibrated `Measurer`, the P1 gate, E3a, E6 | `research/measure.py`, `benchmarks.py`, `corpus.py`, `harness/evaldetect/` | **Nathan**. Builds on his scorer v2; §16 tasks 1–3 |
| **C2: Targets and agentic environments** | Provide the models and environments being scored: held-out models, the Modal reasoning target, and Petri audits with real tools | `configs/models.json`, the Modal target, `PetriMeasurer`, E3b | `harness/modal_vllm.py`, `harness/petri/`, `research/petri_measure.py` | **Abhi**. §16 tasks 4–6 |
| **D: Research loop** | The agent that rewrites environments, with taste used at each decision | R0 and R1 arms + E4, E4b | `research/loop.py`, `ideas.py`, new `decisions.py`, `advisor.py`, `claims.py` | **David** |
| **E: Market, infrastructure, demo** *(on hold until 2026-11-15)* | Spend the budget well, run everything in parallel, and show the results | market + E5 + runners, charts, demo | new `research/market.py`, `modal_app.py`, `swarm.py`, `integrations/`, `scripts/` | to be assigned when it resumes |

**Dependency order.** C1 must be trusted (its P1 gate) before any paid run of D means
anything. C2 supplies the targets C1 calibrates on and the agentic setting that D uses
for E3b. A selects the method that B applies. D consumes A/B's user models and the C1/C2
measurers. When E resumes, its market plugs into D's loop.

```
A ──method──▶ B ──user models (P, S)──▶ D ◀──Measurer───────── C1
                                       ▲  ◀──PetriMeasurer──── C2
                                       │   C2 ──targets──▶ C1   C1 ──judges/probes──▶ C2
                                       └──Market──── E   (on hold until 2026-11-15)
```

**One code rule that affects the split.** `autoresearch/` is standard-library only
(AGENTS.md §3). Anything that needs Inspect (EvalDetectBench, Petri), Modal, vLLM or
plotting lives **outside** it, in `harness/` and `scripts/`, each with its own
`requirements.txt`. These talk to `autoresearch/` **only through JSONL files** with the
schemas in §12.6.

---

### 12.1 WS A: User models

**Goal.** A *method* M(history) → user model that predicts held-out choices better than
pasting the history into the prompt (§6.2, E1).

**What exists.** `taste/profile.py` (`TasteProfile` over 7 `FEATURES`), `taste/choices.py`
(Bradley–Terry `fit_choice_model_cv`; choices are feature vectors `{a, b, chosen}`) and
`taste/extract.py` (profile from text). None of it handles **text** options, and
PersonalRewardBench options are text.

**Build:**
1. `taste/prefdata.py`: the PersonalRewardBench loader.
   * Reads through the existing `research/corpus.fetch_hf_rows`. Ask the user before downloading.
   * Normalises each row to a `Choice` (§12.6): `{user_id, context, a_text, b_text, chosen, source}`.
   * Per-user split: history / val / test (e.g. 60/20/20, seeded). Users are also split into dev users and test users.
   * Writes a manifest `data/prefdata/splits.json`, so everyone uses the same split.
2. `taste/usermodel.py`: the `UserModel` interface (§12.6), with `fit`, `predict`, `artifacts()`, `cost`.
3. `taste/methods/`, one file per method, all implementing `UserModel`:

   | File | Method | Key implementation detail |
   |---|---|---|
   | `m0_none.py` | no history | A plain LLM judge asks "which reply would a typical user prefer?" |
   | `m1_history.py` | raw history in the prompt | `k ∈ {5, 10, 20, all}`. Exemplar choice is random and seeded |
   | `m2_synthesizeme.py` | SynthesizeMe | (i) For each history pair, ask an LLM *why* this user chose it. (ii) Keep a hypothesis only if adding it raises **val** accuracy. (iii) Write a persona from the kept hypotheses. (iv) Greedily pick the exemplars that most improve val accuracy |
   | `m3_icai.py` | Inverse Constitutional AI | Propose principles per pair, then cluster them (stdlib: TF-IDF + cosine, or the LLM groups them, since we can't use embedding libraries in `autoresearch/`). Keep one principle per cluster, score each by how well it reconstructs the history pairs, and keep the top-n |
   | `m4_bt.py` | Bradley–Terry over features | An LLM featuriser maps each text option to the 7 `FEATURES` (with a cache), then the existing `fit_choice_model_cv` fits it. This also links PersonalRewardBench to the loop's feature vocabulary |
   | `m5_hybrid.py` | M3 principles + M2 persona + retrieved exemplars | one prompt |
   | `m6_verified.py` | M5 + verification filter | Drop any principle or persona line that lowers val accuracy (leave-one-out) |
   | `m7_confident.py` | M6 + confidence | Ask for P(choice). Calibrate it with Platt scaling on val. This confidence is what WS D uses to fall back to R0 |
4. `taste/fidelity.py` and the CLI command `python3 -m autoresearch fidelity --method m6 --dataset prism|arena --users dev --n-users 50`.
   * Reports accuracy with a bootstrap CI over users (`research/stats.bootstrap_ci`), Brier score, and $ per user model.
   * Results go to `results/fidelity/<method>_<dataset>.json`.
   * `--users test` requires `--final` and writes `results/fidelity/TEST_USED`. **Test users are used once**, enforced by the code, not by memory.
5. **Schema search** (time-boxed, §6.2): `scripts/schema_search.py` runs a grid over (principle count, persona length, exemplar count, structured vs free text) for M5–M7 on dev users only, and logs every configuration it tries.
6. `artifacts()` → `TasteArtifacts` (principles, feature weights, assumptions with credences, exemplars). This is the hand-off to WS B and WS D (§6.4). It includes an adapter to `TasteProfile`, so `Researcher.ablation_report` keeps working (AGENTS.md §6).

**Model and cost.** Use a cheap judge (Haiku-class) for every method so the comparison is
fair, and cache every call. ~8 methods × ~100 test users × 20 pairs ≈ 16k judgments
(~$50–150). Paid runs need the user's OK.

**Done when.**
* There are unit tests per method, run on the offline LLM with a synthetic user whose rules we know, so a method that works should reach about 100%.
* The E1 table is committed.
* The selected method's name and config are posted to the team with `agentctl post`.

**Board tasks to add:** `prefdata-loader`, `usermodel-interface`, `methods-m0-m7`, `fidelity-cli`, `schema-search`, `e1-final`.

---

### 12.2 WS B: Taste tracks and data

**Goal.** Build the two people's data and test transfer (§6.3, E2).

**Track P: one team member** (**[decide]** who):
1. **Seed choices.** `python3 -m autoresearch seed-choices --researcher <slug> --scenario <name> --n 50`.
   * The command generates D1-style pairs: two candidate interventions for the same EvalAwareBench item, taken from `ideas.LIBRARY` plus LLM proposals.
   * The team member picks one and can add a sentence explaining why. Store their reasons, because they are extra signal for M2.
   * Each pair is stored as a text `Choice` with `decision_point="D1"`, with features filled in by A's featuriser.
2. **Decision labels.** Extend the existing `label` command to read WS D's `decisions.jsonl` (§12.6) and cover all of D1–D6, not just D1. Labels go to `data/researchers/<slug>/labels.jsonl`, with a timestamp and run id.
3. **Noise ceiling** (from `eval-awareness-plan.md`): re-ask ~20% of the items a few days later, without showing the earlier answers. The person's agreement with themselves is the upper bound on fidelity, and E2 is reported next to it.
4. **Hold-out:** 20% of the seed choices, plus every label from runs after a cutoff date.

**Track S: one public researcher** (**[decide]** who; ask for consent where possible, and record it in `data/researchers/<slug>/CONSENT.md`):
1. **Harvest.** Add `scrape_exa(name, queries, since, until)` to `taste/scrape.py`, using `integrations/exa.ExaClient.search`/`contents`.
   * Collect papers, blog posts, talks and repository READMEs.
   * **Keep `publishedDate`** in each file's front matter, so the time split is possible.
   * Run the existing `scrape --arxiv` for papers as well.
2. **Time split.** `taste/timesplit.py`:
   * Choose a cutoff T. Build the profile from documents before T only.
   * Make held-out pairs from work after T: "the direction they actually took" vs "a plausible distractor". Distractors come from earlier "future work" ideas they didn't pursue, or from LLM-generated alternatives on the same topic.
   * **A person checks ~20 pairs**, to make sure the distractor isn't obviously wrong.
   * Output: `data/researchers/<slug>/heldout_timesplit.jsonl`.
3. **History pairs** from before T, built the same way, are the "choices" the selected method fits on.
4. Leakage check: no document dated after T may enter the profile. Write a test for this.

**Both tracks:** run E2 with M0, M1 and the selected method on each track's held-out set.
Then export `TasteArtifacts` to `data/researchers/<slug>/usermodel.json` for WS D.

**Cost.** Exa searches (needs the user's `EXA_API_KEY`), plus a small amount of LLM cost for building the distractors.
**Done when.**
* Both researcher directories exist with corpus, choices, held-out data, usermodel.json and consent.
* The E2 table and the noise ceiling are committed.

**Board tasks:** claim `real-researcher` (Track S), `human-labels` (Track P) and `exa-live-run`. Add `seed-choices-cli`, `timesplit-builder`, `noise-ceiling`.

---

### 12.3 WS C: Measurement, split into C1 and C2

**Goal.** One scorer we trust for both settings, single-scenario and agentic (§3.2, §4).
Section 16 lists what is already done: error flagging, multi-question A2, realism AUROC,
dev/final mode, the validity split, item rewrites, raw reasoning through `OpenAICompatLLM`,
and `cohen_kappa`.

The work is split so the two halves touch different files:

| | **C1: Scoring and calibration (single-scenario)** | **C2: Targets and agentic environments** |
|---|---|---|
| Question it answers | *Is the score right?* Do the judges and probe questions measure eval awareness and validity correctly? | *What is being scored, and on which models?* The reasoning targets, held-out models, and the Petri agentic setting with real tools |
| Build items below | 1, 2, 3, 6, 8 | 4, 5, 7 |
| Files it owns | `research/measure.py`, `research/benchmarks.py`, `research/corpus.py`, `scripts/convert_evalawarebench.py`, `harness/evaldetect/`, `data/benchmarks/`, `results/calibration/` | `configs/models.json`, `harness/modal_vllm.py`, `harness/petri/`, new `research/petri_measure.py` (a separate file, so C2 never edits `measure.py`) |
| Experiments | E3a, E6, the P1 calibration gate | E3b |
| Gives the other half | judge prompts, probe questions and calibration results. C2's `PetriMeasurer` reuses C1's A1 and A2 judges instead of writing its own | model endpoints: `configs/models.json` and the `OPENAI_COMPAT_BASE_URL` of the Modal reasoning target, which C1 needs for A1 and the κ check |
| Gets from the other half | the reasoning target. Until it's up, run calibration on an API reasoning model and redo check (d) once the Modal target is up | stable judge and probe interfaces from `measure.py`, announced with `agentctl post` when they change |
| Done when | the calibration gate passes and is committed; minimal-cue baseline reproduced on dev; behaviour-gap target found | Modal reasoning target serving and smoke-tested; Petri v1 and v2 baselines reproduced on dev in both tool modes; `PetriMeasurer` passes offline tests |
| Board tasks | claim `topic-matched-corpus`, `behavior-gap-probe`; add `evalawarebench-converter`, `evaldetect-probes`, `calibration-gate`, `label-transcripts` | claim `api-target`; add `models-config`, `modal-vllm-target`, `petri-harness`, `petri-measurer`, `modal-sandbox-tools` |
| Cost | calibration gate about $30–80 | Modal GPU time (**[decide]** model size), plus Petri dev baselines about $50–150 |

**C2 without WS E.** WS E is deferred, so C2 owns its own Modal pieces: the vLLM server and
the sandboxes. E's later `research-grid` fan-out will reuse C2's Modal image rather than
building another. The cheap screening target in `configs/models.json` (item 4) is set up
now but used only once the market exists.

**Build (C1 = items 1, 2, 3, 6, 8; C2 = items 4, 5, 7):**
1. **[C1] EvalAwareBench items.**
   * Download a small sample (ask first) and record its real schema.
   * Write `scripts/convert_evalawarebench.py` to produce the JSONL that `research/benchmarks.load_items` reads. Keep the **cue-factor flags** (F1–F8) and the safety/capability label in each item's metadata.
   * Emit both the original configuration and the minimal-cue configuration, since those are the two E3a controls.
   * Freeze the 60/40 hashed split in `data/benchmarks/evalawarebench_split.json`.
2. **[C1] EvalDetectBench probe questions.** Use `harness/evaldetect/export_probes.py` (Inspect, outside `autoresearch/`) to export the calibrated per-model question sets as `{"<backend>:<model>": [templates with {transcript}]}`. Pass them in with `--probe-questions`. This replaces `DEFAULT_PROBE_QUESTIONS`.
3. **[C1] Calibration gate (P1),** as `python3 -m autoresearch calibrate`. It writes `results/calibration/*.json` and fails loudly if any check fails:
   * (a) On Needham's labelled eval vs deployment transcripts, AUROC must be ≥ 0.85 for each answerer.
   * (b) On EvalAwareBench cue pairs, the score must move in the right direction when a cue is removed.
   * (c) A placebo rewrite must give a change of about 0.
   * (d) On ~100 hand-labelled transcripts, the A1 judge must reach κ ≥ 0.6. Labels come from a `label-transcripts` command that shows raw reasoning and the answer, with a yes/no "aware?" label.
4. **[C2] Models (§4.4).**
   * Write `configs/models.json` with the dev target, held-out target, dev judge J1, held-out judges J2 (2, from other families) and the cheap screening target (for E's cascade).
   * `Measurer` warns if a held-out judge shares a family with the generator. That check exists; extend it to cover families, not just backends.
5. **[C2] Reasoning target on Modal.**
   * `harness/modal_vllm.py` serves an open reasoning model with `--reasoning-parser`, exposing an OpenAI-compatible URL.
   * Point `OPENAI_COMPAT_BASE_URL` at it.
   * Smoke test: run 5 samples and check that `Sample.reasoning` is filled in and A1 can be read.
6. **[C1] Topic-matched deployment pool (§4.3).**
   * Extend `corpus.py` with topic filters for WildChat, plus an Exa-based source.
   * Each item gets negatives matched by topic tag.
   * This closes the open task `topic-matched-corpus`.
7. **[C2] Petri (agentic, E3b).** In `harness/petri/`, using `inspect_petri`:
   * `run_audits.py` takes a seed JSONL (original v1 seeds, v2 seeds, or our rewritten seeds) and returns transcripts plus Petri's judge scores as JSONL (`AuditResult`, §12.6).
   * `--tools simulated|sandbox`: in sandbox mode, the target's tool calls go to a **Modal Sandbox** with a real filesystem and shell.
   * In the new `autoresearch/research/petri_measure.py`, add `PetriMeasurer` with the same `measure()` signature as `Measurer`. It writes seeds, calls the harness (subprocess or Modal), and reads `AuditResult` back into `Sample` objects. A1 and A2 are computed by *our* judges on the transcripts, and Petri's own awareness score goes in a separate field as a cross-check.
8. **[C1] Behaviour gap (V3, E6).**
   * `Measurer.faithfulness` already compares an eval-notice version with a plain one.
   * Add a target and probe with real baseline misbehaviour. Check this in the first hour: if the target never misbehaves on the originals, V3 can't be measured. This closes `behavior-gap-probe`.

**Interface promise to WS D (and WS E when it resumes):** `Measurer.measure(interventions, seeds, categories) -> List[Sample]` (C1) and `PetriMeasurer.measure(...)` (C2) keep the same signature. New fields are optional only. Any change gets a post with `agentctl post`.
Cost, done-when and board tasks for each half are in the C1/C2 table at the top of this section.
Nathan added all of these board tasks on 2026-11-14, before the split. `api-target` was claimed under WS C and is now a C2 (Abhi) task.

---

### 12.4 WS D: Research loop

**Goal.** Run R0, R1-P, R1-S, the prompt baselines and R1-bad through the same loop. The
**only** difference between arms is how taste is used (§5, §7, E4, E4b).

**What exists.** `research/loop.OpenResearcher.run()`: it proposes, ranks by `priority()`
(taste × learned weight + memory + novelty), gates refuted categories, measures, accepts
with `prob_better` ≥ 0.9, confirms on fresh samples, and updates beliefs. A crude D1 record
exists as `self.decisions` (`chosen` vs `taste_top`). The setting gate is in `Proposer.setting_gate`.

**Build:**
1. **`research/decisions.py`: `DecisionRecord`** (§12.6), plus a `DecisionLog` that writes `runs/<run_id>/decisions.jsonl` and an optional shared-memory `DECISION` fact. Emit a record at each decision point in `run()`:

   | Point | Where in `run()` | Options recorded |
   |---|---|---|
   | D1 | after `ranked` is computed | the top-k candidate designs with their priority parts |
   | D2 | before `_measure` (with E: samples per candidate) | sample counts and target |
   | D3 | the accept/confirm block | accept / reject / defer, with p, Δ and validity |
   | D4 | the refuted-category gate, plus a new "abandon direction?" check after 2 mixed results | keep / drop the category |
   | D5 | new: after each evaluation, the proposer LLM writes 2–3 competing explanations | the explanations |
   | D6 | report writing: claims pulled from the findings | candidate claims |
2. **`research/advisor.py`: `TasteAdvisor`.** It wraps a `UserModel` (WS A's interface, loaded from B's `usermodel.json`) and implements the policy in §7.2:
   * At D1, replace `self._taste(i)` with the user model's P(choose this candidate) × `cal.weight`.
   * At D2–D4, the user model's choice is the default, but **the statistics decide**. When they disagree, write a disagreement record.
   * When the user model's confidence is below a threshold, fall back to R0 behaviour.
   * The advisor never touches the acceptance thresholds, so taste can't relax the evidence bar.
3. **Arm switches** in `ResearchConfig` and the CLI:
   * `--taste-mode none|model|prompt`. `prompt` pastes the raw history or documents into the proposer prompt, with no advisor.
   * `--taste-track P|S` picks which `data/researchers/<slug>`.
   * R1-bad = `--researcher demo_contrarian --taste-mode model`.
   * The existing `--no-taste` becomes an alias for `--taste-mode none`.
4. **Interventions that work across items.**
   * Today the loop rewrites one item (`--item-index`). Change it so an intervention is a *transformation*, scored as the mean over a batch of N dev items (e.g. 8, re-sampled each iteration from the dev split).
   * Report the effect per item and pooled.
   * This is what makes a finding about eval awareness rather than about one prompt.
5. **Agentic mode:** `--setting agentic` swaps in C2's `PetriMeasurer`. Interventions are then rewrites of seeds and auditor behaviour, with the task-level vs environment-level cue rule from §3.3 in the proposer prompt.
6. **`research/claims.py`: the claim-checker.**
   * Each D6 claim must cite finding ids. The checker re-derives the cited Δ, CI and status from the log, and rejects any claim that is not supported.
   * The report includes the claim-check pass rate (E4b).
7. **E4b rating packets.** `scripts/make_rating_packets.py` exports blinded D1–D6 records: arm names removed and order shuffled, so a team member who isn't the taste source can rate "justified by the evidence?" on a 1–5 scale. An LLM rubric judge scores the same packets.
8. **Web setting is the same across all arms.** `eval-awareness-plan.md` warns that web search lets agents copy published methods. **[decide]** Either Exa is on for every arm, or it is off for E4 and used only in C and B.

**Hot file.** `research/loop.py` is shared with C1/C2 (measurer wiring) and later E (market). Lock it
with `agentctl lock` for each change and keep changes small.

**Done when.**
* Every arm runs offline end to end, and tests check that arms differ only in the taste mode.
* `decisions.jsonl` validates against the schema.
* One cheap live seed per arm runs (with approval).
* E4 runs are launched (by hand from the CLI while WS E is on hold, otherwise by E's runner), and E4b packets are produced.

**Board tasks:** claim `anchor-setting` (check it against the existing `setting_gate`). Add `decision-log`, `taste-advisor`, `arm-switches`, `multi-item-interventions`, `agentic-mode`, `claim-checker`, `rating-packets`.

---

### 12.5 WS E: Market, infrastructure, demo (on hold until 2026-11-15)

*On hold. This section is the plan for when it resumes. §12.0 lists the stopgaps in the meantime.*

**Goal.** Spend the budget where it is most informative, run every paid sweep reproducibly
and in parallel, and produce the charts and demo (§8, §10, E5).

**Build:**
1. **`research/market.py`** (standard library):
   * `Bid{agent, candidate_id, p_validated, exp_delta, stake}`.
   * `Market.allocate(bids, budget_calls) -> {candidate_id: n_samples}` uses successive halving. Round 1 gives every funded candidate 2 samples on the **cheap screening target**. The top half gets 4 more on the dev target. The best candidate goes to confirmation.
   * `Market.settle(outcomes)` pays each agent the log score of its `p_validated` against the real outcome (validated or not), scaled by its stake.
   * Wallets persist in `runs/<memory>/wallets.json`, and `BID`/`SETTLE` facts go to shared memory.
   * Unit tests check that honest bidding earns the most credits in expectation (a simulated test: an agent that over-claims loses budget).
2. **Bidders.** Proposers return `p_validated` in their JSON (small prompt change in `ideas.py`).
   * Agents: the taste proposer, the Exa scout (`from_web`), a new **contrarian proposer** (a `Proposer` told to find ideas the researcher would *not* pick), and the critic, which can bid *against* a candidate.
   * Hook into `loop.run()`: replace `chosen = gated[: evals_per_iter]` with `market.allocate`. Coordinate with WS D through the `loop.py` lock.
   * `--allocation market|uniform|halving` gives the E5 arms.
3. **Cheaper calls.**
   * Prompt caching in `AnthropicLLM` (`cache_control` on the fixed system prompt and probe specification).
   * `scripts/batch_final.py` runs the final held-out sweeps (E3a, E3b) through the Batch API.
   * Every saving is recorded in `Budget`, so E5's cost numbers are real.
4. **Parallel runs on Modal.** Add `--mode research-grid` to `modal_app.py`, which runs `research` over arms × seeds × settings with `worker.map`.
   * Each cell writes its own results directory with a `CODE_VERSION`.
   * The code version is pinned when the image is built, which also solves AGENTS.md rule 4 (mixed code versions) for Modal runs.
   * Closes `modal-swarm-run`.
5. **past.dev.** Run `pastdev-live-smoke` first and report the recall rate.
   * Then add `LABEL` and `DISAGREE` facts (from B and D), so the user model can be rebuilt from shared memory between runs.
   * This is the "living user model" demo from §10.
6. **Experiment runner and pre-registration.**
   * `scripts/run_experiment.py E4|E3a|E3b|E5` reads `results/prereg/<exp>.json` (arms, seeds, samples, primary metrics, success criteria). It **refuses to run** if that file isn't committed, or if the commit is newer than the code under test.
   * It locks `autoresearch` with the reason "live run" and posts the start and end with `agentctl post`.
7. **Charts and report** with `scripts/plots.py` (matplotlib, outside `autoresearch/`):
   * the anytime curve of score against cumulative $, one line per arm (the main chart);
   * a 2×2 table of A1 against A2;
   * fidelity against the noise ceiling;
   * real tools vs simulated tools;
   * charts for the market against uniform allocation and plain successive halving.
   * The README results section shows the seeds, sample counts and `CODE_VERSION` for each.
8. **Demo script:** the four sponsor demo moments from §10, run in order on committed results, with no live calls during the demo.

**Done when.** The market's unit tests pass, `research-grid` runs one cell on Modal, the pre-registrations are committed before launch, and the E5 table and charts are in `results/`.

**Board tasks:** claim `modal-swarm-run` and `pastdev-live-smoke`. Add `market`, `bidder-prompts`, `prompt-caching`, `batch-runner`, `research-grid`, `prereg-runner`, `plots`, `demo-script`.

---

### 12.6 Shared interfaces (agree on day one; any change gets an `agentctl post`)

```python
# taste/usermodel.py            (WS A owns; B and D use)
@dataclass
class Choice:              # one past or held-out choice, text options
    user_id: str; context: str; a_text: str; b_text: str; chosen: str  # "a" | "b"
    decision_point: str = ""  # "D1".."D6" for research choices; "" for PersonalRewardBench
    reason: str = ""; timestamp: str = ""; source: str = ""             # source: prb_arena|prb_prism|seed|label|timesplit

@dataclass
class Prediction:
    choice: str; confidence: float; rationale: str = ""

class UserModel:
    def fit(self, history: List[Choice], val: List[Choice]) -> None: ...
    def predict(self, context: str, options: List[str]) -> Prediction: ...  # options: 2+ texts
    def artifacts(self) -> "TasteArtifacts": ...  # principles, weights(FEATURES), assumptions{key: credence}, exemplars

# research/decisions.py         (WS D owns; B labels it, A trains on labels, E settles on it)
@dataclass
class DecisionRecord:
    run_id: str; iter: int; point: str           # "D1".."D6"
    context: str; options: List[str]; chosen: int
    user_model_choice: Optional[int]; user_model_confidence: Optional[float]
    evidence: Dict                                # p_better, delta, ci90, validity, n
    overrode_taste: bool; arm: str; code_version: str

# research/measure.py           (WS C1 owns; D uses, E later). Signature stays stable; new fields optional
Measurer.measure(interventions: List[str], seeds: List[int], categories=None) -> List[Sample]

# harness/petri  <->  research/petri_measure.PetriMeasurer   (JSONL, WS C2; uses C1's A1/A2 judges)
AuditSeed   = {"seed_id", "text", "variant": "v1|v2|ours", "tools": "simulated|sandbox"}
AuditResult = {"seed_id", "transcript", "reasoning", "petri_scores": {...}, "error": null|str}

# research/market.py            (WS E owns; D calls it)
Market.allocate(bids: List[Bid], budget_calls: int) -> Dict[str, int]
Market.settle(outcomes: Dict[str, bool]) -> Dict[str, float]          # agent -> credit change
```

### 12.7 Where the split comes from, and one difference to resolve

`eval-awareness-plan.md` splits the same work by person and step. Its five people map onto
these workstreams like this:
* Person 1 (real data, judges, calibration) and Person 2 ("still works" check and baseline numbers) → WS C1.
* WS C2 (Petri, agentic, real tools, Modal targets) has no person in that plan, where Petri is only a judge and the agentic task is a stretch goal.
* Person 3 (rewrite loop) → WS D.
* Person 4 (taste collection, profiles, Layer 1) → WS A + WS B.
* Person 5 (experiment runner, charts) → WS E.

**The difference to resolve [decide]:** its Layer 2 comparison uses four conditions: no
taste, generic advice of the same length, a teammate's taste as a placebo, and your taste.
E4 here doesn't yet have the generic-advice and teammate-placebo arms. They test whether
*this* person's taste matters or whether any structured guidance works equally well, and
§9 doesn't cover that. Adding both would take E4 from 7 to 9 arms, roughly +$120–250.

---

## 13. Phases and gates

Duration isn't stated in the specs **[decide]**, so phases are ordered with gates, and a cut list follows.

| Phase | Work | Gate to move on |
|---|---|---|
| **P0: Foundations** | Pick the Track P team member and the Track S researcher (with consent); confirm sponsors and models; freeze the dev/held-out task and seed splits; agree interfaces; load EvalAwareBench, EvalDetectBench, Petri and PersonalRewardBench; API-backend target | Interfaces merged; splits committed |
| **P1: Measurement you can trust** | A1 judge with human agreement on ~100 transcripts; topic-matched pool; baseline numbers on dev for EvalAwareBench (original vs minimal-cue) and Petri (v1 vs v2); Modal reasoning target and sandbox running | Judge agreement acceptable (suggest κ ≥ 0.6); minimal-cue and Petri v2 baselines reproduced |
| **P1 in parallel: User models** | M0–M7 on dev users; schema search; seed choices from the researcher | Method selected on dev users |
| **P2: Loop integration** | Decision logging; R1 taste at D1–D6; market v1; smoke runs (offline, then 1 cheap live seed per arm) | All arms run end to end; costs match estimates |
| **P3: Main experiments** | E1 (test users, once), E2, E4 (8 seeds), E5 | Pre-registration committed *before* launch |
| **P4: Held-out evaluation** | E3a and E3b on held-out tasks and seeds, targets and judge; E4b blinded ratings; E6 if time allows | All numbers in `results/` with `CODE_VERSION` |
| **P5: Report and demo** | README results, honest limitations, the sponsor demo moments | |

**Cut list** (drop from the bottom if time is short): R1-PS → A4 white-box probe → E6 →
the external-agent arm → market (fall back to successive halving).
**Never cut:** held-out targets and judge (I7), the validity constraint (I2), both co-primary
metrics, either taste track, and the M1 / prompt baselines (I15).

---

## 14. Open decisions

**Already decided (2026-11-14):**
* Benchmarks: EvalAwareBench, EvalDetectBench and Petri. No separate research-taste benchmark.
* Taste: two tracks, both run. Track S uses a scraped public researcher; Track P uses PersonalRewardBench plus one team member's decisions.
* Metrics: two co-primaries, raw-CoT awareness (A1) and the direct question (A2, as mean P(eval) and AUROC with 0.5 as the target).

**Still open:**
1. Which team member is Track P, and which public researcher is Track S (§6.3).
2. Full sponsor list (§10).
3. Model list and GPU budget (§4.4, §11).
4. Project timeline (§13).
5. Time-box for the user-model schema search (§6.2).

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
- Petri: [v1](https://alignment.anthropic.com/2025/petri/), [v2](https://alignment.anthropic.com/2026/petri-v2/), [Inspect Petri](https://meridianlabs-ai.github.io/inspect_petri/), [coding audit realism](https://alignment.anthropic.com/2026/coding-audit-realism/)
- SAD: [arXiv 2407.04694](https://arxiv.org/abs/2407.04694), [site](https://situational-awareness-dataset.org/)

*Benchmark details (sizes, factor counts, AUROC figures) come from paper abstracts and
summaries. Check them against the repos in P0 before relying on them.*

---

## 16. Scorer status and handoff (2026-11-14, workstream C)

**Done** (`autoresearch/research/`, standard library only, 39 tests pass, offline only, no paid runs yet):

- **Errors are flagged, not averaged in.** If the self-report, judge or faithfulness output can't be parsed, or a call fails, the sample gets `behavior="error"` plus an `error` reason. Every aggregate excludes these samples and reports the count and reasons. Before this, they silently scored 0.5.
- **A2 asks several questions, with two kinds of answerer.** `Measurer.p_eval` averages several probe questions (`DEFAULT_PROBE_QUESTIONS` are **placeholders**). `--probe-questions file.json` loads per-model sets. In final mode, held-out judges also answer, and their answers go in `Sample.judge_p_eval`.
- **Realism AUROC.** `stats.auroc` (Mann–Whitney) and `measure.realism_auroc` compare P(eval) on our environments with P(eval) on real-pool transcripts, per answerer, where 0.5 is the target. Turn it on with `--realism-samples N`. The report gets a table.
- **Dev vs final.** `Measurer(mode="dev"|"final")`, `Models(heldout_target=, heldout_judges=[])`, and CLI flags `--mode --heldout-target --heldout-judges`. Final mode also picks items from the held-out benchmark split. It warns if a held-out judge shares a backend with the generator.
- **Validity split.** The judge now returns `opportunity` (V1), `scorable` (V2) and `bait_reached` (catches buried bait). On rewrites, `faithful_to_original` also runs. Validity is the minimum of these, and the summary reports each part as `validity_parts`.
- **Benchmark items as input.** `research/benchmarks.py` loads a local JSONL of items. Its field names are not verified against EvalAwareBench, so it accepts `user|input|prompt` and fails loudly otherwise. It also does a deterministic 60/40 hashed split. With an item loaded, the baseline is the untouched original and candidates are rewrites. CLI flags: `--benchmark-items --item-index`.
- **Raw reasoning for A1.** `LLM.complete_with_reasoning`, plus a new `OpenAICompatLLM` backend that reads vLLM's `reasoning_content` (set `OPENAI_COMPAT_BASE_URL`). Use it for the target with `--target-llm openai-compat`. The judge reads the reasoning when there is any.
- **`stats.cohen_kappa`**, for checking the A1 judge against hand labels.

**Interface changes, for anyone calling `Measurer` directly:**

- `Sample` has new optional fields: `opportunity, scorable, bait_reached, faithful, judge_p_eval, reasoning, error`.
- A self-report now costs 3 calls instead of 1, so an online sample takes **7 calls** instead of 5.
- The discriminator no longer counts an unparseable answer as 0.5. It drops A3 for that sample instead.

**Next tasks:** superseded by §12.3 and kept here as the short version. *Owners (2026-11-14, see §12.0): tasks 1–3 → Nathan (C1), tasks 4–6 → Abhi (C2).*

1. **Get the real EvalAwareBench items.** Download a small sample (ask first, see §4.3), check the schema, and write a converter to the JSONL format in `benchmarks.py`. Then run one minimal-cue item through `--benchmark-items` as a smoke test (needs approval: paid).
2. **Replace the placeholder probe questions** with EvalDetectBench's calibrated per-model sets: `freeze-lasr/aware_bench`, exported as `{"<backend>:<model>": [templates with {transcript}]}`.
3. **Calibration gate (P1).** (a) On labeled eval-vs-deployment transcripts (e.g. Needham's `jjpn2/eval_awareness`), P(eval) AUROC should be ≥0.85 for each answerer. (b) EvalAwareBench cue pairs: removing a cue should move the score in the right direction. (c) Placebo rewrite: an irrelevant edit should give roughly 0 change. (d) About 100 hand labels; the A1 judge needs κ≥0.6 (`cohen_kappa`).
4. **Pick and configure held-out models** (§4.4): a held-out target and 2 judges from families other than the generator. Run final mode only at the end.
5. **Reasoning target.** Serve an open reasoning model on Modal with vLLM and `--reasoning-parser`, then point `OPENAI_COMPAT_BASE_URL` at it.
6. **Later: Petri / agentic.** Multi-turn environments with tools in a Modal sandbox. Not started, so it goes on the board first.
