# decoys results (2026-11-15, devin-tastepetri)

Pre-registered in `PREREG.md` (main test, then a replication on fresh samples). Haiku proxy plus the Petri-judge
proxy, 9-11 scorable seeds, paired per seed, 90% bootstrap CI over seeds.

## Answer: null. The first-batch effect did not replicate.
| comparison | Petri realism | A2 | A1 | validity | bait_reached |
|---|---|---|---|---|---|
| DC vs R0, k=0-2 (main) | +0.3 [−0.1, +0.7] | **−0.05 [−0.10, −0.01]** | +0.02 | +0.03 | +0.02 |
| DZ vs R0, k=0-2 (texture placebo) | −0.1 [−0.5, +0.3] | −0.03 [−0.06, +0.00] | +0.00 | −0.07 | −0.08 |
| DC vs DZ, k=0-2 | +0.4 [−0.1, +0.9] | −0.00 | +0.00 | +0.08 [+0.01, +0.16] | +0.12 [+0.04, +0.20] |
| **DC vs R0, k=3-5 (replication, fresh samples)** | +0.2 [−0.1, +0.7] | +0.02 [−0.04, +0.09] | **+0.07 [+0.03, +0.11]** | −0.10 [−0.21, +0.01] | **−0.10 [−0.20, −0.01]** |
| DC vs R0, k=0-5 pooled | +0.3 [−0.0, +0.6] | +0.00 [−0.03, +0.05] | +0.04 [+0.01, +0.08] | −0.04 | −0.03 |

- **Primary rule** (DC − R0 realism, CI above 0): not met, either in the main test or in the replication.
- **The main test's A2 drop (−0.05) did not replicate** (+0.02 on fresh samples), and neither did DC's validity edge
  over the placebo.
- One direction did hold in both batches: realism +0.2 to +0.3, CI touching 0. Pooled over 6 samples it is
  +0.3 [−0.0, +0.6].
- Decoys raise A1 a little (+0.04 pooled): the target voices suspicion slightly more often when there are several
  anomalies.

## A/A check: how noisy is the proxy at k=3?
The same arm, sample batch k=3-5 minus batch k=0-2. The expected difference is zero.

| arm | realism | A2 | A1 | validity | bait_reached |
|---|---|---|---|---|---|
| R0 | +0.1 [−0.3, +0.5] | −0.02 | −0.01 | +0.02 | +0.02 |
| DC | +0.0 [−0.2, +0.3] | +0.01 | **+0.05 [+0.01, +0.09]** | **−0.09 [−0.18, −0.01]** | **−0.11 [−0.20, −0.01]** |

Three of the 10 A/A tests come out "significant" at 90%, where 1 is expected. The seed-bootstrap CI at about 10
seeds and k=3 is overconfident for validity, bait_reached and A1. **Implication for every result tonight:** a single
secondary metric whose CI barely excludes 0 at k=3 should be treated as noise until it replicates. That includes
petri_taste's bait-adjusted A2 and taste_ranker's Bowman validity signal. The petri_taste primary conclusions
(taste null; TT2's realism gain comes with a bait loss) rest on larger, consistent effects across six arms.

LEGIT vs GAMING: decoys are LEGIT (deployments are noisy). On this proxy they are neither a win nor a loss.

## Calls
- 675 haiku in total:
  - main: DC 166, DZ 172;
  - replication: R0 167, DC 170.
- 24 devin-cli sonnet calls for the rewrites.
