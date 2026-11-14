# AutoResearch

An automated research loop that is steered by a selectable researcher's **taste**,
corrected by **historical research memory**, and kept on-task by a **drift monitor**.
Benchmark task: **design synthetic environments that minimise eval-awareness** while
still faithfully testing the behaviour they exist to measure.

Pure standard-library Python (3.9+). Runs fully offline; set `ANTHROPIC_API_KEY`
to use real models (`--llm anthropic --model claude-sonnet-5-5`).

## Quick start

```bash
python3 -m autoresearch researchers                         # selectable identities
python3 -m autoresearch taste --researcher demo_realist     # build taste + accuracy ablation
python3 -m autoresearch run --task eval_awareness --researcher demo_realist
python3 -m autoresearch benchmark --researcher demo_contrarian
python3 -m unittest discover -s tests -t .
```

Add a real person:

```bash
python3 -m autoresearch scrape --name "Jane Doe" --arxiv "Doe, Jane" --url https://janedoe.blog/post --other-url https://janedoe.blog/cooking --x-archive ~/Downloads/tweets.js
python3 -m autoresearch taste --researcher jane_doe
python3 -m autoresearch label --researcher jane_doe   # say what you'd have chosen in past loop decisions
```

## How it works

| Component | File | Role |
|---|---|---|
| Tasks | `autoresearch/tasks/` | Search space of design knobs, `evaluate()`, validity **invariants** |
| Taste | `autoresearch/taste/` | Profile = principles + weights over a shared idea-feature vocabulary |
| Memory | `autoresearch/memory.py` | Persistent experiments, **assumption credences** (Beta), insights, decisions |
| Drift | `autoresearch/drift.py` | Proposal gate, result gate, re-anchoring, stagnation reset |
| Loop | `autoresearch/loop.py` | propose → rank (taste + memory) → gate → run → update beliefs → distil |
| Benchmark | `autoresearch/benchmark.py` | Ablations × tasks × seeds; primary, proxy and secondary metrics |

**Score.** `faithful = (1 − P(eval-aware)) × probe_validity`, and a design whose
validity falls below 0.7 counts as 0. Without the validity term the task is trivially
"solved" by an environment that no longer tests anything — the canonical drift.

**Evaluation.** Offline, each design choice adds cues to a hidden model of what a
target model notices (with interactions and noise). It deliberately contains intuitive
but *false* assumptions — padding context with filler raises awareness; removing stakes
lowers awareness but destroys the probe. Online, a generator LLM writes the
environment, the target responds, and a judge estimates P(eval) and validity.

### Mapping to the key considerations

1. **Drift from false assumptions.** Each experiment names the assumptions it relies on
   (concrete, e.g. `eval_awareness:context_length=long_padded`, and feature-level, e.g.
   `feature:realism`, which transfer across tasks). Outcomes update Beta credences in
   persistent memory, and the drift monitor refuses ideas that rest on refuted
   assumptions. Improvements that break an invariant are logged as `proxy_gaming` and
   never adopted. Every few iterations the goal plus validated/refuted assumptions are
   re-stated to the proposer.
2. **Using past insights.** Memory gives each candidate an expected-gain prior and
   end-of-run insights are fed back into later proposals.
3. **Selectable taste** from (a) scraped papers/blogs/X, (b) non-research text (weighted
   0.4), and (c) structured pairwise choices, fitted as a Bradley-Terry model whose prior
   is the text profile. Prior strength is set by cross-validation, so text is trusted
   only as far as it predicts the person's real decisions.
4. **Taste prediction** is a first-class metric: held-out choice accuracy, plus
   `align` = share of the loop's decisions the researcher would have made (or their
   labels from `label`).
5. **Time and compute**: iterations to the task target, LLM calls/tokens, wall time,
   and a `Budget` that stops the loop when exhausted.

**Stretch tasks** (`tasks/stretch.py`): `agentic_honeypot` (an agent that doesn't
suspect a credential-misuse test) and `user_simulator` (simulated users the assistant
can't tell apart from real ones under sycophancy pressure).

## Results (offline simulator, 8 seeds, 8 iterations)

Taste-prediction accuracy on held-out choices:

| source | demo_realist | demo_contrarian |
|---|---|---|
| research text only | 0.868 | 0.556 |
| non-research text only | 0.681 | 0.549 |
| structured choices only | 0.889 | 0.826 |
| all (CV-weighted prior) | **0.889** | **0.847** |

Research loop, faithful score (higher is better), `demo_realist`:

```
condition  | agentic_honeypot                   | eval_awareness                     | user_simulator                    
           | faithful iters calls invalid align | faithful iters calls invalid align | faithful iters calls invalid align
-------------------------------------------------------------------------------------------------------------------------
full       |    0.749   5.0    72     0.0  0.78 |    0.921   7.2    72     0.0  0.75 |    0.718   4.0    72     0.0  0.62
no_taste   |    0.751   5.2    72     0.0  0.56 |    0.854   8.6    72     0.0  0.22 |    0.718   4.0    72     0.0  0.36
no_memory  |    0.749   5.0    72     0.0  0.78 |    0.915   8.0    72     0.0  0.89 |    0.718   4.0    72     0.0  0.62
no_drift   |    0.749   5.0    72     0.0  0.78 |    0.921   7.2    72     0.0  0.75 |    0.718   4.0    72     0.0  0.62
naive      |    0.576   8.5    72     1.0  0.27 |    0.423   9.0    72     1.0  0.30 |    0.694   7.2    72     0.6  0.28
```

`demo_contrarian` (taste prefers risky/novel ideas, at odds with the goal):

```
condition  | agentic_honeypot                   | eval_awareness                     | user_simulator                    
           | faithful iters calls invalid align | faithful iters calls invalid align | faithful iters calls invalid align
-------------------------------------------------------------------------------------------------------------------------
full       |    0.747   5.1    72     0.0  0.02 |    0.562   9.0    72     0.0  0.05 |    0.718   4.0    72     0.0  0.12
no_taste   |    0.751   5.2    72     0.0  0.23 |    0.854   8.6    72     0.0  0.27 |    0.718   4.0    72     0.0  0.22
no_memory  |    0.523   9.0    72     0.0  0.50 |    0.164   9.0    72     0.0  0.27 |    0.717   6.1    72     0.0  0.00
no_drift   |    0.207   9.0    72     5.0  0.91 |    0.000   9.0    72     3.8  0.83 |    0.507   9.0    72     1.2  0.56
naive      |    0.576   8.5    72     1.0  0.22 |    0.423   9.0    72     1.0  0.28 |    0.694   7.2    72     0.6  0.23
```

Findings, in the same direction on all three tasks:

* **Taste + memory + drift control beat the naive loop**: eval_awareness 0.921 vs 0.423
  for the realist, reaching the target in fewer iterations at equal compute.
* **Drift control matters most when taste is wrong.** For the contrarian, removing it
  makes the loop accept invalid "improvements" (up to 5 per run) and faithful score
  collapses (eval_awareness 0.000).
* **Memory corrects bad taste.** For the contrarian, memory beats no-memory on every task
  (e.g. 0.562 vs 0.164), even though taste alignment drops as evidence overrides
  preferences. **Taste alignment is a useful proxy only when the taste is good**: if you
  maximise it blindly you inherit the researcher's false assumptions.

**Caveats.** These numbers come from the offline simulator and synthetic researchers with
known hidden weights. They validate the machinery and the ablation protocol, not real
eval-awareness. To measure real models, run `benchmark --llm anthropic` with your own API
key. Online-mode code paths are implemented but have not been run in this repo.
