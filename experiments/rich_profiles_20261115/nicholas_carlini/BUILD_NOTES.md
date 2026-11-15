# Build notes: Nicholas Carlini rich profiles (full-corpus v2)

- These notes replace the v1 selective-source notes. v1 (selective sources, plus EVIDENCE_SELECTION.json) is kept in git history at d420d1e6.
- Corpus frozen at source commit d4c18edad437b46bc57b0b58b2efc4bae0fac100: all 167 files in data/researchers/nicholas_carlini/corpus. Every file is listed in full_corpus/sources.json and full_corpus/coverage.json. SOURCES.json is a short index of the same catalog.
- Pipeline (build/synthesize.py): reuse verified extraction evidence, then source capsules in independent batches over disjoint packets, each checked for exact packet and evidence-ID coverage. Next, merge the complete capsule inventory for this researcher into each of the five method prompts. The five profile calls are independent; there is no sequential profile updating.
- Model calls: gpt-6-astra (reasoning effort high). The Codex CLI ran out of quota partway through, so the remaining capsule batches and all final profiles went through the OpenAI Responses API via build/codex_api_shim.py. The shim is a drop-in replacement for the codex executable and keeps the call.py receipt format (events.jsonl, turn.completed, result hashes).
- Validation (build/validate.py, written to ../validation.json) passed. It checks exact provenance and full-input transport only, not semantic correctness, exhaustive reading, or preference-prediction validity.
- Coauthored findings are kept separate from individual testimony. Profiles are inferred models of research judgment, not researcher-endorsed statements.
- Word counts use whitespace splitting; citation-excluded counts strip bracketed source IDs first (see ../profiles.json).
