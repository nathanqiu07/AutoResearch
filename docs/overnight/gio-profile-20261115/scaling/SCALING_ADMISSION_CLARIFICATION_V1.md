# Additive clarification: request hash conventions

This note narrows the collision interpretation of handoff 0006 and the selected-scaling readiness
report `ec31be71a741cfe4c986ff5f0183a3f7c6045418aef69ba9ee25c7ac382c2b94`.
The prior artifacts remain unchanged. **The report's zero matches do not establish absence of
collisions with all nine provider-unknown requests.** Mechanical preparation is still distinct
from live admission.

The helper emits `wire_request_sha256 = digest(body)`: compact, sorted, BODY-only JSON. The recipe
compares those hashes directly with the combined nine-entry list. Per the coordinator's discovery,
that list contains two conventions: four profile requests use this BODY-only convention; five
reference requests hash endpoint-plus-body JSON using default separators. Comparing those five
hashes directly with BODY-only hashes does not test request equivalence. The separate wire-byte
hash field also does not establish the missing endpoint-plus-body comparison.

A fresh metadata-only check verified the original four-profile denylist
`/private/tmp/gio_profile_unknown_requests_1154_v1.json`, SHA256
`11ace3c15bf90f04678a66d99b73b85074b827875f735c7d05664428393b4345`, and the published report hash.
Its four hashes are contained in the combined list
`8804a408fd50f1617f4a4004b05d7a6453fc94b16b30e7fca061d6548d977750`.
The 12 ready new prediction packets expose 168 distinct BODY-only identities; **zero match those
four profile identities**. This is the full proven static scope. It is not a reference-request
clearance, a current provider-health claim, or permission to execute.

The following remain pending the existing infrastructure owner's reviewed v3 admission checks:

- Normalize and compare both hash conventions using the owner's verified actual endpoint/body
  information. Role09 has not fabricated endpoints or created a competing wrapper.
- Check each actual future extraction and each consumer request after its profile/packing
  dependency resolves. New job or profile IDs do not establish a new outgoing request.
- Keep any collision unavailable and retain the original uncertain request evidence. Admit a new
  request only with the coordinator's current collision, spend/holds, deadline and lease checks.

The immutable f6 runtime, adopted selection, original profile/source artifacts, compiler/helper,
recipe, packet files, prior handoff and prior review records are unchanged. The historical recipe's
`new_request_collision_count: 0` must be read as a BODY-only string-set result, **not** as combined
nine-request admission approval. This note is the required interpretation until the owner's exact
normalized v3 proof is supplied and separately pinned.

The completed general review covered code, mechanical bindings, finite ceilings and safe metadata.
Its combined-list zero-match observation had this same convention limitation. Role05's baseline
review did not approve continuation or denylist proofs. Neither review authorizes execution. All
201 preparation checks, original alias counts, cost/time limits and zero-call claims remain as
previously reported; this clarification changes only the scope of the collision claim.

Validation: checked the unchanged helper/recipe lines, verified the three exact metadata-file
hashes, and recomputed the four-profile intersection. No source/decision/profile text, target
labels, provider, or live ledger was accessed. No code changed, so the prior 892-test result is
retained without rerunning unchanged tests.
