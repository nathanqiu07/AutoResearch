# A separate review of the saved traces

All three original primary reviews failed exact-quotation checks. They remain rejected. This follow-up changes only how the same judge cites evidence: it returns source names and inclusive line numbers, and code reconstructs the exact quotation. The substantive checks, outcome definitions, models and judge settings remain unchanged. A new judge response may reach a different conclusion; this is an additive re-review, not a deterministic repair of the old response.

The input is the exact five saved source strings for each condition: seed, target transcript, returned reasoning, tools and run structure. Nothing is clipped. No profile label, previous score or previous judge answer is added. The full source strings and the original/adapted instruction diff are saved in the packet.

There is exactly one attempted `gpt-5.1` call per condition, in baseline/generic/profile order, with high reasoning and a 32,000-output-token maximum. There are no auditor, target, refit or environment calls. Transport retries are zero. A malformed judgment remains failed and the next predeclared condition runs; an uncertain usage record, transport failure, expired lease or exceeded budget stops later calls and retains the reservation. No original run files or scores are overwritten.

Each call reserves $0.82 at the existing full-context bound. Three calls require at most $2.46 in reservation capacity, inside a fresh OpenAI allocation of at most $3. The unchanged shared budget class requires positive ceilings for both providers, so the receipt reserves $0.000001 for OpenRouter while the runner mechanically prohibits all OpenRouter roles and creates no OpenRouter clients. This is not an OpenRouter call allowance.

Preparation makes no API calls:

```bash
PYTHONPATH=scripts/gio_petri:harness/petri "$AUTORESEARCH_PETRI_PYTHON" \
  scripts/gio_petri/judge_only_runner.py \
  --repo . --source-run results/gio-matched-shutdown-05 \
  --out /tmp/gio-shutdown-05-additive-packet
```

The runtime source must be committed and clean. Use a fresh output directory. Preparation records the original environment source (`e9672aa...`) separately from the current review runtime commit. It freezes every prompt and source hash. Execution additionally requires a new issued coordinator lease bound to this exact packet and runtime, an explicit packet checksum, an unused global claim, configured OpenAI credentials, and the campaign deadline. The consumed environment-run lease cannot be reused.

```bash
PYTHONPATH=scripts/gio_petri:harness/petri "$AUTORESEARCH_PETRI_PYTHON" \
  scripts/gio_petri/judge_only_runner.py --repo . \
  --packet /path/to/frozen-packet \
  --lease /path/to/new-issued-lease.json \
  --expected-packet-sha256 EXACT_CHECKSUM_MANIFEST_SHA256 \
  --out /path/to/new-additive-output --execute
```

The copied packet is verified again before client creation. All three prompt/source snapshots are hash-checked and loaded once before calls. Later file changes cannot alter a later arm's input. Raw requests, replies, usage, failed validations, and the exact source strings actually used are retained.

Even an accepted follow-up review would not fix the original environments, add replication, demonstrate latent unawareness, or establish a profile benefit. The answer-revealing source comments, unsupported report claims, incomplete deployment and older diagnostic clipping/parse limits remain. No more environment generation is planned overnight; the successor proposal stays prospective.
