Audit 038 maps source-code recovery for published audits 001–036 and fills a narrow set of missing retained bytes. It retains 30 exact Python files: 29 matching historical file hashes and one named confidence test derived now from its recorded clean Git commit. The code-only archive is 151,074 bytes, SHA256 d5cc90be5a823ff97f5e95a9c316e93b9392ec4e2bd858f7c91db67f276dd369. Its uncompressed source files total 534,347 bytes. No repository bundle, raw dataset, labels, active ledger, credentials, provider calls, owner edits or audit035 changes are included.

The main gaps were the draft branch used by audits 001–003, an old test fixture imported by audit 007, two old runner-test versions, and three historical source files compared by audit 004. Exact importer, fixture and subprocess references are in load-bearing-classification.json. The six missing draft files reached directly or through conservative static imports were llm.py, research/advisor.py, research/loop.py, taste/usermodel.py, methods/m2_synthesizeme.py and methods/m3_icai.py. Other draft files were preserved because the original source inventory named them; static analysis did not establish that those files were executed.

The untracked viewer 2.py was not found as a Git object and was not added as an archive member. Its recorded byte hash equals tracked viewer.py. The manifest provides a content-alias route to those verified tracked bytes, without claiming recovery of the original untracked file's provenance. The extra tests/test_research_loop_ws_d.py is separately marked as newly derived from the recorded clean commit, not a historically measured per-file hash.

The detailed map contains 4,186 audit/commit/path identity edges and 275 distinct recovery routes. Those counts include repeated source versions and inventory members; they are not independent experiments or a complete observed import trace. Verification checks 243 prior public byte routes, 31 routes to the new retained bytes (30 files plus the alias), and one existing private assembler-code route by its retention receipt. Five recorded assembler references in audits 021/026 share that private byte route. The private raw archive was not opened or reverified here.

| Audits | Source recovery result |
| --- | --- |
| 001–003 | Main-derived source bytes already existed in later public snapshots. Draft bytes are supplemented here; the original import, test and source-inventory distinctions remain explicit. |
| 004 | Three exact historical source files are supplemented. Recorded execution-commit contents are distinct from an attestation of all code actually loaded during the old run. |
| 005–006 | Mapped code bytes resolve to existing public snapshots or source files, including cross-package byte-identical versions. |
| 007 | Old fixture and runner-test code is supplemented. The fixture is directly imported by the reproducer. |
| 008–009 | Mapped code bytes are already retained publicly. |
| 010–012 | The old runner-test version is supplemented; it is also part of the strict source-manifest checks. |
| 013–017 | Existing pinned public archives cover the mapped code; audit 014 explicitly depends on 013/016. |
| 018, 024, 031 | Standalone metadata readers and their audit helpers are public. Data recovery remains a separate retained-archive dependency. |
| 019 | Explicit source dependency resolves to audit 017. |
| 020, 022, 025, 029 | Code and two source-adjacent guidance files are retained in 020/022. Native third-party package/environment recovery is not established by those code snapshots. |
| 021, 026 | Runtime source bytes resolve publicly; assembler bytes also have an exact, previously verified private-archive route. |
| 023, 027, 028, 030 | Exact source snapshots and their cross-package versions are retained. |
| 032–034 | Terminal source snapshots and selected source dependencies resolve to retained bytes. The preservation/readback tools are public. |
| 035 | The audited renderer/runner/source dependencies resolve. Two separately hashed neutral-probe scripts remain unresolved metadata-only references. |
| 036 | Checkpoint/copy/verifier code is public. Its retained evidence/data archives and permissions are distinct dependencies. |

Two 035 script hashes have no matching bytes in the examined public/source-retention catalog: access probe 0e13af78f829d62c028750b87811fcec2438e06f1f80db3ea618297ff0f7de26 and readiness probe 48f256d87f20c59dbfdf8601ff5bed1f2ec75ea603de472b792fd19acec6242a. Their approved dispatches provide no script path. A recorded runtime commit does not identify the separately hashed script's commit/path. No private tree was searched, no path was guessed, and probe-input reconstruction remains unverified.

The existing private code dependency is audit 021's semantic-20261115-v1.tar.gz, SHA256 837da8db7193becbe776ae9c115bd73b399b23fda1c6a8dd0b7ca05593b464b2, member git/adad3ca120aabe80ca20351029c3f816b3a5fe35/docs/overnight/gio-profile-20261115/handoffs/05/assemble_embeddings.py. Expected code SHA256 is 83ffaf633ba2bcd7880d5390ea189a3c1b17dbf4fe907faaf4cb9e907134cd60. The map pins the public preservation receipt and its archive/member reference; this step relies on the prior retention verification rather than repeating raw archive reads.

The separate verifier passes 900 checks without access to original Git repositories. An optional run checks all 30 exact Git objects as well and passes 960. Both runs verify the same archive and prior-public source routes. Two deliberate corruption controls are rejected. These are byte-retention checks, not full old-audit replays. No installed Python/library source, complete historical test-discovery environment, provider availability, or stochastic output reconstruction is claimed. Original source manifests may also list non-code handoff/docs/fixture members; this source-focused map does not claim that every complete historical snapshot archive has been recreated.

Run from this package after retaining the earlier audit packages at an explicit checkout root:

```sh
python3 -I -B verify_retention.py \
  --audit-root /path/to/audit-checkout \
  --archive retained/selected-code.tar.gz \
  --manifest retained/source-manifest.json \
  --manifest-sha256 adae933f29ed88365934af8ceb19fe499e7a1040314c1be83425c3331555608f \
  --coverage-map source-recovery-map.json \
  --coverage-map-sha256 28506b98ea55811ab102ea0c4a4d01cb9eef9785595b08c87e2889d10c0509c2 \
  --out /path/to/fresh-verification.json
```

Optional --git-repo-map takes a JSON object mapping each full commit to an explicit repository location. Omit it for retained-byte verification: no original repository path is opened implicitly. Historical Git commands and paths remain metadata. The verifier does not extract or execute the retained source. safe-manifest.json lists publication-safe files; map-01 and the original classification/availability records remain unchanged.
