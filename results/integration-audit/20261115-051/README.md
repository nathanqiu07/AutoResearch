The relevant legacy logic is unchanged at local origin/main 7fa363d0e93bbfc623e1ee3bf773a2f663649c17. advisor.py is byte-identical to audit 001's main_like commit 0a541515f71e519cad0e4b0629336fd28cb509f0. Ten relevant function slices match both that snapshot and draft 9616fe8a3c550664d8aae0b72c938d936c0a7347. The full loop changed, but its load-bearing _d1 function did not; TasteProfile source also matches all three.

The public CLI still constructs TasteAdvisor in legacy model mode and passes it to OpenResearcher. Thus the old malformed/nonfinite-input issue remains conditionally relevant to that legacy route. This static comparison is not a new failing-run reproduction, nor evidence that a current run encountered it.

No selected P8/neutral-profile call into the legacy adviser is demonstrated by this pinned tree. The named autoresearch/taste/overnight and scripts/gio_petri directories are absent, and the explicit legacy loader/factory supports version-1 M0–M7 artifacts. This does not establish the behavior of a separately pinned P8 runtime or external adapter.

Keep the legacy finding open at its correct scope. Rerunning the unchanged historical reproduction would add little here. To decide P8 reachability later, use the exact selected runtime's public consumer commit/entrypoint; do not infer either contamination or a fix from an unrelated passing suite. No private artifacts are needed for that source-level question.

Only the published confidence README, exact relevant public Git blobs, explicit call sites and targeted tree metadata were inspected. No tests, submitted source imports, runtime outputs, private data or credentials were read or executed. All outputs in this review are newly authored metadata and notes.
