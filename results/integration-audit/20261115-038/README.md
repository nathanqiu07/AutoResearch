Audit 038 retains missing source bytes needed to reconstruct parts of audits 001–036. The original supplement contains 30 Python files: 29 that match historical file hashes and one named confidence test derived now from its recorded clean Git commit. A later, separate supplement retains two explicitly released neutral-probe scripts. Both archives contain code only. No private raw evidence archive, dataset, labels, credentials, active ledger or provider call is included.

The original map contains 4,186 audit/commit/path edges and 275 distinct recovery routes. Its 243 prior-public routes, 31 new-file or content-alias routes, and one private receipt-only route all resolve at the stated level. The private assembler archive was not reopened; that route relies on its pinned prior retention receipt. These inventory counts include repeated versions and files not established to have run. They are not a complete observed import trace or a claim of full historical replay.

The main gaps and load-bearing distinctions are documented in [README.original.md](README.original.md), [load-bearing-classification.json](load-bearing-classification.json) and [source-recovery-map.json](source-recovery-map.json). The original map and its then-unresolved probe-script classification remain unchanged. The untracked `viewer 2.py` has only a content-equivalent route to verified tracked `viewer.py`; its original provenance was not recovered. The extra confidence test is marked as derived now from a recorded clean commit, not a historically measured per-file hash.

The later [probe-script addendum](probe-script-addendum/README.md) closes recovery of the exact two script-byte hashes cited in audit 035. It also binds each module-level literal `PROMPT` hash to the corresponding saved-call prompt hashes, through the frozen audit 035 report. It does not establish immutable Git membership, full request/system reconstruction or authenticated provider execution. Audit 035 and the original 038 evidence are unchanged.

The main verifier passes 900 checks without original Git repositories, and 960 when the 30 explicit Git objects are checked as well. Root independently repeated the 900-check run from a recovered public evidence tree. Two deliberate corruption controls are rejected. The separate probe-byte verifier passes 32 checks, and the static literal checker passes 16 checks covering all three recorded calls. Three synthetic AST controls pass, including rejection of dynamic expressions and ambiguous reassignment. These are retention and metadata-binding checks, not historical workload replays. Installed dependencies, native third-party packages, runtime environment, provider availability and stochastic output recovery remain separate requirements.

The two new archives retain 32 files totaling 556,193 source bytes:

| Archive | Files | SHA256 |
| --- | ---: | --- |
| `retained/selected-code.tar.gz` | 30 | `d5cc90be5a823ff97f5e95a9c316e93b9392ec4e2bd858f7c91db67f276dd369` |
| `probe-script-addendum/retained/probe-scripts.tar.gz` | 2 | `762133227fb664f14aac88957453104552d11f80b569f5b2cb2c5df195e90058` |

Run from this package, with the earlier published audit packages available under an explicit checkout root:

```sh
python3 -I -B verify_retention.py \
  --audit-root /path/to/audit-checkout \
  --archive retained/selected-code.tar.gz \
  --manifest retained/source-manifest.json \
  --manifest-sha256 adae933f29ed88365934af8ceb19fe499e7a1040314c1be83425c3331555608f \
  --coverage-map source-recovery-map.json \
  --coverage-map-sha256 28506b98ea55811ab102ea0c4a4d01cb9eef9785595b08c87e2889d10c0509c2 \
  --out /path/to/fresh-source-verification.json
```

The optional `--git-repo-map` is a JSON object mapping full commits to explicitly supplied repositories. Omit it to verify retained bytes without original repositories. Historical commands and machine paths remain metadata, not implicit recovery dependencies. Both verifiers read archive members without extraction or execution. The addendum README gives its portable verification command.

[main-safe-manifest.json](main-safe-manifest.json) preserves the 26 original safe files. [safe-manifest.json](safe-manifest.json) is the current publication allowlist, including the separate addendum and root verification metadata. No shared documentation, owner source, runtime configuration or existing audit package was changed.
