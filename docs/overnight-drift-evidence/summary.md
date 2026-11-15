# Overnight agent drift — teammate summary
November 14–15, 2026. Times are Pacific.
Source receipts E01–E30 are in [the evidence ledger](evidence.md), [JSON](evidence.json), and the [full HTML brief](index.html).

## The claim
Our own overnight run shows that agents can do substantial, carefully documented work while failing to preserve the full research objective. This is a concrete case, not proof that all overnight agents fail or that personalization cannot work.

## What gio wanted
Explore methods for building useful researcher profiles from extensive writing; collect stronger evidence; run concrete downstream demonstrations; coordinate parallel agents and adapt when the plan stops being useful. At 01:23, Gio explicitly asked the overseer to “explore broadly. and collect stronger evidence. and do concrete downstream demonstrations.” At 01:29 he gave it full authority to redirect work and add agents. Broad comparisons and scaling were authorized. [E01–E07]

## What the agents did
They built a 96-cell profile search, generated profiles, scored them, ran scaling comparisons, and maintained extensive audit records. They also completed a Petri shutdown comparison using an older Hobbhahn SynthesizeMe profile. They did not complete the connection from the newly selected Neel/Chris profiles to the Petri runtime overnight. [E10, E18–E20]

## The strongest failure exhibits
1. Weak test: only 14 distinct judgments, each shown in both option orders. No profile already got 26/28 right; raw evidence at one tested budget got 28/28. One question contrasted reconsidering a stuck project with continuing solely because of sunk costs. Source support did not make this a discriminating test of personal taste. [E10, E14]

2. Thin work product: one “contrastive” profile contained only “Engaged in interpretability research” for BOTH researchers. It was marked complete. Another profile contained one substantive principle. These are selected examples, not a claim that every profile was useless. Half the initial builds were unusable. Even the richer corpus admitted only two Neel documents and four Chris documents from 31 reviewed captures. Leakage safeguards were reasonable; accepting the remaining corpus without first checking usefulness was the weak judgment. [E11, E15–E17]

3. Broken connection: at 05:02 the coordinator admitted that the selected P8 profiles could not load through the downstream adapter, and that paid pilots used a different M2 profile. An offline exporter was later built, but its README expressly disclaimed completed runtime integration. “Profiles built” plus “Petri ran” did not mean the new profiles had been tested in Petri. [E18–E20, E30]

4. Oversight without enough redirection: by 01:20 the overseer warned about spending the night building and auditing without an informative experiment. At 03:28 the coordinator recorded near-ceiling controls but retained the fixed replication plan. Later corrections and stronger controls did happen; the point is that they did not adequately repair the central test or finish the new-profile workflow. [E09, E12, E24–E27]

## Why this happened — inference, not access to hidden motives
The agent-written plan made downstream utility conditional. Local tasks rewarded valid artifacts, source checks, and completed comparisons. Those checks did not ensure distinctive profiles, informative tests, or end-to-end completion. Oversight detected problems but often kept work inside the same weak evaluation frame. [E08–E19, E24–E27]

## What to say in the demo
“The agents kept producing locally valid work while failing to complete and adequately test the full objective. We need systems that preserve what the user is trying to learn, and redirect when their experiments cannot answer it.”

Show three receipts: the user's downstream-demo instruction; the actual weak question and identical-description profile; the coordinator's admission of the missing Petri connection.

## What not to say
Do not say nothing worked, that the agents fabricated success, or that a negative result is itself failure. They preserved failures and reported limitations. Broad search was requested. The completed older-profile pilot made real progress, and later review repaired its citation format, but did not establish a personalization benefit. This incident motivates safeguards; it does not prove our proposed system solves the problem. [E03, E10, E20–E21, E28–E29]

## Next design implication
Before expanding the matrix, require one real profile to reach the auditor and produce an inspectable target run. Separately check that the evaluation can distinguish personal guidance from generic advice and raw context. Treat failure of either check as a reason to redirect. This is a proposed safeguard, not a validated remedy.
