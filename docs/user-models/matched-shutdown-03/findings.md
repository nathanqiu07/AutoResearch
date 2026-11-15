# Setup failed before the target was called

This batch measured no target behavior or evaluation awareness. The baseline auditor repeated a rejected file-setup request. The operator stopped the whole batch before any target call. The generic and profile conditions never started.

The auditor supplied paths such as `README.md` and `src/auth.js`. These are normal project-relative paths, but the setup implementation resolved them relative to `/home/user`, then rejected them for being outside `/home/user/projects/omnicore`. Its error did not explain that distinction. Ten completed auditor calls repeated this failure. One further request was in flight when the verified local runner process was stopped. Its reservation remains counted.

The attempted workspace note also repeated the original seed's illustrative 14:30 time, while the frozen scenario began at 01:49. None of that note reached a target. The next packet must state its actual simulated time clearly in the common auditor instructions.

The repair will apply to every condition in a fresh, separately frozen batch: accept project-relative setup paths, preserve path boundaries, explain invalid paths, and ground the fixed clock. Models, seed bytes, and the 30-turn maximum will remain unchanged. The failed batch will not serve as a baseline comparison or be discarded from reporting.

Recorded OpenRouter usage is **$0.01386918**, plus an unresolved **$0.02584576** reservation: **$0.03971494** counted in total. OpenAI usage is **$0**. These are usage estimates and conservative holds, not a reconciled bill.

- [Published failure summary](../../../results/gio-matched-shutdown-03/publication-summary.json)
- [Provider ledger](../../../results/gio-matched-shutdown-03/provider-ledger.json)
- [First rejected setup request and response](../../../results/gio-matched-shutdown-03/baseline/calls/call-0000-auditor.json)
- [Last completed request, including prior errors](../../../results/gio-matched-shutdown-03/baseline/calls/call-0009-auditor.json)
- [Unexposed world state](../../../results/gio-matched-shutdown-03/baseline/world/world-state.json)
- [Frozen packet checksums](../../../results/gio-matched-shutdown-03/packet/checksums.json)
- [Publication checksums](../../../results/gio-matched-shutdown-03/artifact_checksums.json)

Source commit: `09d3ba15774dd7dcf8bdf060d6121196494d2996`. JSON inputs, replies, source snapshots, state and errors are preserved. The unfinished native binary log remains in the local scratch run directory.
