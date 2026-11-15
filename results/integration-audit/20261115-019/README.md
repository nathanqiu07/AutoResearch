# Recorded first-pilot conditioning audit

The 32 recorded control requests match the frozen renderer applied to the exact saved profiles and selected decision inputs at runtime commit `0dcd4b43b82a5a271d195e0bcc6b67695281f37c`. This checks application-level recorded requests, not independently observed provider traffic or preference accuracy.

All four executed methods cover the same eight ordered decisions across two researchers. No-profile personalization is empty. Name-only personalization contains exactly the declared name. Raw-evidence and lexical profiles preserve exact source substrings and their declared 2048-byte cap. Recorded prompt, system/settings, rendered-profile/payload hashes and per-row cache provenance agree. The 14 distinct profiles bind the same approved document set within each researcher. There are no P1 prediction requests in this batch; audit018 verifies the two rejected builds and the eight absent planned predictions.

## Attributed spans and actual impact

Across the 14 distinct profiles, the ten raw/lexical profiles contain 20 passages. Eight passages cross an attributed-span boundary. Together they include 16 characters outside the union of permitted spans, all whitespace; there are zero non-whitespace characters outside that union. Counts here are across distinct profiles, not summed repeatedly over each prediction using a shared profile.

This is limiting evidence for the conditional difference in audit017: raw/lexical can use surrounding full-document content while P1 uses attributed spans. The contract gives spans attribution/citation meaning but does not unambiguously prohibit every other byte of an approved fit record. These actual records do not establish unauthorized substantive text, target-label leakage, or a reason to rerun the pilot. They do not prove the same property for future releases.

## Reconstruction without publishing source text

Only code, hashes, IDs, counts, statuses and preservation metadata are published here. Actual approved source/profile/decision/response text remains private. Root preserved all 252 input artifacts used by audits018/019 in a local Git-ignored archive, with directory mode700 and archive mode600. `private-preservation.json` records its exact local path, archive SHA256 and member hashes. It contains no credential file or private evaluator labels. The archive is not pushed to Git; retain it alongside the report if the worktree is moved or removed.

Archive SHA256: `643f92df856165bd6378fbfc7c292b170d505ba3ace6e64d349368b8ee16a806`. This is the archive hash, not the hash of the preservation receipt itself.

Every archive member was rehashed after extraction into a new directory. The reader then reproduced the same 32 request records, 14 profile summaries and eight matched decisions using recorded-root remapping. It reads only explicitly referenced JSON inside the supplied data root, never opens the packet's environment-file field, imports no API backend, disables socket/network access, and refuses to overwrite an output directory. Original-path and relocated results are retained separately. Earlier report wording requiring original paths is superseded by the demonstrated private-archive replay and the final reader.

The code snapshot is shared with package017: extract its `source/source.tar.gz` and copy `source/AUDIT_SOURCE.json` into the extracted root. Extract the private data archive separately. Then use a fresh output directory:

```sh
python3 -B reproduce.py \
  --source-root /path/to/code-snapshot \
  --data-root /path/to/private-data-copy \
  --recorded-data-root /private/tmp/gio-profile-20261115-coordinator \
  --prepared /path/to/private-data-copy/receipts/c0e41ac85c806548b007f47f6ad08a9564ffe75ca4cd5a0a207ef4d936d4051a/preparation/prepared.json \
  --prepared-sha 4dfcaccb489ce152f97d01e8321eed4898ec17c6723858723edf3de2914c900a \
  --out /path/to/fresh-sanitized-evidence
```

The recorded-data-root argument names the root embedded in the immutable packet; it is not a required current location. The published `input-hashes.json` files bind every private artifact the reader inspected. The private replay tree itself is deliberately excluded from this package.

## Evidence limits

No evaluator labels or scoring were inspected, and no model calls, source edits or settings changes were made. Source hashes and recorded-request agreement do not authenticate provider execution or establish researcher fidelity. The earlier probe's assumptions and source-policy interpretation are not treated as empirical proof. The audit is an automated independent check, not a human scientific review.
