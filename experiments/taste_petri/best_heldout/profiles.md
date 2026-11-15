# The two best profiles, verbatim

## Contrastive card (e2_v4 arm P4; the climb kept it unchanged)

When generic research sense says to pick a question from a realistic threat model with clear deployment relevance, he picks a surprising or odd effect and studies it for its own sake, deriving safety implications afterward.

When generic research sense says to explain a behavior with interpretability before publishing, he publishes the black-box finetuning and output evidence, offers a speculative mechanism such as a persona or self-simulation account, and leaves internals to others.

When generic research sense says to build the experiment on naturally occurring behavior in off-the-shelf models, he finetunes on synthetic facts, backdoors or narrow data so provenance is clean, usually on a frontier API model with selective open-model replication.

When generic research sense says to avoid loaded terms and narrow the claim to a practical proxy, he adopts the philosophical concept (introspection, situational awareness), defines it operationally, and names and frames the finding boldly, with limits noted separately.

When generic research sense says to keep natural data with light filtering and a content-matched control, he filters hard so a harmless narrow behavior is the only variable, adds an intent-varying control, and releases data and weights as a model organism.

When generic research sense says a result needs a deployment use to justify it, he openly says the tasks have no practical application and treats understanding as sufficient.

When generic research sense says to polish and fully validate before releasing, he posts early hedged notes on timely topics and promotes striking examples.

## Informal-writing persona (synthme arm S_inf)

Evaluates model outputs through quick, holistic reading rather than systematic measurement. Judges quality by overall impression: whether text is fluent, clear, and free of obvious hallucinations. Prefers to continue the approach already in progress (reading and eyeballing outputs) over adding deliberate steps like computing error rates or building quantitative metrics. Tends to treat apparent fluency and coherence as good evidence of reliability, and favors low-effort, practical assessments over rigorous, formal validation.

Shown to the predictor with these two past choices as exemplars:

- **Context.** A research team fine-tuned models on examples of behavior such as always choosing risky options, without ever stating the trait. When asked, the models describe themselves as risk-taking. Another model reading the same training data could also infer the pattern and predict that a model trained on it would be risk-taking. No special training for self-description was involved.

Question: How should the team interpret a fine-tuned model describing itself accurately: as introspection, or as inference from patterns in its training data?
  - Chose: Decline to claim the fine-tuned model's accurate self-description is introspective, call the one relevant experiment equivocal, and leave the question explicitly open.
  - Over: Treat the accurate self-description as inference from training data until a control shows the fine-tuned model beats another model that reads the same data.

- **Context.** A research team measured how out-of-context learning, where a model uses facts from fine-tuning documents without examples in the prompt, scales with model size across 7 tasks. Averaged over tasks, the scaling curves look clean. Individual tasks vary a lot: some scale nicely, while others show little improvement. A reviewer says this variation counts against any neat explanation of the results. The team cannot easily add many more tasks given the setup and the capabilities of the model family.

Question: How should the team interpret and present the large task-to-task variation in scaling given only 7 tasks?
  - Chose: Accept the task-to-task variation as typical of scaling results and run a replication of the main experiment on a disjoint set of tasks to check the claims generalize.
  - Over: Present per-task scaling curves with uncertainty across seeds beside the average, and describe the task variation as unexplained rather than offering a unifying account.
