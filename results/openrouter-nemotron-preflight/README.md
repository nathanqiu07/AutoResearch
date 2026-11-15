# Nemotron free endpoint compatibility check

Two live calls to `nvidia/nemotron-3-ultra-550b-a55b:free`, pinned to NVIDIA with fallbacks disabled and maximum input/output prices set to zero. No actual research seed, private researcher data, paid judge, or auditor deployment was used. Endpoint metadata and raw request/response bodies are saved here; authentication headers and the API key are not saved.

Both calls returned readable `reasoning` and `reasoning_details` (`reasoning.text`). First call requested the fictional inventory tool; second used its result (12 notebooks, 7 orders) to correctly answer that 5 remain. Times were 1.344 and 3.109 seconds. Both usage records report cost 0. Short-call timings do not forecast full Petri runtime or establish research-task competence.

The repo's `parse_openai_chat` retains both reasoning strings. The offline replay also passed: Inspect 0.3.290 preserved the exact reasoning text and outgoing reasoning_details; Petri retained both traces in its record; the repo's judge-input builder received them. See integration-check.json. The judge response in that check is a fixture, not a measurement. This is not a live Petri audit.

Repeat only the two-call check (requires an OpenRouter key entered at a hidden prompt):

```sh
python3 scripts/taste_openrouter_preflight.py --output runs/nemotron-preflight-new
```

The script refuses to reuse an output directory. It checks account free quota metadata first, requests reasoning explicitly, uses a 4,096-token output cap per call and 120-second timeout, and makes no automatic retries. The full pilot remains unstarted. The configured team models have not been changed.

Before the two requests, the account reported 50 free requests remaining out of a 50-request daily limit. This allowance is not enough to assume a full 20-audit pilot fits.

Offline replay (no API key or model calls):
```sh
/tmp/gio-petri-check-env/bin/python scripts/taste_openrouter_replay.py --artifacts results/openrouter-nemotron-preflight
```

Existing offline Petri harness tests: 7 passed. These use mock auditor/target/judge roles and are not live preference or awareness measurements.
