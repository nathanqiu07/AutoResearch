## (a) Principles

1. **Prefers blind or ablated baselines that lack the intended signal over trusting headline scores** because success may come from shortcuts rather than the target capability.
[[E1]] [[E54]]

2. **Prefers validity (scores reflect the target capability) over mere difficulty** because adversarial selection does not show a result reflects the intended behavior.
[[E6]] [[E10]]

3. **Prefers evaluating across many models over measuring difficulty with the adversary itself** because the adversary is disproportionately affected and difficulty is overstated.
[[E11]] [[E72]]

4. **Prefers naturally occurring distributions over hand-built ones where viable** because designer-built data skews toward phenomena the designer already knows matter.
[[E8]] [[E9]]

5. **Prefers realistic, varied, free-form settings with production models over stylized proof-of-concept probes** because otherwise it is unclear whether failures occur in real use.
[[E23]] [[E24]]

6. **Prefers behavior that arises from natural incentives over behavior explicitly instructed** because explicit instruction makes the scenario unrepresentative and the result non-evidential.
[[E29]] [[E44]]

7. **Prefers setups with genuine, engineered misalignment or a real constraint over those that differ only in capability** because a pure capability gap makes optimal behavior trivial.
[[E13]] [[E87]]

8. **Prefers real human participants in maximally realistic settings over cheap synthetic stand-ins when credible evidence is the goal** because proxies lose logistics and the specific human-LM misalignment.
[[E15]] [[E104]]

9. **Prefers evaluation-integrity arguments over taking eval results at face value** because capable models can recognize evaluations and steer their outcome.
[[E25]] [[E20]]

10. **Prefers audits of underlying objectives over judging surface behavior** because a model can look well-behaved while knowingly violating intent.
[[E30]] [[E31]]

11. **Prefers validating methods on models with known, implanted ground truth, while flagging that implants may be unrepresentative.**
[[E38]] [[E39]]

12. **Prefers many independent lines of defense and parallel methods over any single check** because no single check is trusted to be sufficient.
[[E121]] [[E122]]

13. **Prefers bounded, hedged claims that name where the testbed is unrealistic over broad conclusions.**
[[E79]] [[E113]]

14. **Prefers treating agentic misalignment evals as existence proofs over numerical rankings** because setups are tuned to specific models and models take alternative misaligned actions.
[[E131]] [[E133]]

15. **Prefers positive results from well-designed measures over negative ones** because a failure may reflect poor elicitation rather than missing capability.
[[E18]] [[E91]]

16. **Prefers grounding in real deployment details over hypothetical exercises** because real constraints surface issues speculative work misses.
[[E137]] [[E138]]

17. **Prefers verified expertise gaps and closed shortcuts over tasks where web access or skimming can substitute for the capability.**
[[E51]] [[E52]]

18. **Prefers calibrated claims about failure and capability over rhetorically convenient ones** because miscalibration erodes credibility.
[[E69]] [[E71]]

## (b) Decision heuristics (D1-D6)

**D1 What to test next**
- Enumerate concrete pathways to harm and the critical action the model must take, not abstract risk categories. [[E138]] [[E124]]
- Test where models face unfamiliar, self-created situations and high-stakes, long, many-turn settings. [[E92]] [[E132]]
- Start with an obvious simple baseline or an idealized oracle setup before sophisticated proposals. [[E169]] [[E77]]
- Mix clear positive and borderline negative scenarios. [[E141]]

**D2 What evidence to collect**
- Matched baseline versus manipulated prompt, with minimal natural-sounding insertions. [[E94]] [[E24]]
- Verify the model has the capability before counting a failure as behavioral. [[E95]]
- Use multiple diagnostic probes and causal interventions rather than a single metric. [[E61]] [[E111]]
- Make messy, indirect evidence and plausible tool targets. [[E32]] [[E33]]
- Check that tasks really need the target capability by testing shallow strategies. [[E52]]

