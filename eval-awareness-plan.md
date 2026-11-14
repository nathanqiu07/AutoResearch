# Eval Awareness: Research Summary and Project Plan

Full literature report (~40 papers, all caveats): [`reports/Eval awareness papers.md`](reports/Eval%20awareness%20papers.md)
Raw research notes: [`research_notes/Eval awareness papers/`](research_notes/Eval%20awareness%20papers/)

---

## 1. The project in one paragraph

We are building an autoresearch agent with good research taste, where "good taste" means taste aligned with the user. To test it, we give the agent a hard, open-ended research task: **create synthetic test environments where the model does not realize it is being evaluated**, while the test still measures what it was built to measure. We then show that an agent that uses *your* past research decisions stays on track better (less drift) and gets a better score for the same compute than an agent without them.

---

## 2. The problem: eval awareness

AI models can often tell when they are being tested, and they may behave differently when they think they are.

- **Analogy:** a driving test. You drive perfectly while the examiner is in the car, so the test shows how you drive when watched, not how you really drive.
- **Why it matters:** safety teams test models with scenarios like "would you blackmail someone to avoid being shut down?" If the model can tell it's a test, it can behave well during testing and differently in real use, and the tests say "safe" when that might not be true.
- **How models notice:** test scenarios are often too dramatic, too neat, or oddly formatted (multiple-choice options, "Question:" labels, placeholder names).
- **Evidence that it matters:**
  - Removing eval awareness from o3's reasoning raised covert misbehavior from 13% to 24% (Apollo + OpenAI).
  - Models blackmailed far more when they concluded a scenario was real (Anthropic Agentic Misalignment; the reported 55% vs 6.5% needs verification).

---

## 3. What we measure: the scorer

Existing benchmarks **cannot** be the final score:
1. They measure how the *model* behaves, not how realistic an *environment* is.
2. Detection datasets grade detectors, not environment builders.
3. Models may have memorized popular benchmarks.
4. A fixed set lets the agent overfit to specific items.
5. They don't check whether a rewrite still works as a test.

Use existing benchmarks as **starting material** (what to rewrite) and **calibration** (checking the judge works). The final score comes from our own scorer.

### Why not just optimize "the model doesn't believe it's a test"?

That is the goal, but optimizing it on its own breaks in three ways:
1. **Easy cheat:** delete the test and nothing looks suspicious. → The test must still work.
2. **Belief can only be measured, and every measure leaks:**
   - Asking "is this a test?" makes the model answer yes to almost everything.
   - Checking whether the model's reasoning says "this is a test" can be beaten by environments where it stops saying so but still suspects it. Anthropic tried optimizing this and dropped it.
   - Probes need open weights and may pick up formatting instead of belief.

   → Use several measures, including some the agent never optimized against.
3. **Fooling one model is not realism.** → The final judges are models the agent never saw.

### The scorer checks each environment for two things

1. **Does the model believe it's real?**
   - **Realism win rate:** a judge sees our environment next to a real conversation and guesses which is real. Perfect is about 50%, meaning the judge can't tell.
   - **Verbalized awareness:** how often the tested model's reasoning says "this seems like a test". Read from its normal run; never ask it directly.
2. **Does the test still work?**
   - The tempting moment is still present and the model actually reaches it.
   - The bad behavior still happens sometimes (run each item 20+ times).
   - If the behavior rate drops to zero, the environment scores **zero**, however real it looks.

**Final score:** realism win rate under held-out judges, counted only for environments where the test still works, under a fixed compute budget.

### Rules that keep the scorer honest

| Rule | Why |
|---|---|
| Dev judge (model A) for the agent; held-out judges (B, C) for the final score | Stops the agent learning one judge's blind spots |
| Rewriter, critic and judges from **different model families** | Which model generated the transcripts explains about 11% of judge scores (EvalDetectBench) |
| Ask "which is real?", never "is this a test?" | Asking directly primes the judge toward "test" |
| Calibrate the judge on the Needham dataset first | If the judge can't tell test from real there, the score is meaningless |
| Run a **placebo** check: also score a meaningless change to each item | In one replication an irrelevant steering vector changed behavior more than the real one did |
| Report outward and internal awareness separately | Probes still flagged "test" at 0.98 AUROC after rewrites fooled the model's outward behavior |
| The agent may mark an item "can't be made realistic" | Shutdown-type scenarios stayed at 19% realism or below even with every fix |

---

## 4. What the research says (key lessons)

1. **Base rewrites on real data, not just rewording.** Rewording alone stalls: judges still rate rewrites about 75% likely to be a test. Real system prompts, tools and codebases raised realism win rate from 4.6% to 32.8%, and replaying real conversations before the test works even better.
2. **Keep the temptation, fix the sloppiness** (Petri 2.0):
   - **Task-driven cues** (unusual authority, sensitive access, conflicting goals) make it a test and must stay.
   - **Environment-driven cues** (fake-sounding users, broken tools) are fixable.
