# Baselines and retrieval handoff

Role 05 owns only `baselines.py`, `retrieval.py`, their two test files and this directory. The coordinator owns jobs, the infrastructure owner owns the registry/runner, and the existing audit owner owns independent conditioning checks.

Call `register_baselines()` from `autoresearch.taste.overnight.baselines` once per process; no registry source edits are needed. Registration pins the baseline module and includes the retrieval module hash in the policy digest. All controls call the same neutral renderer. These modules fetch nothing and make no extraction calls.

| Method ID | Input and behavior |
|---|---|
| `no_profile` | Intentional empty personalization; researcher identity and source metadata remain outside the consumer payload. |
| `name_only` | Requires `researcher_name`; personalizes with that name only. |
| `raw_evidence` | Packs exact excerpts in document-ID/offset order. |
| `lexical_retrieval` | BM25 ranks approved excerpts against the decision context and options, then packs the top `top_k` (default 5). |
| `semantic_retrieval` | Cosine ranking from a separately produced, hashed embedding bundle. Without a valid bundle it is explicitly unavailable; it never substitutes lexical retrieval. |
| `memory_summary` | Reuses the exact content of the supplied frozen P1 artifact. Requires `summary_method_id`, `frozen_profile`, and `expected_profile_id`; does not independently generate another summary. |
| `profile_retrieval` | Preserves a supplied compatible frozen profile and adds lexical excerpts within the registered `profile_cap` and remaining passage cap. |

Use the shared `build_profile(documents, config, extractor)` entry point. Extra config fields are above plus `chunk_chars` (default 1200), `top_k`, and for retrieval `decision={context, options}` with no other keys and `consumer_identity={model, ...}`. The shared exact source allowlist is always checked. Excerpts include only opaque document ID, start/end character offsets and text; URLs/titles/labels/arbitrary metadata do not enter personalization.

Chunking uses fixed nonoverlapping character windows, trims exterior whitespace while retaining offsets, and deduplicates exact text. BM25 uses Unicode word tokens, case folding, k1=1.5/b=0.75. Ties use document ID then offset. Zero-match queries retain that deterministic order. Raw and retrieval use the same excerpt structure. If a full excerpt cannot fit, packing takes an exact prefix and adjusts its end offset. It never cuts the frozen profile. A missing source, empty usable evidence or infeasible allocation cannot silently become no-profile.

Caps include serialized JSON overhead and use **UTF-8 byte upper bounds**, matching contract v1. They are not measured tokenizer counts. Equal caps establish the same conservative limit, not exactly equal token usage. The retrieval cache identity includes exact source hashes, context/options in order, consumer identity, settings/config and retrieval implementation; no persistent cache is implemented here.

**Decision binding:** use `predict_baseline(profile, context, options, consumer, config)`. It rejects a retrieval artifact built for different context/options before invoking the common `predict_profile`. The infrastructure runner must call this adapter or enforce the same binding itself. A global frozen summary can be reused across decisions. A retrieval artifact must be rebuilt per decision. Neither path conveys calibrated confidence.

Own/swapped/shared comparisons must be registered by the coordinator with evaluator-approved target/peer bundles and matched caps/settings. These builders do not invent peer data or silently relabel a foreign artifact. Missing peer evidence means the corresponding arm is unavailable. P1 generation belongs to its existing owner; this lane records the original P1 fit usage separately from zero-cost reuse.

Run the offline synthetic packet from the repo root:

```sh
python3 docs/overnight/gio-profile-20261115/handoffs/05/fixture.py --output /tmp/baselines-fixture-unique.json
python3 -m unittest tests.test_overnight_retrieval tests.test_overnight_baselines
python3 -m unittest discover -s tests -t .
```

Fixture probabilities are scripted plumbing evidence, not preference scores. Output paths are exclusive. No live model calls, real researcher corpora or final labels were used for this implementation milestone. Live evidence follows only after DATA_READY and a coordinator-assigned job.

## Semantic extension

`embedding_inputs(documents, config, decision)` gives the exact ordered input strings for a separately leased embedding operation: canonical context/options JSON first, then approved chunks. `make_embedding_bundle(..., model, vectors, usage)` records vectors from that operation. `rank_semantic` revalidates the bundle's exact chunks, source manifest, query/options, model, dimensions, implementation and hashes before cosine ranking. Query and document vectors must be from the same call/model settings. Prefixes/normalization cannot be silently introduced.

The builder requires `embedding_bundle`, `embedding_bundle_sha256`, `embedding_model`, and `embedding_dimensions` in its frozen config. Bundle vectors never enter the consumer prompt; only the selected original source spans do. Zero vectors, nonfinite values, dimension/count mismatches and malformed provenance are unavailable inputs. Live bundles require a producer job ID and raw response hash. These consistency checks do not authenticate a claimed provider: the producer must retain its actual request/response evidence.

Builders still make zero model calls. `fit_usage.embedding_production_usage` preserves separate embedding-production usage; the coordinator should charge its producer job once, not again for every reused arm. No live embedding job has been executed here. The optional API candidate is [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small), listed at $0.02 per million input tokens when checked November 15, 2026. Its [endpoint schema](https://developers.openai.com/api/reference/resources/embeddings/methods/create) supports batched strings and explicit float output. Account availability and the coordinator's allocation must still be checked before use.

Add `--semantic-fixture` to the fixture command to exercise all seven controls with artificial vectors. This remains synthetic plumbing evidence and is never an embedding-quality result.
