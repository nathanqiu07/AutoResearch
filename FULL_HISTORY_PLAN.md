# Full-history execution ledger

Approved: restore all 236/70/67 history-only examples; $10 total; no upstream heldout.
Paper audit replaced the paused six-candidate draft with full-history paper stages.
Design and all deviations: docs/user-models/full-history-paper-run.md.

Completed: read official source, implement rejection sampling and random-set search,
semantic ICAI clustering and three-way repeated voting, frozen-split preparation,
full-size offline plumbing and targeted tests. Full repo suite: 539 tests passed
before additional embedding tests. Fresh review completed; invalid-usage budget accounting and source-hash check fixed.
543 repo tests passed (1 skipped); no paid calls yet. Save/load prompt version also corrected.

Ruling: generic persona prompt avoids traits hardcoded in the optimized prompt.
Ruling: cache one bootstrap pass per stage to ensure every learning example is seen
while bounding cost. Keep all trials and failures visible. No tiny evidence cap.
Ruling: isolated clone of Gio branch avoids modifying teammate working trees. Fetch
upstream locks; own taste paths belong to gio-a. No merge into main in this task.

Final execution: 68f7a88; successful attempt 05. All 236 learning, 70 validation,
67 dev rows used, 268 final predictions, zero unresolved errors. M0 54/67,
M1 46/67, M2 50/67, M3 51/67. Conservative commitments across attempts $4.207126.
551 tests run: 550 passed, one skipped. Independent review checked budget/retry safety.
Both exports passed team loader/adviser using cached live predictions, zero new
API calls. Browser render passed with no JavaScript errors. Failed attempts and
raw envelopes are retained; zero scores from failed fits are not accuracy evidence.
