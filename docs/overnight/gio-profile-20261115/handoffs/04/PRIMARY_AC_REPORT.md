# Fresh P8 extraction: one usable profile, no new accuracy gain

**The only valid new profile, Neel/Sol, produced 14/14 correct predictions.** The matched Sol consumer already scored 14/14 with the saved Luna-derived P8 profile and with no profile. The new result therefore establishes no personal-profile accuracy gain. Three other new profile builds exceeded the fixed 8,192-byte cap and remain invalid; none was repaired or replaced.

The fixed configuration is `P8-c8192-explicit-only`, replicate 0, with the original sparse fitting sources and original 28 ordered target items. These are selected development comparisons, not a final test or a ranking of model sizes.

## Delivery and accuracy

StudyA pairs each extractor with the same consumer. Historical Luna predictions are reused with their original provenance.

| Extractor → consumer | Correct / planned | Valid / planned | Accuracy among valid | Brier, valid only |
|---|---:|---:|---:|---:|
| Luna → Luna, historical |27/28|28/28|96.4%|0.04205|
| Sol → Sol |14/28|14/28|100%|0.00164|
| Astra → Astra |0/28|0/28|unavailable|unavailable|

All 14 valid new Sol rows belong to Neel. Chris/Sol, Chris/Astra and Neel/Astra did not yield admissible profiles. Their missing predictions count as zero delivered-correct in the planned denominator; they are not observed wrong choices. Conditional 100% accuracy for Sol therefore describes half its planned panel.

The fixed byte-cap outcomes were Neel/Sol 7,193 bytes, Chris/Sol 10,442, Chris/Astra 10,181 and Neel/Astra 9,727. The native counting method is a UTF-8 byte upper bound, not provider tokenization. The cap failures measure delivery under this encoding rule; they do not measure preference-inference quality. All four build calls had known usage. The operative native rejection is `personalization_cap_exceeded`; this classification does not certify every other validation check.

StudyC preserves the full Luna/Astra extractor-by-consumer matrix:

| Extractor → consumer | Correct / planned | Valid / planned | Evidence |
|---|---:|---:|---|
| Luna → Luna |27/28|28/28|Historical alias of StudyA|
| Luna → Astra |28/28|28/28|Historical saved-profile consumer result|
| Astra → Luna |0/28|0/28|Unavailable parent profiles|
| Astra → Astra |0/28|0/28|Alias of unavailable StudyA slots|

StudyA has 84 logical rows and StudyC has 112. They overlap on 56 slots, yielding 140 unique execution slots. Of 84 newly planned descendants, 14 completed and 70 remain missing because of invalid parent profiles. The 56 completed historical slots add no calls or independent observations. Cross-view aliases must not be counted twice.

## Matched probabilities and limits

For the 14 Neel items at the Sol consumer, Brier loss was 0.0016375 with the fresh Sol profile, versus 0.0034643 with the saved Luna profile and 0.0127286 with no profile. All three were 14/14 correct. Raw evidence scored 0.0017214 and semantic retrieval0.0013071 on those same items. These descriptive probability differences do not establish reliable calibration or a generally best method.

All seven new reversal pairs were consistent and correct in both orders. They are seven underlying judgments from only two Neel source groups, not 14 independent judgments. Chris has one target source group and no valid new profile here. Perfect agreement and a degenerate descriptive bootstrap interval cannot overcome this small, selected panel or its generic-control ceiling. Different profile content, length, generation time and stochastic draws remain possible explanations for probability differences; model IDs establish no parameter-count ordering.

The crossed Astra-extractor comparisons are unavailable. The preserved historical cells show consumer behavior for the saved Luna-derived profile; they do not establish how an Astra-derived profile would perform. No substitute profile, repair, new target, repeat extraction or change to selection was used.

## Cost and verification

Four new builds cost **$0.36092** in known conservative recorded usage. The 14 new predictions cost **$0.085065**, for **$0.445985** combined. Historical aliases cost zero incrementally; earlier fitting, predictions and embedding production remain in their original receipts. These figures are saved usage estimates, not invoices or cumulative ledger balances.

Role04 verified exact completion, manifest, source, target schedule and profile bindings before opening the 14 new prediction bodies. The existing manifest-aware scorer used unchanged private development targets. A separate direct tally matched all 14 correct/valid results, Brier loss and seven consistent pairs. Prior private scored reports supplied historical aliases without reopening or rescoring their result bodies.

Role09's published completion-index review is closed through a separate immutable receipt: the source mapping, all four parents, 70 missing rows and both study views match the frozen preparation. That owning review covers code and safe metadata; it is not a second native execution audit. Original pending markers remain preserved in the initial score artifact. No API calls or final-test access occurred during evaluation.
