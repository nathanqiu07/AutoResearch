# Audit 049: coordinator copy verification

The coordinator's local snapshot contains exactly the 27 payload files allowed by audit 046, plus five snapshot metadata files. All 27 copied payloads match the approved SHA-256 and size tuples. All 32 local files also match immutable Git blobs at `fad097490d501719d1567bf07dc382faef413feb`. HEAD remained at that commit during the check, and snapshot-scoped Git status was clean. Remote publication was not checked.

| Scope | Files | Bytes |
| --- | ---: | ---: |
| Approved copied payloads | 27 | 175,124 |
| Snapshot metadata | 5 | 34,897 |
| Complete snapshot | 32 | 210,021 |

The payload inventory is 23 files under `source/` and four under `review/`. The five metadata files are `README.md`, `retention-proposal.json`, `audit046-retention-decision.json`, `copy-verification.json`, and `SHA256SUMS`. No additional files, directories beyond `source/` and `review/`, symlinks, or special files were found in the bounded inventory. The reader does not descend into unexpected directories or read unlisted bodies.

The decision was read from an actual Git blob at audit commit `74b21b4d73fc2ceea78034a4764c26d71899f152`, path `results/integration-audit/20261115-046/retention-decision.json`, and matched SHA-256 `8b965768fdbfe32a41c46b201ee1bfc9d443a5c1f647166fde2e6240757b17a4`. The coordinator's copied decision is byte-identical. The copied proposal matches the decision's proposal hash and the same ordered source/hash/size/destination tuples. The 27 lines in `SHA256SUMS` match the approved payload mapping exactly; that checksum file covers the payloads, not the five metadata files. The metadata files are separately hashed in the report and bound to the verified Git blobs.

`run-01/report.json` records 110 passing checks, the exact inventory, and all 32 Git object identities and byte comparisons. `run-01/git-read-commands.json` records each read-only Git invocation and its exit status, stdout hash/size, and stderr hash/size; source bodies are not exported there. `invocation.json`, `execution.json`, `stdout.txt`, and `stderr.txt` preserve the verification command and outcome. The report SHA-256 is `861407d9e189cb69e5936a0b52ab0dc38dc3d9f7de4d38f7dd21ae5dd4a8a730`.

The owning copy receipt says the originals were unchanged and original/destination bytes matched during copying. This audit checks those recorded statements for metadata consistency but does not independently re-establish current original-file equality: the original paths were not opened. The copied README's historical-source and limited-authority wording is consistent with the decision. Source semantics, prior test outcomes, content eligibility, dependency closure, and scientific validity were not re-reviewed.

The verifier is parameterized by the two repository roots, immutable snapshot commit, and a fresh output directory. Its only source-body reads are the 27 approved destination files and the corresponding immutable Git blobs, used solely for hashing and byte comparison. It parses only the named decision/proposal/copy metadata and checksum text. No payload was imported, executed, semantically parsed, or copied into this audit stage. No embedded source/private paths, environment files, profiles, ledgers, labels, or imports were followed. There were no model calls or settings changes.

The local copy and Git-object binding close the concrete copy dependency. They do not by themselves prove a remote push, historical execution of these exact bytes, runtime portability, or complete recovery of their referenced inputs. Root owns remote confirmation and any publication addendum.