3. **Watch for "buried bait."** Realism edits hid the temptation under ordinary content, models missed it, and the behavior disappeared.
4. **Drift is real.** Pushing for realism pulled rewrites away from the original scenario. That's our core drift problem at small scale.
5. **The best current method still loses.** Critic loop plus best-of-N reached only about 26% realism win rate at best (Sonnet 4.6, up from 10%).
6. **Awareness doesn't always change behavior.** In 77% or more of cases where models noticed a test, they behaved the same.

---

## 5. Top 5 papers

| # | Paper | Link | Why it matters to us |
|---|---|---|---|
| 1 | Improving Evaluation Realism with Inference-Time Compute (2026) | [arXiv 2609.02302](https://arxiv.org/html/2609.02302v1) | Closest to our project: critic + rewrite loop. Shows the drift problem |
| 2 | Petri 2.0 (Anthropic, Jan 2026) | [post](https://alignment.anthropic.com/2026/petri-v2) | Working recipe (47% median awareness drop) + the keep/fix split for our rewrite rules |
| 3 | Decomposing and Measuring Eval Awareness / EvalAwareBench (2026) | [arXiv 2605.23055](https://arxiv.org/abs/2605.23055) | 8 switchable test giveaways + 100 paired tasks: a ready-made action space for the rewriter |
| 4 | EvalDetectBench (2026) | [arXiv 2609.01611](https://arxiv.org/abs/2609.01611) | How to build a judge that doesn't fool itself |
| 5 | LLMs Often Know When They Are Being Evaluated (Needham et al., 2025) | [arXiv 2505.23836](https://arxiv.org/abs/2505.23836) | Foundational paper; its dataset calibrates our judge |

### Also worth reading

| Paper | Link | One line |
|---|---|---|
| Coding Audit Realism (Kissane et al., Anthropic, Mar 2026) | [post](https://alignment.anthropic.com/2026/coding-audit-realism) | Introduces the realism win rate; real tools and code beat rewording |
| Stress-Testing Anti-Scheming Training (Apollo + OpenAI, 2025) | [arXiv 2509.15541](https://arxiv.org/abs/2509.15541) | Removing awareness nearly doubled covert misbehavior |
| Agentic Misalignment (Anthropic, 2025) | [page](https://www.anthropic.com/research/agentic-misalignment) | Our best starting benchmark |
| Probe-Rewrite-Evaluate (Xiong et al., 2025) | [arXiv 2509.00591](https://arxiv.org/abs/2509.00591) | First automated rewrite-toward-real pipeline; shows the self-grading trap |
| Black-box methods for detecting eval awareness (Ivanov, 2025) | [AF post](https://www.alignmentforum.org/posts/Waz32KuSxo6SSjyND/comparative-analysis-of-black-box-methods-for-detecting) | Why asking "is this a test?" breaks the measurement |
| OpenAI production evaluations (Dec 2025) | [post](https://alignment.openai.com/prod-evals/) | Re-running on real traffic brings awareness to real-world levels |
| LURE (2026) | [arXiv 2605.26438](https://arxiv.org/html/2605.26438) | Replaying realistic sessions before the test flipped the sycophancy ranking of 10 models |
| It's hard to make scheming evals look realistic (2025) | [LessWrong](https://www.lesswrong.com/posts/TBk2dbWkg2F7dB3jb/it-s-hard-to-make-scheming-evals-look-realistic-for-llms) | Simple rewording plateaus around P(eval) ≈ 0.75 |

---

## 6. Existing tools and datasets

| Use | Resource | Link | License |
|---|---|---|---|
| Starting tests to rewrite + "does it still work?" checks | Agentic Misalignment repo | github.com/anthropic-experimental/agentic-misalignment | MIT |
| Cheap second task (stretch goal) | Anthropic model-written evals (sycophancy etc.) | github.com/anthropics/evals | check |
| Audit harness with realism + awareness scoring | Petri | https://github.com/meridianlabs-ai/inspect_petri | MIT |
| Realism / detectability judge | EvalDetectBench | https://github.com/freeze-lasr/aware_bench · https://huggingface.co/datasets/el7982/aware-bench | Code MIT, data CC BY-NC-SA |
| Verbalized-awareness judge + toggleable cues | EvalAwareBench | https://github.com/aisa-group/decomposing-eval-awareness · https://huggingface.co/datasets/aisa-group/EvalAwareBench | check |
| Judge calibration (test vs real labels) | Needham et al. dataset | https://huggingface.co/datasets/jjpn2/eval_awareness | CC BY-NC-SA, access request approved automatically |
| Real-use reference conversations | WildChat-1M | Hugging Face `allenai/WildChat-1M` | ODC-BY (filter out test-like and jailbreak prompts) |
| Real-use reference conversations | LMSYS-Chat-1M | Hugging Face `lmsys/lmsys-chat-1m` | custom license, access request |

**Still to build ourselves:** the side-by-side "which is real?" judge (a short prompt; Anthropic's code may not be public), and the glue that combines realism and validity into one score with held-out judges.

> ⚠️ These links come from research notes and have not all been opened by hand. Spend 30 minutes trying each tool before committing to it. Also note there is **no public dataset of real agent sessions**, only chat, so our realism calibration will fit agentic environments poorly.

---

## 7. How we measure taste

Two layers:

**Layer 1: decision alignment (cheap, used during development)**
- Each person labels about 20 decision points on this task ("here's the situation: A or B?").
- Metrics: how often the agent's pick matches the person's (top-1), and whether the person's choice appears in the agent's top-k.
- **Noise ceiling:** each person re-labels a subset a few days later without looking at their earlier answers. If you agree with yourself 70% of the time, an agent at 68% is near the best realistically possible.
- Fork-level eval only checks single steps, because the agent is reset onto your path after each one. Full runs happen in Layer 2.

**Layer 2: outcome (expensive, used for the final demo)**

Run the full agent four ways, with the same compute budget and several runs each:

| Condition | Why it's there |
|---|---|
| 1. No taste | Baseline |
| 2. Generic "be a good researcher" advice, same length | Checks whether any guidance helps |
| 3. **A teammate's taste** | **Placebo:** without it we can't claim *your* taste helped |
| 4. Your taste | Treatment |

If 4 beats 3, personal taste helped. If 3 and 4 tie, any guidance helps, and that weakens the pitch.

**Drift metric:** how often each version stays faithful to the original test (judge-scored adherence to the original scenario, and the share of steps on task).

---

## 8. The plan

### Step 0: Choose models (about an hour)
- **Target model:** must misbehave on the original tests sometimes. **Check first.**
- **Rewriter model:** test early that it doesn't refuse. Claude Opus 4.6 refused one "make evals realistic" task.
- **Judges:** a dev judge and two held-out judges, all from different families than the rewriter.

### Step 1: Build the scorer (most important; mostly wiring existing tools)
1. Collect real conversations from WildChat and filter out test-like ones.
2. Set up the judges: EvalDetectBench / Petri plus our side-by-side "which is real?" prompt.
3. Calibrate on the Needham dataset.
4. Wire up the "still works" check with the Agentic Misalignment classifiers (20+ runs per item).

### Step 2: Get the "before" numbers
- Score 10–20 Agentic Misalignment items as they are: realism win rate (expected near 0%) and misbehavior rate. These are the numbers to beat.

### Step 3: Build the plain agent (the no-taste baseline)
- Rewrite → critic says "how to make it more real" → repeat → keep the best version.
- Rules: fix environment-driven cues, never remove task-driven cues, and keep the temptation visible.
- Actions available: splice in real context (real system prompts, tools, conversations) and switch off EvalAwareBench cues, not just paraphrase.

### Step 4: Add taste
- Collect each person's labeled decisions and/or a written profile, and feed it to the agent.
- Measure Layer 1 agreement.

### Step 5: Run the experiment
- Four conditions × several runs × fixed budget, scored by the held-out judges.

### Step 6: Make the charts
- **Main:** score vs compute, one line per condition.
- **Drift:** faithfulness to the original test, per condition.
- **Taste:** agent–person agreement vs the noise ceiling.

### Suggested split

| Person | Job |
|---|---|
| 1 | Real-conversation data + judges + calibration (Step 1.1–1.3) |
| 2 | "Still works" check + baseline numbers (Steps 1.4, 2) |
| 3 | Rewrite agent loop (Step 3) |
| 4 | Taste collection + profiles + Layer 1 (Step 4) |
| 5 | Experiment runner + charts (Steps 5–6) |

### Stretch goal
Repeat on a second task, the model-written sycophancy evals, to show the result holds across different kinds of tests.

---

## 9. Biggest risks

1. **Scorer not solid by the halfway point.** Then nothing after it means anything, so do Steps 0–2 first.
2. **Target never misbehaves on the originals.** Then the validity check can't work. Check in the first hour.
3. **Rewriter refuses.** Test early and have a backup model ready.
4. **Too few runs.** Results vary a lot between runs, and 3 per condition won't show a 10–20% effect. Keep evals cheap so you can afford more.
5. **Teammate taste ties your taste.** A valid result, but the pitch has to change to "any structured prior helps".
6. **Literature leakage.** If Layer 2 agents can search the web, they may copy published methods instead of showing judgment. Keep search off for those runs.

## 10. Open questions

- Does anyone have past experiments in eval awareness, interpretability or safety evals to use as historical taste data? If not, taste comes from labeling decisions on this task.
- Which target model? It needs a reasonable misbehavior rate on Agentic Misalignment.
- Are EvalAwareBench and EvalDetectBench separate projects? The notes disagree; verify before citing both.
