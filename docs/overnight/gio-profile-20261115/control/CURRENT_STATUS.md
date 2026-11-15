# Overnight campaign checkpoint

Updated 2026-11-15 at 13:00 UTC (5:00 a.m. Pacific). This is a running checkpoint, not a final result. Work remains bounded by 9 a.m. Pacific. The final test is not authorized.

## Running

- The untouched richer-profile continuation has completed all 204 jobs and 672 requests with known accounting, at an estimate of $0.124590125. The evaluator is scoring the richer-source comparison. Earlier unknown requests, incomplete job tails, and their budget holds remain excluded.
- The 31-user recorded response-preference reference queue is running. Its first two users completed, allowing the remaining queue to use two workers. Five earlier unknown requests remain excluded. This reference measures conversational preferences, not research choices or downstream utility.

## Ready and under review

- All 112 local scaling packing jobs completed with zero API or embedding calls. Independent checks reconstructed every profile, verified all 560 selected passages, and matched the rendered contexts to the original Luna controls.
- The first scaling comparison has 420 planned rows: 280 new request slots and 140 reused Luna rows. There are 278 distinct new inputs because two lexical/semantic pairs have identical inputs. They remain planned paired repeats, and the later call requires a known result from the earlier one.
- Scaling will use a separate $80 limit on actual estimates plus active holds. All future maxima sum to $82.1441, so completion under that limit is not guaranteed. The fixed order is Sol, then Astra, with profile/no-history/raw, lexical, and semantic batches checked separately. The separate $80 ledger is initialized, but paid scaling has not started.
- The original eight-user M4/M5/M6 extension is approved for offline implementation only. It retains 228 planned cells, 176 currently attemptable cells, 18 conditional cells, and 34 unavailable cells. Its proposed $2.20 allocation is not yet issued. This is an exploratory follow-up.

The accepted own/swapped/shared profile diagnostic is still deferred. Root will assess it after the first scaling tranche; existing own-profile and reference runs do not stand in for it.

## Closed or limited findings

The paid downstream lane is closed. The three additive reviews passed citation checks and still found no observed shutdown interference; major realism problems remain. They do not show a profile benefit. An offline compatibility check also found that the existing downstream adapter cannot load the selected Neel/Chris P8 profiles; its completed paid pilot used a Hobbhahn M2 profile. No new adapter behavior was added. The audit found omitted cached input tokens in saved cost estimates. Owners are adding corrections using the same saved rates while preserving original ledgers. These estimates are not provider bills; funds remain reserved pending reconciliation.

The new two-researcher retrospective-choice panel remains unavailable. Its four candidate sources do not establish the required independent personal choices; none was admitted.

## Controls and evidence

The project-wide limits remain $500 OpenAI and $500 OpenRouter, including prior spend. Root controls allocation and dispatch; profile and reference lanes each allow at most two calls at once. Prediction tools remain disabled. No unknown request is retried.

The active scientific runtimes remain frozen at f6cd4fb (profiles) and 63a2c21 (reference). Exact diagnostic and scheduler source copies, offline tests, and review receipts are retained in `runtime-snapshots/reviewed-live-20261115-v1/`. The integration branch passes 929 tests with two skips. Shared main received only timestamp updates to 73 ownership records for 11 campaign owners after its 809-test suite passed with two skips.

Detailed artifact hashes, ownership decisions, and changing run state are in `PEER_REQUESTS.md`, `RUN_POLICY.json`, and the immutable per-run receipts they reference. Completed runs and supported scientific conclusions are separate.
