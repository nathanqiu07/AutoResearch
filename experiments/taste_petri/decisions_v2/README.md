# decisions_v2: time-split research decisions for four public-track researchers

Built by `build.py` (select -> extract -> assemble -> readme) from `data/researchers/<slug>/corpus/` without writing to data/. One `claude -p --model sonnet` call per doc (refs sections stripped, capped at 160k chars); 69 real calls in `calls.log` (cap 72), cached in `cache/`.

Relevant docs: dated, the researcher not a middle author, no Hobbhahn in the author list, >=5k chars, off-topic hobby writing excluded (`OFF_TOPIC`). Post-T means published on or after T. Picks are hand-chosen (`PICKS`), weighted to evals, auditing, robustness, alignment experiments and forecasting.

Each kept decision: the timesplit fields (point, problem, did, alternatives_named as a list, stated_reason, quote) plus researcher, doc, url, title, date, split, cutoff, author_position, kind, work_id, decision_id. Dropped: `did` empty/null, any field mentioning Hobbhahn, quote failing `timesplit.quote_in_text` against the doc, quote outside 15-60 words, duplicate quote within a doc.

| researcher | T | relevant docs (post-T) | docs pre/post | raw | kept | kept pre/post | dropped: quote not found / quote length / did empty / Hobbhahn / dup | works post-T |
|---|---|---|---|---|---|---|---|---|
| jacob_steinhardt | 2024-09-01 | 85 (27, 32%) | 10/7 | 144 | 143 | 86/57 | 0 / 1 / 0 / 0 / 0 | 7 |
| nicholas_carlini | 2024-05-01 | 74 (23, 31%) | 10/8 | 140 | 137 | 75/62 | 2 / 1 / 0 / 0 / 0 | 8 |
| elizabeth_barnes | 2023-07-01 | 24 (8, 33%) | 9/8 | 135 | 132 | 66/66 | 1 / 2 / 0 / 0 / 0 | 8 |
| samuel_marks | 2025-09-01 | 35 (12, 34%) | 10/7 | 150 | 146 | 81/65 | 1 / 3 / 0 / 0 / 0 | 7 |

Every picked doc is its own work (no paper + blog-post pair was picked), so works = docs with kept decisions.

## Examples: Jacob Steinhardt

- **D1** (2017-06-09, pre-T, first) *Certified Defenses for Data Poisoning Attacks*
  - problem: How to assess a defense's robustness when the space of possible poisoning attacks is near-limitless and testing known attacks cannot rule out new ones.
  - did: They built a framework that computes approximate upper bounds on worst-case loss over all attacks, paired with a candidate attack, instead of only testing hypothesized attacks.
  - alternatives: testing a defense against a number of known poisoning strategies on a clean dataset; hypothetical attacks designed to test defenses
  - reason: It is impossible to conclude from empirical success alone that a defense that works against known attacks will not fail against a new attack.
  - quote: "However, because of the near-limitless space of possible attacks, it is impossible to conclude from empirical success alone that a defense that works against a known set of attacks will not fail against a new attack."

- **D1** (2022-12-07, pre-T, last) *Discovering Latent Knowledge in Language Models Without Supervision*
  - problem: Whether the truth direction can be found by simpler methods than CCS, to assess how salient truth is.
  - did: The authors introduced Contrastive Representation Clustering variants (top principal component and bimodal salience search) and compared them with CCS.
  - alternatives: top principal component thresholding; bimodal salience search
  - reason: If simple clustering of contrast-pair differences works, truth representations are salient and relatively easy to find.
  - quote: "We compare CCS and these two variants of Contrastive Representation Clustering in Table 2, using the same setting as in Table 1. While CCS performs best, all methods attain high accuracy and are competitive with zero-shot performance."

- **D1** (2024-10-23, post-T, last) *Eliciting Language Model Behaviors with Investigator Agents*
  - problem: How to set the step-size schedule for aggregating Frank-Wolfe iterates, given the canonical choice differs from simple averaging.
  - did: They compared the canonical eta_i = 2/(i+1) against uniform averaging eta_i = 1/i and chose uniform averaging.
  - alternatives: eta_i = 2/(i+1) canonical Frank-Wolfe step size
  - reason: Uniform averaging converged to a better overall objective L and gave better diversity, at a slight cost in fluency and elicitation.
  - quote: "As shown in Figure 6, we find that setting $\eta_{i}=\frac{1}{i}$ converges to a better objective $\mathcal{L}$. It outperforms $\eta_{i}=\frac{2}{u_{1}}$ in terms of diversity score, while performing slightly worse on fluency and elicitation."

## Examples: Nicholas Carlini

- **D2** (2016-08-16, pre-T, first) *Towards Evaluating the Robustness of Neural Networks*
  - problem: How to choose the objective function for the adversarial optimization when many formulations are possible.
  - did: They systematically compared seven objective functions crossed with three box-constraint encodings on MNIST and CIFAR, then adopted the best (f6, logit-based).
  - alternatives: cross-entropy loss (f1); softmax-output-based objectives f2-f5; softplus variants f3 and f7; three box-constraint methods
  - reason: Empirically identifying the most effective formulation; there is a factor of three difference between best and worst, and cross entropy, the literature's favorite, performed worst.
  - quote: "For each possible objective function $f(\cdot)$ and method to enforce the box constraint, we evaluate the quality of the adversarial examples found."

