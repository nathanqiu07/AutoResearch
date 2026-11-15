# Future runs count all input tokens

The future cost helper now adds cached input when it receives Inspect-normalized usage. If it receives a raw OpenAI Responses total, it uses that total once. The caller must name the format; ambiguous fields are rejected.

This uses the same saved rates as before. It does not estimate a provider-specific cache discount or replace an invoice. Original input and cache counts remain visible alongside the full input used for pricing and input bounds.

Failed, invalid and missing-usage calls retain their reservations. A later settlement cannot release those holds. The legacy helper now stops on missing usage, matching the matched-run helper. No model, provider route, seed, rate, generation setting or original run artifact changed.

The implementation is committed as `a2c384cdfc5168ebbbcbbbbb157d2cacbc2f054b`. It applies only to future runs. The live judge-only wrapper has new helper pins; archived wrappers and packets retain their original pins.

Verification:

- All 124 Petri tests passed, including 11 new accounting tests. All 816 repository tests completed successfully, with two skipped.
- Independent review passed 48 focused tests and replayed 48 saved OpenAI usage records offline. Both explicit accounting formats reconstructed the same full input totals.
- The old consumed packet was rejected under the new runtime. A fresh packet was prepared and verified without network access or a model client; its three prompts exactly matched the original prompts.
- All 213 original batch05 files and 26 old review-packet files remained unchanged. No lease was created and no paid call was made.

The preparation check is tied to the implementation commit above. A later documentation commit changes Git HEAD and therefore invalidates that sample packet under the strict runtime guard. This is a recorded offline check, not an execution request or reusable authorization.

[Independent code review](future-fix-independent-review.json) · [Offline packet checks](future-packet-verification.json) · [Petri test output](petri-tests.log) · [Repository test output](repository-tests.log)
