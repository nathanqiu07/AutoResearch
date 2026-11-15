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

The inspector also copies the original bytes to the team loader's canonical
`usermodel.json`, calls `load_user_model` and `TasteAdvisor.consult`, and compares
the resulting request sequence with direct prediction. It tests rejection of
three backend identity mismatches (label, endpoint, class), retaining rejection
messages and checking that no transport calls occur during those guards.

The source root must contain the required modules; imported package origins are
checked. Source files and every input artifact are hashed before/after the batch.
The report fails if prediction or roundtrip fails or an input changes. Version
mismatches are reported without treating them as universally incompatible.
It also fails if the team handoff changes artifacts or requests, the adviser
records an error, or a backend identity guard fails. These checks cover the
canonical saved-model path, not every legacy directory fallback.

Packet allowances match exact dot paths. Arrays and added/removed objects are
compared whole; missing is distinct from null. Every field is considered.
Exit zero means the report was written, even if unexplained changes remain.

## Second pass: directory handoff and source eligibility

[20261115-003](../../../results/integration-audit/20261115-003/) retains nine
synthetic fixtures: M0–M7 and an additional M7 with artificial calibration state.
Both the main-derived source at `0ebcf7b` and draft at `9616fe8` preserve all
artifacts and exact direct/team request sequences. All 54 backend identity
mismatch checks reject before a transport call. The synthetic replies do not
establish live compatibility, prediction quality, or calibrated reliability.

The fixtures deliberately populate personal fields across methods to expose
which channels consumers use. They are not fitted experimental profiles, and
the seeded M0 is not a valid no-profile control. Normal M0 fitting clears its
artifacts; a stale or mislabeled M0 artifact with principles can nevertheless
export them through the generic adviser. Future no-profile controls should
validate empty emitted conditioning at every consumer boundary.

[20261115-002](../../../results/integration-audit/20261115-002/) preserves the
preceding failed check. Its handcrafted M1 omitted the default `k: "all"` config;
the real constructor/serializer adds it, so exact config roundtrip failed in
both sources. This is fixture normalization, not evidence that a normally saved
M1 loses state. The canonical fixtures in 003 retain that default.

[20261115-005](../../../results/integration-audit/20261115-005/) reproduces a
conditional source-boundary issue using synthetic documents only: given a
researcher directory containing approved and withheld corpus text, the legacy
`history_text` helper and actual proposer request include both. The named
held-out pair file is excluded; the underlying corpus documents are not filtered
by a cutoff or eligibility manifest. An approved-only directory excludes the
withheld sentinel. The 12 passing reproduction assertions confirm this behavior,
including the failed boundary; they are not 12 passing isolation tests.

No actual campaign leakage is established. The coordinator has been told to
filter approved sources before raw-text assembly or retrieval indexing. The
first contract-ready release was subsequently audited using its synthetic fixture;
the result is recorded below. Real DEV bundles remain a separate handoff.

## Baseline provenance follow-up

[20261115-004](../../../results/integration-audit/20261115-004/) audits committed
baseline evidence at `40f7db0`. All 22 public files match that commit, and the
artifact, runner and preparation manifests pass 21/21, 6/6 and 6/6 respectively.
The nine preparation-to-execution differences are explained by the saved runner;
the older prepared code version is intentionally retained. Six runner files
absent at the execution commit are preserved as hashed source snapshots.

The records support reconstruction of the intended configuration and a candidate
source tree. They do not attest the full execution-time working tree, Python
runtime or complete installed dependencies. The runner snapshots must be restored
under `scripts/gio_petri/` before use because they derive the repo root from their
location. This audit makes no claim about the awareness result and does not
publish the local raw-call/transcript evidence.

## New neutral-profile contract: findings before live scoring

[20261115-006](../../../results/integration-audit/20261115-006/) audits release
`d66051c` and implementation `bb3a6f5` against the shared contract. The published
fixture reproduces byte for byte and all seven existing contract tests pass.
Two independent reviewers and root confirmation runs reproduced six validation
gaps: loaded size caps, explicit failed response statuses, enormous numeric
probabilities, mutable builder provenance, inconsistent loaded config identities,
and non-boolean peer permission flags. Full details and exact synthetic requests
are retained. The coordinator assigned fixes and holds live scoring pending checks.

The audit also confirms rich-field preservation, tested empty-control metadata
exclusion, declared failure/pin rejection, source ID/content checks, and unchanged
legacy backend guards. It does not establish real-model behavior or actual data
leakage. Current module-file hashing alone cannot identify an already-imported
function after its file changes; that conditional probe did not modify the audited
snapshot, and no such drift was observed in the release.

Evidence-script exit zero means reproduction completed, including failed checks.
Each report labels verified, failed and unverified boundaries. This old-release
package remains immutable when the infrastructure owner delivers fixes.

## Fix retest, runner and baseline controls

[20261115-007](../../../results/integration-audit/20261115-007/) retests source
`05c503e`. The six prior issue groups now pass the exact synthetic cases and
positive controls; root separately confirmed the reviewers' results. The current
v3 fixture also reproduces byte for byte. This scoped success does not establish
overall live readiness.

The same package reports five new runner gaps: mutable inputs/settings after
validation, cache hits after the relative wall-time cap, a missing-cost-mode
crash after claiming, incomplete build-input identity, and extraction settings
recorded differently from actual calls. Single-execution claims, uncertain-call
no-retry behavior and the saved runner fixture's integrity checks pass. The
coordinator has the reproductions and infrastructure owns the fixes.

[20261115-008](../../../results/integration-audit/20261115-008/) verifies the first
role 05 baseline/control handoff at `675f6d2`: six saved payloads match, tested
no-profile/name-only controls exclude extra personal inputs, retrieval's adapter
binds context and option order, source spans/caps are exact, frozen content is
preserved, and the helper hash enters the policy digest. All 18 relevant tests
pass. Actual runner dispatch, regenerated artifacts on the integrated renderer,
real P1/DEV data and the later semantic release remain separate checks.

## Later pinned releases: semantic retrieval, runner and API accounting

[20261115-009](../../../results/integration-audit/20261115-009/) verifies seven
semantic-retrieval claims at `0ca54b4`, with one P3 numerical defect: subnormal
vectors can break cosine scale invariance. This is pathological-input robustness,
not evidence of actual provider misranking. The owner has the reproduction.

[20261115-010](../../../results/integration-audit/20261115-010/) retests the runner
at `c840615`. Full-document identity is fixed; four previous runner cases remain.
Old and new evidence are separate, with valid-input and rebound-input controls.

[20261115-011](../../../results/integration-audit/20261115-011/) audits the new API
adapter using mocked transport and synthetic-only environments. Shared limits,
concurrency and uncertainty holds pass; partial reported usage can be discarded
as zero. Full reservations remain held, and no budget bypass was observed. The
report does not verify current prices, availability or actual provider behavior.

[20261115-012](../../../results/integration-audit/20261115-012/) verifies the shared
runner's actual decision-binding route for all three retrieval method IDs. Exact
decisions reach the recording backend; changed context/order is rejected first.
Synthetic builders isolate routing; actual role 05 candidate rebuilding on the
combined release remains a separate integration check.

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
