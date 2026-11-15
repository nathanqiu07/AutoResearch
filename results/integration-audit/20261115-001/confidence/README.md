# Offline confidence and fallback audit

This folder preserves the probes and evidence from an independent read-only audit.
No production source or policy was changed. No external backend was initialized or
called by the probes. Existing unit tests use their repository's offline fixtures.
No credentials, real final-test marker, or real final-test dataset were accessed.

## Exact sources and results

`run-01/capture.json` contains exact argv, working directory, stdout/stderr paths,
exit codes, Python version, script hashes, source hashes, before/after Git commits,
and tracked working-tree status. Both audited source sets stayed unchanged during
capture. `main_like` is a label for a historical integration checkout, not a claim
that it is the current remote main branch.

| Label | Repository | Commit | Probe | New regression tests | Existing tests |
|---|---|---|---|---|---|
| main_like | `/tmp/AutoResearch-gio-auditor-setup` | `0a541515f71e519cad0e4b0629336fd28cb509f0` | exit 0 | exit 1, expected RED | 48 passed |
| draft | `/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/AutoResearch-gio-draft` | `9616fe8a3c550664d8aae0b72c938d936c0a7347` | exit 0 | exit 1, expected RED | 41 passed |

The 57 probe records are identical across these source versions. Nonfinite values
are preserved as objects such as `{"nonfinite_float":"NaN"}`, so observations are
strict JSON. Full outputs are retained, including existing ResourceWarnings.
The new regression suite has eight test methods: seven failing assertions and
five errors across subtests, plus the passing valid-decision control.

## Reproduce

Use a fresh output directory. The capture command refuses to overwrite a run.
Each repository must be restored independently to the recorded commit and source
hashes for a historical reproduction; do not reset a live shared checkout.

```sh
python3 -B /tmp/gio-integration-audit-staging/confidence/capture.py \
  --output /tmp/gio-integration-audit-staging/confidence/run-02 \
  --repo main_like=/tmp/AutoResearch-gio-auditor-setup \
  --repo 'draft=/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/AutoResearch-gio-draft'
```

Individual commands, with `REPO` set to one checkout:

```sh
python3 -B /tmp/gio-integration-audit-staging/confidence/probe.py --repo "$REPO"
python3 -B /tmp/gio-integration-audit-staging/confidence/test_safe_fallback.py "$REPO"
```

The captured existing-test command was run with each checkout as cwd:

```sh
python3 -B -m unittest tests.test_usermodel tests.test_research_loop_ws_d
```

## Reproducible defects

1. **D1 feature outputs are not validated or gated.**
   `autoresearch/research/advisor.py:137-150` validates conversion and length, but
   accepts nonfinite, negative, and non-normalized vectors. It sets `usable=True`
   regardless of the configured threshold. A real profile with weight 0.2 produces
   `[0.5498339973, 0.4501660027]`, confidence `0.0996679946`, and usable advice at
   threshold 0.6. The method's documented behavior promises uniform fallback for
   low-confidence predictions. Proposed regression: invalid vectors return finite
   uniform scores, unusable advice, and an error; low-confidence finite scores
   follow the documented threshold. If feature profiles intentionally bypass that
   threshold, the owner must choose and document that policy rather than silently
   adopting the regression's expectation.

2. **Malformed profile values reach ranking.**
   A real `ProfileUserModel` with NaN or Inf weights emits `[NaN, NaN]`. The actual
   `OpenResearcher._d1` implementation creates NaN priorities at
   `autoresearch/research/loop.py:414-416`. This is not only a malformed mock result.
   The `actual_loop_d1_nan` probe records both scores and `all_finite=false`.

3. **Returned-prediction normalization can escape fallback.**
   `consult` catches `predict()` exceptions, but normalizes its returned object
   outside that handler (`advisor.py:106-117`). Choice `²` raises in `int()`, choice
   `İ` raises because lowercasing produces two codepoints, and a huge confidence
   or probability integer raises `OverflowError` during float conversion. These
   failures also escape `decide(..., decisive=True)`, since it consults first.
   Proposed regression: malformed returned data produces an auditable fallback;
   decisive evidence retains the supplied default without crashing.

## Intentional limits and policy choices

- `calibrated=False` and `True` currently behave identically. This was already a
  documented limit; this audit does not introduce a calibration requirement.
- Empty text profiles send no principles, persona or examples but still invoke
  the generic preference predictor. A valid scripted 0.9 prediction remains
  usable. An empty feature profile instead returns uniform D1 scores, although it
  records option zero as a usable choice with confidence zero. Explicitly label
  these cases in comparisons; they are not the same intervention.
- Confidence 2, positive infinity, and boolean true become 1; negative confidence,
  NaN and negative infinity become 0. Numeric strings are coerced. This permissive
  normalization deserves an explicit owner decision, not an unapproved policy fix.
- An invalid optional distribution normally becomes `None`, then D1 derives a
  vector from confidence. Boolean and numeric-string distributions are accepted.
  Rejecting all such cases would change existing behavior; the RED tests only
  require the overflowing case not to crash.
- A duck-typed result with choice A but probabilities `[0.1, 0.9]` favors A in
  ordinary decisions and B in D1. The normal core predictor derives choice and
  confidence from validated probabilities, so it cannot produce that mismatch.
- Core prediction parsing rejects nonfinite, negative, boolean, string,
  mis-sized and non-normalized probabilities. A huge integer raises OverflowError,
  but the adviser catches it when it originates inside the core `predict()` call.
- Valid decisive decisions preserve the default. The passing regression control
  confirms this; malformed returned objects are the exceptional failure path.

## Files

- `probe.py`: deterministic behavior matrix and real profile/ranking probes.
- `test_safe_fallback.py`: proposed regressions, deliberately RED on these sources.
- `capture.py`: reproducible runner and evidence capture.
- `findings.json`: machine-readable classification of findings and limits.
- `run-01/capture.json`: exact provenance and executed commands.
- `run-01/{main_like,draft}/observations.json`: full strict-JSON observations.
- `run-01/{main_like,draft}/*.stdout.txt` and `*.stderr.txt`: retained outputs.

The tests are an evidence artifact for the integration owner, not a production
change or an assertion that all new policies have been agreed.
