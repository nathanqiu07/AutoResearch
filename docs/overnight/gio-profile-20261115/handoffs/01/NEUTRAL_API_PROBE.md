# Neutral Sol/Astra API access probe

This standalone script performs only the coordinator-assigned access probe. It
does not build a profile, read researcher inputs, score predictions or retry.
Root parses credentials with its established pinned data-only parser and injects
the child environment. The script/backend reads OPENAI_API_KEY and optional
OPENAI_ORG_ID/OPENAI_PROJECT_ID only; it never reads a credential file or prints
credentials/provider error bodies.

The fixed prompt is:

`Return exactly this JSON object and no other text: {"probe":"ok"}`

The panel is exactly gpt-6-sol then gpt-6-astra, sequential, with medium reasoning,
max_tokens=8192, timeout cap=180 seconds and no tools. The current pinned actual
OpenAIResponsesBackend performs both calls and enforces shared reservations and
the 30-minute cache-write price bound. Per-call caps are $0.125 and $0.50; the
dispatch allows at most two attempts and $1 total. No live calls were made while
implementing or testing this script.

## Dispatch and launch

Root supplies a raw-file-hashed JSON dispatch with these fields:

```json
{
  "schema_version": "neutral-api-probe-dispatch-v1",
  "campaign_id": "gio-profile-20261115",
  "script_sha256": "EXACT SCRIPT FILE SHA256",
  "runtime_root": "ABSOLUTE FROZEN NATIVE WORKTREE",
  "runtime_commit": "EXACT FULL COMMIT",
  "runtime_backend_sha256": "RAW backends.py SHA256",
  "policy": {"path": "EXISTING PHASE2 POLICY FILE", "sha256": "RAW FILE SHA256"},
  "authorization_source": "EXACT COORDINATOR ASSIGNMENT",
  "deadline": "2026-11-15T17:00:00Z",
  "max_seconds": 400,
  "max_calls": 2,
  "max_usd": "1",
  "probes": [{"model": "gpt-6-sol", "max_usd": "0.125"}, {"model": "gpt-6-astra", "max_usd": "0.5"}],
  "settings": {"reasoning": "medium", "max_tokens": 8192, "timeout": 180},
  "claims_root": "CANONICAL SHARED CLAIM ROOT OUTSIDE RUNTIME",
  "output_root": "NEW OUTPUT DIRECTORY OUTSIDE RUNTIME"
}
```

```sh
python3 path/to/neutral_api_probe.py \
  --dispatch /absolute/path/to/dispatch.json \
  --expected-dispatch-sha256 EXACT_DISPATCH_FILE_SHA256
```

The runtime is selected explicitly in the hashed dispatch. Before execution the
CLI verifies the exact Git HEAD, clean tracked files, backend file hash and import
origin. It checks the policy hash and requires its existing ledger file; it never
creates or resets a phase ledger. The dispatcher must verify the script hash
before launch as well. Atomic exclusive claim files are written before calls.
Claims bind the campaign, policy, fixed prompt, panel and settings, so changed
output directories do not grant another attempt. All launches must share the
coordinator's canonical claims root.

Started records preserve the fixed prompt and its hash, settings/hash, model and
backend identity. Result records preserve normalized response text/hash, original
response hash, per-call known usage, unknown-usage flags, dollar holds and errors.
A successful response must equal `{"probe":"ok"}` after stripping outer
whitespace. Different output is a completed call with `completed_call_invalid_probe`;
it is preserved without retry and the next assigned probe may run. An uncertain
backend failure stops the panel and keeps the backend's shared reservation.

`summary.json` includes both rows, local attempted calls/known dollars/holds and
the shared ledger snapshot. Stdout contains only status, count and summary hash.
Exit 0 means both probes matched; exit 2 means blocked, partial or invalid. A
crash leaves the claim and any existing reservation intact. Root reviews these
artifacts before any follow-up. These results establish API access only.

Offline tests use fake HTTP with the actual current backend and temporary ledgers:

```sh
python3 -m unittest discover -s docs/overnight/gio-profile-20261115/handoffs/01 -p 'test_neutral_api_probe.py'
python3 -m unittest discover -s tests -t .
```
