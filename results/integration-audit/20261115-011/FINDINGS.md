# Independent API adapter and shared-ledger audit

Reviewer role: `parallel_gap_audit`, independent integration reviewer.
Scope: the pinned Responses adapter, shared dollar reservations, concurrency,
uncertain calls, declared request identity/settings, and usage accounting.
Runner/final-use policy and other workers' controls were not re-audited.

**Result: 13 checks verified; two failed observations identify one narrow usage
accounting gap. All ten existing backend tests passed. No budget bypass was
observed.** All 160 published snapshot-file hashes match and remain unchanged.

## Finding: partial reported usage is discarded

At `autoresearch/taste/overnight/backends.py:224-230`, both `input_tokens` and
`output_tokens` must validate before either is copied into the accounting
variables. If one valid component is supplied and the other is absent, rejection
occurs while both local counters remain zero.

Two synthetic Responses bodies demonstrate this:

| Reported usage | Recorded input/output | Recorded known spend | Reservation and follow-up |
|---|---|---|---|
| `{"input_tokens":100}` | `0 / 0` | `$0` | `$0.00371` retained; uncertain lane; second call blocked |
| `{"output_tokens":20}` | `0 / 0` | `$0` | `$0.00371` retained; uncertain lane; second call blocked |

The two evidence keys are `partial_input_usage` and `partial_output_usage` in
`run-01/observations.json`. Each made exactly one mocked transport call. Under the
adapter's declared sol rates, the independently valid component in either case
would contribute `$0.0002`. This arithmetic uses the code's rate table; it is not
a statement about current provider pricing or an invoice.

This falls short of the module/README claim that an uncertain outcome retains its
full hold **plus any known usage**. It is a reporting gap under malformed/partial
usage, not a demonstrated overspend: the full conservative reservation remains
charged and all subsequent calls are blocked. No claim is made that real provider
responses normally omit just one field.

Suggested correction: preserve each independently valid reported component before
raising for missing/malformed usage, while keeping the full reservation and lane
hold. Alternatively make the unknown accounting status explicit instead of
representing a supplied valid component as measured zero. A regression should
assert both preserved valid usage and unchanged uncertainty handling.

## Verified boundaries

- The shared ledger counts pending reservations before transport. Separate ledger
  instances cannot exceed the aggregate declared dollar allocation.
- Reopening the same ledger refuses changed dollars, deadline or concurrency.
- Pending reservations persist across reopen. Uncertain reservations retain the
  full amount plus valid complete reported usage, block further reservations, and
  cannot be settled again to release the hold.
- Three concurrent thread connections admit exactly two pending reservations.
  A separate three-process probe also admits exactly two, with all child argv,
  stdout/stderr and exit codes retained.
- Expired campaign and insufficient per-job allocations block before transport.
  A completed call consumes a one-call local allocation.
- Explicit outgoing model, reasoning, maximum output, `store=false` and default
  service tier reach the mocked request. Tools and temperature are absent.
  Identity records reasoning and `temperature=not_sent`, rather than claiming the
  supplied generic temperature was enforced.
- Successful usage charges all reported input at the declared uncached rate and
  total output once; cached-input/reasoning detail fields are not double-counted.
  The synthetic `100 input / 20 output` response records `$0.0004` at the table's
  sol rates and releases the reservation.
- A transport exception makes one mocked call, retains the reservation, holds the
  lane and does not expose the synthetic key in the returned error. Complete usage
  on an incomplete response is preserved. Reported over-bound usage is also
  retained while holding the lane. Entirely missing usage does not fabricate
  token counts and keeps the full uncertain reservation.

## Credential and network isolation

The adapter has no explicit API-key argument. Before constructing or calling each
test backend, the probe replaces that module's entire `os` reference with a
synthetic-only environment mapping and patches `urlopen` with a local function.
It never reads or patches the real process environment. No real key is used.

Original unit tests run in a child process with an explicitly supplied synthetic
environment, replacing environment inheritance. An outer denial guard blocks
`urlopen`, socket connect, and create_connection before tests load; individual
tests replace HTTP with their own local mocks. The child command, environment,
stdout/stderr and exit status are recorded. No network or paid call occurred.

## Limits

These results concern accounting under the configured rate table and reservation
bound. Current billing rates, model availability and physical provider/model
authenticity were not verified. The UTF-8-byte-plus-overhead token bound remains a
conservative assumption, not tokenizer or billing proof. The coordinator must
supply one shared ledger path; hostile code choosing another path is outside this
cooperative accounting boundary. No live HTTP retry/redirect behavior, invoice
reconciliation, entire campaign, or final-data workflow was executed. Passing this
audit does not establish live readiness.

## Provenance and reproduction

- Source commit: `c840615c885464404147a1cdea12343569d331fc`.
- API implementation commit: `e24543cb40b2043016f771a2a0359766e81399d2`.
- Adapter SHA-256: `b3b163e07365937fee4d7f1bde76fe8cc84181cbe8c07462f2cb927295f319b7`.
- Existing backend-test SHA-256: `9bfcfffdfe3e1b589aba398cf282b91271ab19811f920b8328dae26ccc3de4cc`.
- Probe SHA-256: `db12bbc7d5809700cf60c5d3e057eaafcbb7919a71ff8aa0f565d13ab02fc2fc`.

```sh
python3 -B /tmp/gio-integration-audit-staging/api-adapter-11/reproduce.py \
  --source-root /tmp/gio-integration-audit-contract-c840615 \
  --out /tmp/gio-integration-audit-staging/api-adapter-11/run-02
```

Use a fresh output directory. The probe creates only new evidence/SQLite files
there and does not edit the source snapshot. `run-01/observations.json` records all
inputs, requests, observations, source hashes and executed commands. SQLite ledgers
and the original test logs are retained. Run-01 exited 0 because evidence capture,
source integrity and existing tests succeeded; the report separately retains the
two failed partial-usage assertions. No production fix was made.