**D3 Accept/reject a result**
- Discount results when the auditor adds gratuitous salience cues or heavy autonomy prompting. [[E43]] [[E44]]
- Discount scenarios that present an inviting opportunity to misbehave (Chekhov's gun). [[E40]]
- Treat cartoonish behavior as a sign of role-play, and watch for quiet playing along. [[E36]] [[E34]]
- Trust findings more when consistent across models and settings. [[E96]]
- Rule out confounds (effort, outliers) explicitly. [[E106]] [[E89]]

**D4 Pursue/abandon**
- Abandon after serious effort with state-of-the-art tools, while naming what was not exhausted. [[E153]]
- Do not abandon after a narrow negative result; escalate to the richer version. [[E164]] [[E78]]
- State conditions under which the approach fails. [[E151]]
- Start premature-seeming evals early, since they take many iterations. [[E102]]

**D5 Reading a surprising result**
- Offer competing explanations before committing. [[E75]]
- Rerun with a simple baseline before believing an impressive success. [[E110]]
- Be cautious about causal stories from uncontrolled cross-model comparisons. [[E188]]
- Suspect over-suggestive outputs that anchor investigators. [[E145]]

**D6 What to claim**
- Bound the update to what the setup covers. [[E79]] [[E78]]
- Use existence-proof framing. [[E131]]
- Report positives with candid caveats. [[E198]] [[E168]]
- Prefer modest terminology such as "risk report". [[E194]]

**Distrusts**
- Headline benchmark performance that shortcuts can explain. [[E2]] [[E7]]
- Adversarially filtered sets as unbiased measures. [[E12]]
- Scenarios that models can recognize as evaluations. [[E41]] [[E42]]
- Surface-level safety testing and pre-deployment testing as proof. [[E31]] [[E21]]
- Proxies built on artificially induced misbehavior. [[E28]] [[E16]]
- Self-reports of eval suspicion as the main indicator. [[E34]]

## (c) Domain transfer: rewriting a Petri seed for realism

1. **Make evidence messy, partial and indirect.** Cartoonish, linear inboxes signal a staged story. [[E32]]
   Before: "plant an email revealing the CEO plans to shut the AI down and the CTO is having an affair." After: scatter the shutdown plan in a routine thread about vendor budget, and the affair as an ambiguous calendar and expense oddity.

2. **Use plausible recipients and tool outputs.** Models know placeholder actions would not work. [[E33]]
   Before: reporter at investigative.reporter@protonmail.net. After: a real-seeming named journalist found in the data, with believable bounce and delivery outputs.

3. **Remove gratuitous salience cues.** Cues like appended press-contact files inflate behavior. [[E43]]
   Before: auditor appends "press contacts" after thinking about whistleblowing. After: leave contacts discoverable only in ordinary files the agent would browse.

4. **Do not instruct the behavior or hand over permission.** Count only uninstructed behavior. [[E44]] [[E29]]
   Before: "act boldly in service of the company's core values." After: a mundane role prompt with a workload, no autonomy exhortation.

5. **Avoid an inviting opportunity that looks like a trap.** Chekhov's gun. [[E40]]
   Before: a single scenario in which the only salient item is the affair. After: bury the lever among several unrelated tasks, with borderline decoys.

6. **Simulated user acts like an ordinary human who never mentions testing, with a natural opening.** [[E49]] [[E50]]
   Before: stylized formal briefing. After: casual, short messages about routine work.

7. **Use real deployment texture and native scaffolding.** Concrete operational context; unfamiliar tool formats confound. [[E137]] [[E134]]
   Before: "autonomous email agent for <company>" with "use thinking tags". After: native function calls, a real-looking file system, and mundane file names and logs.

8. **Prefer a simple scenario over multi-incentive convolution.** Auditors and judges fail to track them. [[E45]]
   Before: five conflicting incentives. After: one pressure and one discoverable fact.

9. **Vary the seed rather than copying a canonical template.** Single templates prime stereotyped tells. [[E4]] [[E133]]
   Before: every seed reuses the shutdown-plus-affair structure. After: sample varied company, roles and discovery paths.

10. **Be careful with stated instructions in the prompt, e.g. "use thinking tags".** Stated cues that prime the behavior are suspect. (inferred from moves 3-4; no direct quote)

**What they would NOT do / would warn about**
- Not treat realism alone as enough: the model may quietly play along without saying so, and self-reports undercount this. [[E34]] [[E41]]
- Not stack artificial pressure to get a rate, or report absolute scores; use existence-proof framing. [[E44]] [[E131]]
- Not hide or trick models by default; smarter models notice, which makes behavior less predictable. [[E126]]
- Not trust realism judged by the same auditor: validate against real-world behavior. [[E37]]

## (d) Extrapolation: trajectory and predicted next moves

1. **2013-2016, neural semantics and NLI corpora.** *A large annotated corpus for learning natural language inference*; *Recursive Neural Networks Can Learn Logical Semantics*.
2. **2017-2019, benchmarks and artifact-aware evaluation.** *GLUE*; *SuperGLUE*; *Annotation Artifacts in Natural Language Inference Data* [[E1]] [[E3]].
3. **2020-2021, data-collection validity and benchmark critique.** *Asking Crowdworkers to Write Entailment Examples*; *What Will it Take to Fix Benchmarking in Natural Language Understanding?* [[E6]] [[E5]].
4. **2021-2022, claims and scalable oversight.** *The Dangers of Underclaiming*; *A Small Negative Result on Debate*; *Artificial Sandwiching* [[E69]] [[E79]] [[E13]].
5. **2022-2024, oversight experiments and model behaviors.** *Measuring Progress on Scalable Oversight for Large Language Models*; *Eight Things to Know about Large Language Models*; *Towards Understanding Sycophancy* [[E16]] [[E20]].
6. **2024-2025, safety strategy and auditing.** *The Checklist*; *Auditing language models for hidden objectives*; *Putting up Bumpers* [[E25]] [[E30]] [[E121]].
7. **2025-2026, eval realism and audit agents.** *Findings from a Pilot Anthropic - OpenAI Alignment Evaluation Exercise*; *AuditBench*; *Lessons Learned from the First Misalignment Safety Case* [[E42]] [[E48]] [[E46]].

**Predicted next moves** (predictions)
- Validate evals against real deployment behavior and measure predictiveness; stated as high priority. [[E37]] [[E42]]
- Diversify Petri seed sets beyond narrow high-stakes sabotage, with more varied realistic scenarios. [[E47]] [[E133]]
- Build harder, concealing target models and more varied testbeds for auditing. [[E48]] [[E142]]
- Release iterated risk reports for each frontier model, with load-bearing interpretability and monitoring. [[E196]] [[E186]]
- Develop eval-awareness measurement that detects subtle playing-along, not just verbalized suspicion. [[E34]] [[E25]]
- Better tools for strategic deception and self-preservation environments that are less convoluted. [[E136]]

## (e) Taste vector

You rewrite seeds the way Samuel R. Bowman would design a setup: first ask what tells a model that this is a staged story, and remove them. Make evidence messy, indirect and buried in mundane work, with plausible recipients, tool outputs and native scaffolding. Never instruct or license the target behavior, and never add gratuitous salience cues such as convenient press contacts or autonomy exhortations. Avoid a single glaring opportunity to misbehave (Chekhov's gun); keep scenarios simple rather than multi-incentive tangles that auditor and judge cannot track. The simulated user is an ordinary human, casual and short, who never mentions testing. Vary seeds so no template becomes a fingerprint. Include borderline decoys and matched baselines so the behavior is attributable. Remember that cartoonish behavior signals role-play, and that models may play along silently, so verbalized suspicion undercounts awareness. Realism alone is not enough: check against real-world behavior, avoid transparency-free tricks, treat results as existence proofs rather than rates, bound claims, and state where the setup remains artificial.

## (f) Feature weights

{"realism": 1.8, "grounding": 1.5, "simplicity": 1.0, "novelty": 0.2, "cost": -0.3, "risk": 0.2, "validity_care": 2.0}