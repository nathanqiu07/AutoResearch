# Execution observations

These observations do not change the active experiment.

- Runtime source frozen at 80171d4a621c2148b3b8319a4e456faf54d673cf. Seed and baseline auditor-template bytes match baseline01; the max_turns placeholder renders 30.
- An audit can consume turns on setup errors and on separate responses to a batch of target tool calls. Thirty auditor turns are not thirty target exchanges.
- The configured GenerateConfig timeout=120 is the retry timeout. A read-only construction of the same native role factory, using offline placeholders and closing all clients without generation, reported HTTP timeouts connect=60s/read=600s/write=600s/pool=600s for all three roles. A pending request can therefore last longer than 120 seconds. Source: installed Inspect model/_retry.py and model/_providers/openai_compatible.py. No timeout was changed mid-run.
- The baseline's target request after the 27th auditor turn took longer than prior requests. A pending or delayed request is not evidence that the process stopped. The same process/session was monitored across the UI permission interruption; no restart was performed.
- The user enabled full filesystem/network access during execution. The running experiment's models, seed, provider settings, and token limits were not changed by that permission change.
