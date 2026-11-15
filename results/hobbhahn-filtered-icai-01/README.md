# Filtered ICAI refit: no retained principles

Execution succeeded, but this is NOT a usable personalized profile for the environment pilot. No pilot was run. The empty usermodel.json is retained as an honest run artifact, not an approved replacement for the existing model.

85 retained history records preserve the old document-group split: 57 learning, 18 validation, 10 dev. Dev was not evaluated. Upstream held-out unchanged and not evaluated. Supplied reasons and filter judgments were excluded from extraction inputs.

Existing ICAI implementation from CODE_VERSION, GPT-6 Luna, 80 candidate clusters, three unanimous votes per rule/choice, correct/total >=10% and correct>incorrect, validation comparison of top 5 versus 10. No method or threshold changes. 228 proposals ->80 representatives ->0 retained. Best correct count 4/57; passing needs at least 6/57.

Cost: $0.127353905 conservative estimate. Stage elapsed time approximately 49.4 seconds, excluding setup/embedding overhead. No request retries or errors. Save/load verified. Raw votes independently reconstructed offline and match all stored counts.

4,356 of 4,560 rule-choice combinations were unanimously irrelevant; 105 had disagreeing repeat votes. Thus the failure is mostly limited applicability, not repeat disagreement. This does not distinguish overly literal extraction, weak inference, or genuinely incoherent/sparse preference data.

The empty-profile validation prediction got 2/18 choices correct. This is not a successful ICAI result or an untouched test result. Validation is heavily selected by the no-history filter, so this number is not comparable to the previous unfiltered benchmark.

## Candidate examples — all rejected by ICAI, not learned principles

Select the response that avoids explaining the slower overall rate through a single trend that decelerated over time, favoring distinct coexisting trends instead.

Correct 4; incorrect 0; irrelevant 53 out of 57 learning choices.

Select the response that preserves the underlying theoretical scaling account by explaining discrepant measurements as a measurement artifact, rather than treating them as evidence of a genuine scaling effect.

Correct 4; incorrect 1; irrelevant 52 out of 57 learning choices.

Select the response that prioritizes clarifying open questions and making them testable before choosing what to investigate, rather than starting from organizational goals.

Correct 2; incorrect 0; irrelevant 55 out of 57 learning choices.

Select the response that emphasizes uncertainty in cost figures from systems with limited transparency over accepting reported figures at face value.

Correct 2; incorrect 0; irrelevant 55 out of 57 learning choices.

## Reproduce

Use the existing runtime at git revision in CODE_VERSION. Run scripts/taste_refit_filtered_icai.py with --runtime-root pointing to that checkout, --kept to ../hobbhahn-history-filter-01/kept.jsonl, --split-manifest to original-split-manifest.json, --heldout to the original upstream heldout_timesplit.jsonl (hash check only), --output to a NEW run directory, and --max-usd 3. Supply OPENAI_API_KEY securely or use the hidden prompt. --plan-only performs no model calls.