# Gio's user-model track

Approved scope: user-model interface, shared PersonalRewardBench splits, M0–M7,
fidelity evaluation and export. No edits to measurement, research loop or orchestration.
Gio approved bounded core-stage adaptations of the papers on 2026-11-14.

## Decisions

- Follow `PLAN.md` §12.6: `Choice`, `Prediction`, `UserModel.fit(history, val)`,
  `predict(context, options)`, `artifacts()` and `cost`.
- Prediction receives text options without target labels. A model fits one person.
- Preserve upstream outer user partitions and inner conversation partitions.
  Do not randomly redistribute already partitioned conversations.
- Pin source rows and their digest in `data/prefdata/splits.json`. Never silently
  overwrite a different manifest. Raw downloads and experiment scratch stay in `runs/`.
- M0 sees no personal history. M1 sees a seeded subset (5, 10, 20 or all).
- M2 generates/validates hypotheses, synthesizes a persona and selects examples.
  M3 proposes, lexically clusters and reconstructs choices with principles.
  M4 learns the existing seven feature weights from label-blind text features.
  M5 combines M2/M3 and retrieves examples. M6 filters on validation data.
  M7 reserves separate calibration data before M6 fitting and calibrates probabilities.
  Describe search caps and adaptations in artifacts; never claim paper reproduction.
- Confidence is a probability of the predicted user choice, not experimental success.
  Mark raw probabilities uncalibrated. Export assumptions as tentative, never findings.
- Use an independent module CLI initially (`python3 -m autoresearch.taste`) to avoid
  concurrent changes to the shared CLI. Existing profile/loop behavior stays unchanged.
- Final evaluation is one registered comparison containing all selected methods,
  guarded by a single exclusive marker independent of output path. Failure consumes
  the attempt, with partial predictions retained; no silent reset/retry.
- Select methods on development users. Final users provide history/validation but
  their target labels never tune the method. Report datasets separately, user-macro
  accuracy, paired user bootstrap differences, Brier scores, failures and usage.

## Alternatives considered

Only using the current feature model is fast but requires a new text mapping and
does not implement the requested methods. Full paper reproduction is too large for
the time budget. Bounded adaptations behind the same interface preserve comparison
and allow later replacements without changing the consuming team code.

## Gates Gio controls

Model/provider, live-call budget and final-test launch remain undecided. Core code,
public-data loading and offline tests may proceed. Explain each milestone and any
change to split policy, method semantics, or comparison design before relying on it.

## Acceptance evidence

Tests must catch label leakage, cross-user/conversation split leakage, invalid model
outputs, reuse of final tests and false confidence. Scripted test responses verify
code paths only; they are not evidence of preference accuracy. Final conclusions
require real calls on untouched targets. Integration handoff is a callable exported
model; downstream research improvement belongs to the other workstreams.
