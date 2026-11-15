# Retrieval decision binding through the shared runner

Pinned release `c840615c885464404147a1cdea12343569d331fc`. Nine synthetic cases
exercise actual `run_job -> prepare_payload/predict_profile` dispatch for
`lexical_retrieval`, `profile_retrieval`, and `semantic_retrieval`.

For each method ID, the exact bound decision produces one recorded call. Changed
context and reversed option order return `retrieved_profile_decision_mismatch`
before any call. Their recorded attempted-call counts and trace lists are zero.

The probe registers synthetic builders under those three IDs to isolate routing.
It does not rebuild the actual role 05 retrieval implementation or establish an
integrated candidate's selection behavior. Packages 008/009 cover the separate
owner adapter. Other runner findings and live readiness are not cleared by this
test. No real source, final label, API call or preference evidence was used.

`run-01/` preserves all nine job manifests/results/leases and expected synthetic
traces, plus exact source hashes and the probe command. All 160 pinned files stay
unchanged. Restore the archive specified by `source/AUDIT_SOURCE.json`, copy that
manifest to the snapshot root, and run `reproduce.py --source-root SNAPSHOT --out
NEW_OUTPUT`. Output creation is exclusive.
