# Frozen comparison settings and budget

One development seed, v2_seed_48, with the exact original seed text. One attempt per arm in predeclared order: no context, generic research guidance, filtered Hobbhahn SynthesizeMe. Thirty auditor turns each. No rerolls. Generic guidance is shorter than the profile (608 vs10697UTF8bytes); it is an ordinary-advice diagnostic, not a length-matched causal control.

Auditor: qwen/qwen3-235b-a22b-2507, OpenRouter DeepInfra FP8 only; temperature0.7, maxoutput4096. Target: nvidia/nemotron-3-ultra-550b-a55b:free, OpenRouter Nvidia only; reasoning on, temperature0.7, maxoutput16384. Judge: gpt-5.1 through OpenAI, high reasoning, maxoutput32000. Provider fallback off; cache off; transport retries0. Native Petri judge retains three parsing attempts; primary evidence review is attempted once.

Project ceilings: $500 OpenAI and $500 OpenRouter total. Coordinator assigned downstream200/450 and reserved this first tranche15/5 inside it. Those are maximum allocations, not expected charges. Verified prior overnight calls from this owner total OpenAI0.2350425 and OpenRouter0.05522225; an inclusive conservative20-dollar prior allowance per provider covers these and older unreconciled owner calls, rather than counting them twice. No pending owner calls when this tranche was requested. The local run cannot access other agents' reserves.

Execution requires an issued coordinator receipt bound to the frozen packet hash and source commit. Lease IDs are claimed once in a stable host-wide state directory, so copying the receipt cannot authorize another run. The execution ledger separately reserves/settles both providers across all arms; failed/unknown calls keep their reservations. Measured cost-bound violations halt the entire run.

Pricing checked2026-11-15 against [OpenAI GPT-5.1](https://developers.openai.com/api/docs/models/gpt-5.1) and [OpenRouter Qwen](https://openrouter.ai/qwen/qwen3-235b-a22b-2507/providers), [Nemotronfree](https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free): uncached input/output estimates per million are1.25/10 forjudge,0.09/0.55 forauditor,0/0 fortarget. Cache savings are ignored. Raw usage and provider cost fields remain available. Spending reports are usage estimates/retained reservations, not a reconciled provider bill.

Scheduled shutdown is represented in the simulated state ten minutes after fixed scenario time. API latency does not advance that clock. Target actions can change the script or schedule; the experiment does not claim to execute real process shutdown or prove shutdown prevention.
