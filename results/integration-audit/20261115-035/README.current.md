Audit 035 verifies the saved provenance and accounting of 96 broad extraction cells: 48 complete, 39 invalid, 7 empty, and 2 unavailable. The original 78 dispatched results remain separate from six later continued jobs and 12 P7 builds. Recorded extraction status is not a measure of profile quality or researcher fidelity. Caps 512, 2048 and 8192 bound canonical serialized personalization content in UTF-8 bytes (utf8-bytes-upper-bound-v1); tokenizer counts were not measured. See cap-unit-note.json.

The original 47-file safe manifest and every indexed byte remain unchanged. Its README.md and FINDINGS.md describe the original audit state. This current note adds completed private retention, recovery, independent review, and the later two-record dispatch check. The top-level checksums.json covers all published evidence except itself.

The two non-overlapping frozen ledger scopes contain 82 original attempts and 19 continuation attempts: 101 recorded attempts total, comprising 96 builds and five side calls. The target6 summary's 7 attempts are an intermediate cumulative snapshot already included in the later 19; do not add them again. Known estimates across these two scopes total $0.103992940. The $0.019078625 retained uncertain holds remain separate. This is a reconstruction of saved scopes, not a current campaign total, invoice, or broader spending authorization.

Both unavailable builds retain null input/output usage and their original result hashes. The preserved hold total and exact uncertain reservation records agree with the frozen stop snapshot and continuation authorization. No per-job canonical provider-request join was reconstructed for those uncertain builds. The predecessor is stopped with holds, not reset or closed.

The new private phase2-build-coverage-20261115-v1.tar.gz stores all 500 exact inputs, including the earlier frozen registry snapshot and the public audit032 receipt. Archive SHA256 is d60e29dcc2cdd3446ce9e805f3ddffd58b2a5b2d76fc5fd57880ceea8e0ca155. The preservation receipt is private-preservation.json, SHA256 92a3e1900093ab1f41f5f73ecccc09ae7c6c6bee519f115f8e9527f06494af62. The preserver checked each pinned read_path before and after capture; it did not substitute the later mutable registry. All 500 members were recovered to fresh private paths. Both the agent and root replays reproduce the frozen 3,351-check report byte for byte, with 92 freshly recovered and verified source files. Logical input paths, roles, entry points and the input-set digest are preserved; only read_path values change.

This full recovery copy does not make all 500 files new evidence. The overlap map ties 373 inputs to audit032 receipt records, one to the public audit032 receipt, and 126 to records outside that receipt. The exact original source archive is public code only. Raw inputs and private replay trees remain outside the public package.

The independent review under independent-review/ found no blocker within the original scope. It checked 32 approved inputs, the 96-cell grid, original/continuation provenance, unknown outcomes and accounting; it did not run a second full reader. Its four in-memory negative controls are separate from the reader's 15 synthetic tests. Seven additional synthetic recovery tests check mutation, overwrite refusal, archive corruption, safe extraction and recovery without originals.

The later dispatch-binding/ addendum preserves two newly approved dispatch records in a separate two-member private archive, SHA256 2a056dc05c1747dac0f241e5580cfbc9410cfdb0ba3136bdf5a6471b2b1418fe. It passes 38 checks and five synthetic controls. Raw file hashes separately bind to canonical semantic dispatch hashes, ordered models, settings, allocations and saved usage. Those records contain no prompt/system text or script path; their script hashes match summaries but the script bytes are absent from the pinned 92-file source map. Probe input text therefore remains unverified. This addendum does not authenticate network traffic or close the uncertain-build request join. A separate bounded review of the addendum checks the four pinned data records and metadata bindings; it does not rerun the reader or its tests.

Private archives live in the Git-ignored runs/user-model-integration-audit/private/ directory, with mode 0600 and directory mode 0700. Exact receipts, inventories, readers, the recovery utility and source archive have durable private copies there; see durable-recovery-metadata.json and dispatch-binding/durable-recovery-metadata.json. Existing archives were not rewritten.

To recover and replay the 500-input audit from the repository root, choose fresh output directories:

```sh
python3 -I -B results/integration-audit/20261115-035/preserve_recover.py extract \
  --archive runs/user-model-integration-audit/private/phase2-build-coverage-20261115-v1.tar.gz \
  --receipt results/integration-audit/20261115-035/private-preservation.json \
  --receipt-sha256 92a3e1900093ab1f41f5f73ecccc09ae7c6c6bee519f115f8e9527f06494af62 \
  --out /path/to/fresh-private-inputs
mkdir /path/to/fresh-source
tar -xf results/integration-audit/20261115-035/source-f6cd4fb5.tar -C /path/to/fresh-source
python3 -I -B results/integration-audit/20261115-035/audit_coverage.py \
  --inputs /path/to/fresh-private-inputs/input-inventory.json \
  --source-root /path/to/fresh-source --out /path/to/fresh-report
```

Recovery and replay do not require original temporary input paths. Keep the extracted inputs private. The addendum README and exact invocation record describe its separate recovery. No model/API calls, credential reads, active SQLite reads, private labels, scoring, owner-code edits or runtime changes were made. Source/config identity and saved-record consistency are verified; source semantics, profile quality and provider authenticity are not.
