# Bounded embedding producer

This standalone script consumes exactly two assigned, hashed request packets.
It does not change the frozen runtime or its API backend identity, select jobs,
scrape inputs, retry a request, or authorize spending. No live call was made while
implementing or testing it.

The coordinator verified the model and rate on November 15, 2026:
[text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small)
costs $0.02 per million input tokens. The
[embeddings API](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
supports the explicit dimensions and float encoding used here.

## Assigned packet schema

Each packet has exactly `model`, `dimensions`, `encoding_format` and `input`.
The first three values must be `text-embedding-3-small`, `1536` and `float`.
Input is a nonempty list of nonempty strings. The script POSTs the original
packet bytes without reserializing or modifying them. File SHA256 and SHA256 of
the canonical input list are both checked before admission.

Canonical JSON means sorted keys, compact separators, UTF-8, ensure_ascii=False,
and allow_nan=False. The supplied packet bytes also have a trailing newline.

The authorized proposal was checked without printing its input text:

| Packet | Strings | Input UTF-8 bytes | Packet SHA256 | Input-list SHA256 |
|---|---:|---:|---|---|
| neel_nanda-request.json | 18 | 8471 | `2d251fe7228d3072f3aaaf5f253a936608d30fdc2ccceeb596e2b0f5a9ef0dd6` | `854a945768889c52479af8f8fc6be0b12d68160ab01f4c0e60110d8dc6075fdc` |
| chris_olah-request.json | 22 | 12261 | `6ff3d4b4598cd3bdd4ea63e36846224d264a23be7e18ba7a8c505804cd0d748e` | `b3dbf1b683e452b5f83f7538199d45fcb222a1f63d50210e980121af43ae4b8a` |

Those requests remain at the coordinator-approved location; their text is not
copied into this branch. The script has no default request paths.

## Dispatch manifest

The coordinator supplies an immutable JSON object with these fields:

```json
{
  "schema_version": "bounded-embedding-dispatch-v1",
  "campaign_id": "gio-profile-20261115",
  "model": "text-embedding-3-small",
  "dimensions": 1536,
  "encoding_format": "float",
  "rate_usd_per_million_input": "0.02",
  "rate_source": "https://developers.openai.com/api/docs/models/text-embedding-3-small",
  "rate_verified_at": "2026-11-15",
  "authorization_source": "EXACT COORDINATOR RUN AUTHORITY",
  "max_calls": 2,
  "max_usd": "0.01",
  "max_seconds": 120,
  "timeout_seconds": 30,
  "deadline": "COORDINATOR ISO TIMESTAMP WITH TIMEZONE",
  "script_sha256": "EXACT PRODUCER FILE SHA256",
  "runtime_root": "ABSOLUTE CLEAN NATIVE RUNTIME WORKTREE",
  "runtime_commit": "EXACT FULL RUNTIME COMMIT",
  "runtime_backend_sha256": "RAW BYTES SHA256 OF RUNTIME backends.py",
  "ledger": {
    "path": "CANONICAL SHARED SQLITE LEDGER PATH",
    "max_usd": "EXACT EXISTING SHARED LEDGER LIMIT",
    "deadline": "EXACT EXISTING LEDGER DEADLINE",
    "max_inflight": 2
  },
  "claims_root": "CANONICAL EMBEDDING CLAIM DIRECTORY OUTSIDE RUNTIME",
  "summary_path": "NEW ABSOLUTE SUMMARY JSON PATH",
  "requests": [
    {
      "request_id": "neel-nanda-embedding-v1",
      "packet_path": "EXACT APPROVED PACKET PATH",
      "packet_sha256": "EXACT PACKET FILE SHA256",
      "input_sha256": "EXACT CANONICAL INPUT-LIST SHA256",
      "response_path": "NEW RAW RESPONSE FILE PATH",
      "receipt_path": "NEW RECEIPT JSON PATH"
    },
    {
      "request_id": "chris-olah-embedding-v1",
      "packet_path": "EXACT APPROVED PACKET PATH",
      "packet_sha256": "EXACT PACKET FILE SHA256",
      "input_sha256": "EXACT CANONICAL INPUT-LIST SHA256",
      "response_path": "NEW RAW RESPONSE FILE PATH",
      "receipt_path": "NEW RECEIPT JSON PATH"
    }
  ]
}
```

The example contains placeholders and is not executable approval. Shared ledger
limits come from the coordinator's current ledger, not a new per-worker allowance.
The embedding allocation remains at most $0.01 and two calls even when the
campaign has a larger approved budget. The script refuses ledger-policy changes.
The claims directory must be shared for this producer across launches: claims
bind model, dimensions, encoding and input hash, so changed output paths cannot
grant another attempt.

## Launch and credentials

The coordinator first verifies the dispatch file SHA256 and script file SHA256,
and prepares an environment using its pinned credential parser. Treat credentials
as data; do not source or execute a `.env` file, place keys on a command line, or
print them. This script only reads OPENAI_API_KEY and optional OPENAI_ORG_ID and
OPENAI_PROJECT_ID from the supplied child environment.

```sh
python3 path/to/embedding_producer.py \
  --dispatch /absolute/path/to/assigned-dispatch.json \
  --expected-dispatch-sha256 EXACT_DISPATCH_FILE_SHA256
```

The CLI verifies a clean native Git runtime at the exact commit and the raw hash
of its existing overnight/backends.py. It imports DollarLedger from that runtime,
checks import origin, and disables bytecode writes. Output, claims and ledger
paths cannot be inside the frozen runtime. No new model adapter is imported into
the pilot or written under autoresearch/.

## Evidence and failure behavior

Before each POST the script checks remaining time and reserves a conservative
cost using packet UTF-8 bytes plus 1024 as the input-token upper bound. The two
reservations must fit $0.01 before any call. Shared DollarLedger handles total
spend and concurrency. No extra request is issued for retry or repair.

Success requires the exact response model, all requested indices exactly once,
1536 finite numeric values per vector, complete consistent usage and usage within
the reserved bound. The raw response is preserved byte-for-byte. Its receipt
contains sorted indexed vectors, packet/input/response hashes, model, dimensions,
usage, estimated cost, script hash and native runtime commit. Summary rows also
include receipt file hashes. These files are for role 05's vector-store assembly;
the producer does not assemble or edit that store.

Unknown or malformed outcomes retain the full reservation plus known usage and
stop the second request. Error output omits provider text, inputs and credentials.
If a valid response cannot be written locally, its paid call stays accounted for
and the remaining packet stops. A crash leaves a durable claim and pending ledger
reservation; neither is reset automatically. Exit 0 means both packets completed;
exit 2 means partial/preflight/local failure. The coordinator inspects the summary,
claims and ledger before assigning any follow-up.

Tests use synthetic text, fake HTTP and real temporary shared ledgers:

```sh
python3 -m unittest discover \
  -s docs/overnight/gio-profile-20261115/handoffs/01 \
  -p 'test_embedding_producer.py'
python3 -m unittest discover -s tests -t .
```
