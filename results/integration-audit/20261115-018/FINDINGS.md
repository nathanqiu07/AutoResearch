# Released pilot metadata audit 018

Independent reviewer role: `/root/parallel_gap_audit`. Read-only audit on 2026-11-15; no project code execution, transport calls, environment/credential access, private evaluator labels, or owner-file edits.

**The corrected reader verified 1,007 metadata/hash assertions with zero failures (run-02, exit 0).** The released records support **34 recorded calls: two rejected P1 extraction outputs and 32 completed control predictions**. The selection called for 40 predictions plus two extractions. The eight P1 predictions are absent because both P1 profiles are invalid with `invalid_source_span`; this remains incomplete planned coverage. The API transport traces for those extraction calls completed, so these profile failures are distinct from uncertain API outcomes.

The results cover 16 build jobs (14 complete, two invalid) and 14 prediction jobs (32 prediction rows, all complete). Each of the four executed controls covers the same four selected ordered decisions for each of the two researchers. There are 68 recorded trace files, paired as started/completed for 34 attempts. No recorded uncertain attempts, retries, or cache hits appear in these jobs. The sum of per-job reported estimated cost is $0.0082642; this is not an independently verified provider invoice.

The three explicitly released entry files match their pinned byte hashes:

- Build prepared metadata: `ec7278a07e0fe0b2033fcda325de1d0e071d14571ad573c396b4a7b00222a3f0`.
- Prediction prepared metadata: `4dfcaccb489ce152f97d01e8321eed4898ec17c6723858723edf3de2914c900a`.
- Completion index: `6fadfd0466ec959b1cbc5bb6852a135e604834aefd2cdadcb7a7cbb2ad922fb6`.

For all jobs, packet file hashes, semantic job IDs, saved manifests, exact claimed leases, configuration hashes, result/index links, source/document hash chains, profile hashes, and trace hashes match. Started trace identities/settings match the declared backend and configuration. Completed trace response hashes and prediction cache-key links match. Selected item/order hashes agree with the approved label-free development release. All read input files remain byte-identical after the read.

Declared settings are gpt-6-luna with medium reasoning, extraction maximum output 16,384, consumer maximum output 8,192, and declared temperature 0.0. The backend identity records temperature as not sent. This metadata audit does not authenticate actual provider request parameters. Runtime SHA `0dcd4b43b82a5a271d195e0bcc6b67695281f37c` agrees across records; source bytes and loaded-process provenance are a separate audit.

The first reader run incorrectly assumed every build carries an empty item list. Eight lexical-retrieval builds correctly carry one selected decision/order. `run-01` preserves the eight failed audit assertions and exact old reader. The corrected assertion hashes the exact selected inputs and schedule for all builds; no owner artifacts changed. These were audit-script errors, not pilot defects.

An exploratory tool invocation accidentally printed nested approved public fit-source text while inspecting a release schema. No private labels or credentials were accessed. The saved audit package contains no source, profile, decision, prompt, or response text. The durable reader emits only allowlisted metadata, hashes, counts, settings and statuses. Raw evidence remains in the original coordinator paths; this audit does not duplicate it.

Scope limits: no prediction scoring, researcher-fidelity claim, provider authenticity/availability verification, invoice verification, or source-span interpretation. Conditioning and span semantics are separately owned by audit 019. Recorded calls mean backend/runner attempt counters paired with traces; no independent physical HTTP/provider request log was available here.

Evidence:

- `read_metadata.py`: standard-library-only reproducible reader, with coordinator-root restriction and filename category guard. It never follows environment/private-label fields or imports the project.
- `run-02/report.json`: corrected complete assertions, sanitized per-job/trace records, hash inventory, scope and limits.
- `run-02/invocation.json`, `stdout.txt`, `stderr.txt`, `reader-used.py`: exact invocation, isolated environment, exit status, output and script version.
- `run-01/`: preserved initial failed assertions and script version.
- `input-inventory.json`: `pilot-audit-input-inventory-v1`; `files` is a list of objects with absolute `path`, byte `sha256`, and `size_bytes`. This is suitable for verifying the coordinator's separate private archive; it does not contain file contents.

Reproduce with a fresh output directory while approved coordinator paths are available:

```sh
python3 -I /tmp/gio-integration-audit-staging/pilot-runtime-18/read_metadata.py --out /tmp/gio-integration-audit-staging/pilot-runtime-18/run-03
```

Expected exit 0 and 1,007 verified assertions. Existing output directories are refused. Source paths and initial file hashes are deliberately pinned; relocation requires an explicit mapping and must preserve those byte hashes.
