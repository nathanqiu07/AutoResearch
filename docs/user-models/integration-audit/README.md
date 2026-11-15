# User-model integration audit

This audit checks what saved profiles deliver to consumers. It does not measure
preference accuracy or research quality. No live model calls, final-test labels,
model changes, inference-setting changes, or production adviser edits occurred.

## First verified result

Evidence: [20261115-001](../../../results/integration-audit/20261115-001/).
Use `runs/verified-20261115/` for current-tool results. Earlier runs and their tool
snapshots are retained, including audit-development failures. Exact commands,
stdout/stderr, source commits, source/artifact hashes and prompt inputs are saved.

Four saved PRISM pilot models preserve their serialized state and loaded artifacts
in the pilot checkout, the baseline checkout and the isolated main snapshot.
The actual prediction path is exercised using a labeled recording transport.

| Model | Saved personal text | Choice predictor receives | Proposer receives |
|---|---|---|---|
| M0 | None | No personal text | No principles |
| M1 | Five labeled examples | Five examples | No principles |
| M2 pilot | None retained | No personal text | No principles |
| M3 pilot | Two principles | Two principles | Two principles |

These channels differ by design; a principles-only downstream comparison would
not reproduce the M1 raw-history intervention. Empty M2 is a legitimate saved
outcome and must be labeled; it is not evidence of a winning method.

## F1: artifact identity does not pin runtime prediction semantics

The draft at `9616fe8a3c550664d8aae0b72c938d936c0a7347` uses M2's persona and
examples for choice prediction and exports principles separately for proposals.
The baseline checkout at `0a541515f71e519cad0e4b0629336fd28cb509f0` and the audited
main snapshot use inherited prediction, which also injects saved principles.

A nonempty **synthetic** M2 fixture loads in all three. Its captured prediction
contains zero principles in the draft and one principle in the other two. The
persona and example remain present. This is a change in conditioning, not a
measured performance difference. The real pilot M2 is empty and masks this case.

Saved M2/M3 prompt versions also differ from runtime versions outside the draft.
The loader checks backend identity but accepts that mismatch. Pin source commit
and artifact together for a handoff; a successful load alone is insufficient.
The audit exposes saved/runtime versions and source hashes rather than changing
the loader's policy. Both linked chats were notified.

## F2: malformed adviser inputs can escape fallback

`confidence/README.md`, `probe.py`, and `run-01/capture.json` reproduce 57 probes
on both checkouts. Existing targeted suites passed 48 and 41 tests respectively.
Proposed safe-fallback regression tests remain deliberately RED and are outside
the default test suite; production behavior has not been changed.

- Invalid feature distributions can reach D1 ranking. A real profile containing a
  NaN or infinity weight produces NaN priorities in the actual research loop.
- Certain malformed choices and very large numeric confidence/probability values
  raise outside the prediction exception handler, including decisive decisions.
- The feature-profile path marks low-confidence advice usable despite the stated
  threshold. Changing this path requires the owning team to settle its policy.

Separate documented limitations: calibration flags are ignored; an empty text
profile still invokes generic preference prediction; optional invalid
probabilities fall back to confidence. These are reported, not silently changed.

## F3: prepared packet and executed settings are distinct records

The copied preparation packet matches the original preparation packet exactly.
Its settings still describe two proposed arms. The run-root `settings.json`
records the actual baseline-only execution.

The all-field comparator found nine changes. Three were explicitly declared for
this check: arms, data gate, and status. Six others remain visible: code version,
prepared-code provenance, prior-spend allowance, remaining-budget gate, run cap,
and unresolved execution requirements. These are not automatically errors.
Models, provider routing and generation settings have no differences in these
saved files. This is configuration evidence, not an independent verification of
the providers' actual runtime behavior. The audit does not assess statistical
comparability or assume metadata is complete.

## Tools

Run from the repo root with Python 3.9+; only the standard library is required.
Use a fresh output path each time.

```sh
python3 -B scripts/user_model_audit/profile_audit.py \
  --source-root . --artifact path/to/usermodel.json --out profile-audit.json

python3 -B scripts/user_model_audit/packet_audit.py \
  --left path/to/prepared-settings.json --right path/to/executed-settings.json \
  --allow arms --out packet-audit.json

python3 -B -m unittest tests.test_user_model_profile_audit tests.test_user_model_packet_audit
```

The profile inspector calls the actual loader and predictor with a recording
transport whose identity strings match the saved artifact. It never creates a
real backend. This deliberate shim does **not** prove live backend access or
compatibility. Synthetic uniform probabilities and zero feature values merely
let the consuming code complete; they are never reported as accuracy evidence.
M4's learned weights operate locally after two recorded feature requests.

The source root must contain the required modules; imported package origins are
checked. Source files and every input artifact are hashed before/after the batch.
The report fails if prediction or roundtrip fails or an input changes. Version
mismatches are reported without treating them as universally incompatible.

Packet allowances match exact dot paths. Arrays and added/removed objects are
compared whole; missing is distinct from null. Every field is considered.
Exit zero means the report was written, even if unexplained changes remain.

## Verification and next work

The full baseline suite passed 656 tests with two skips. With the new audit tests,
677 tests passed with two skips; existing ResourceWarnings are retained in logs.
An independent reviewer found source-origin attribution, learned-M4 transport,
and batch input recheck defects in the audit tool. All three now have reproducing
regression tests and pass. No packet-comparator defect was found in that review.

Next: audit the profile-search candidates as their shared contract and artifacts
arrive, check any baseline revision packet, and hand the adviser reproductions to
the owning integration work. Keep every run and failed check. The overnight goal
remains active; this first package does not establish broad integration coverage.