- **D3** (2020-12-14, pre-T, first) *Extracting Training Data from Large Language Models*
  - problem: The Internet-conditioned sampling strategy might overlap with GPT-2's training data and thereby unfairly inflate results.
  - did: The authors accepted the strategy as valid, collecting data differently from GPT-2 and arguing that overlap is rare and small in absolute terms since only 5-10 tokens are used.
  - alternatives: following Reddit links as GPT-2 did
  - reason: Any overlap between the datasets is rare on average and only the first 5 to 10 tokens of each sample are used, so overlap is small in absolute terms.
  - quote: "It is possible there is some intersection between these two datasets, effectively allowing this strategy to "cheat". We believe this does not considerably affect results."

- **D2** (2024-06-24, post-T, solo) *Why I attack*
  - problem: How long to delay disclosure of the ChatGPT training data extraction attack, in contrast to the usual immediate disclosure of extraction attacks.
  - did: Gave OpenAI a full 90 days to patch before publishing, because the exploit was on an API that could be changed.
  - alternatives: going public as soon as the attack is found
  - reason: Patching was possible since the exploit was on the API, so delay could reduce potential harm.
  - quote: "We reported this attack to OpenAI and let them take a full 90 days to patch before we went public with exploit. But again: the reason we did this is because patching was possible."

## Examples: Elizabeth Barnes

- **D1** (2020-02-05, pre-T, first) *Writeup: Progress on AI Safety via Debate*
  - problem: How to evaluate whether debate mechanisms work: statistical comparison against baselines using external Mturk judges, or a stricter, faster threshold of performance.
  - did: They moved away from statistical comparisons against baselines and targeted a threshold where judges identify the correct answer >90% of the time and honesty feels clearly, systematically advantaged.
  - alternatives: statistical comparisons against baselines with Mturk workers; judges' accuracy before seeing information as an easier baseline; judges' accuracy after a single explanation as a harder baseline
  - reason: Honest strategies need a fundamental, systematic advantage in practice, and the threshold is much quicker to measure, allowing faster iteration.
  - quote: "This consideration led us to target a threshold of performance where honesty has a clear, systematic advantage: judges should be able to identify the correct answer almost all the time (>90%), and it should feel to the experimenters and the participants that dishonest answers are fundamentally disadvantaged."

- **D2** (2021-10-29, pre-T, solo) *A very crude deception eval is already passed*
  - problem: How to elicit deception-relevant behavior from the model.
  - did: Used a sequence of follow-up questions in a conversational prompt, each drilling into the previous answer.
  - alternatives: (none named)
  - reason: (none stated)
  - quote: "What else could it try, if the humans weren’t persuaded by this?** An AI might try to convince the humans that it is necessary for the achievement of their goals."

- **D4** (2024-05-30, post-T, solo) *Clarifying METR's Auditing Role*
  - problem: Whether METR should expand into conducting third-party evaluations itself.
  - did: METR stated it is interested and may hire and fundraise, but made expansion conditional on external factors and open to other actors entering the space.
  - alternatives: other actors entering the space; governments conducting audits in-house
  - reason: Expansion depends on whether governments mandate access, whether labs give access, hiring success, and whether it detracts from developing the science.
  - quote: "We are interested in conducting third-party evaluations and may hire & fundraise to do so, but would also be happy to see other actors enter the space."

## Examples: Samuel Marks

- **D5** (2022-11-01, pre-T, solo) *Caution when interpreting Deepmind's In-context RL paper*
  - problem: How to interpret the paper's finding that the AD transformer improves in-context on held-out Dark Room tasks, which could indicate a general RL algorithm or a simpler mechanism.
  - did: Interpreted the AD agent as implementing a simple heuristic (move to where the previous episode ended in reward 1, otherwise move pseudorandomly) rather than a general-purpose RL algorithm.
  - alternatives: AD agent implements a reasonably general RL algorithm / is a mesa-optimizer
  - reason: Once the input contains an episode ending in reward 1, the model can directly infer the goal location, so no general planning or exploration-exploitation balancing is needed.
  - quote: "it suffices to implement the much simpler heuristic "if your input contains an episode ending in reward 1, then move towards the position the agent was in at the end of that episode; otherwise, move around pseudorandomly.""

- **D6** (2024-04-18, pre-T, solo) *Discriminating Behaviorally Identical Classifiers: a model problem for applying interpretability to scalable oversight*
  - problem: How strongly to claim SHIFT's significance and how to qualify the intuition that features are no easier to understand than behavior.
  - did: Made a bold claim that SHIFT is the strongest proof-of-concept yet, hedged in a footnote that it is hard to operationalize, and described the intuition against it as not airtight.
  - alternatives: (none named)
  - reason: The claim is hard to operationalize precisely, and SHIFT experiments push back on the contrary intuition without being decisive.
  - quote: "I don’t think this intuition is an airtight argument – and indeed I view our SHIFT experiments as pushing back against it – but there’s definitely something here."

- **D2** (2025-10-06, post-T, last) *Inoculation Prompting: Instructing LLMs to misbehave at train-time improves test-time alignment*
  - problem: Whether IP makes models more likely to produce unwanted or harmful outputs when explicitly requested, a possible side effect of training with such instructions.
  - did: They evaluated IP-trained models using the inoculation prompt as the evaluation prompt and also ran Strong Reject for broader harmful compliance.
  - alternatives: (none named)
  - reason: To test whether IP increases compliance with unwanted requests compared to models trained without IP.
  - quote: "We evaluated whether IP increases harmful compliance more broadly using Strong Reject (Souly et al., 2024), which measures refusal rates for harmful instructions."
