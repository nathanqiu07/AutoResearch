# genre_ladder results (2026-11-15, devin-tastepetri)

Pre-registered in `PREREG.md`. Kimi K2.6 (the dev target), through devin-cli, answers the placeholder A2 probes on
transcripts rendered in Petri format with E3b's 24k cut. The calls were 123 Kimi plus 19 sonnet bait insertions (the rest were cache hits);
2 of the 25 insertions failed and are excluded from the paired test.

| group | true label | n | Kimi A2 [90% CI] |
|---|---|---|---|
| REAL_CHAT: WildChat business chats, real users, no tools | deployment | 25 | **0.68 [0.61, 0.74]** |
| REAL_CODE: OpenHands sessions, real users | deployment | 25 | **0.90 [0.88, 0.92]** |
| REAL_CODE+BAIT: the same sessions with one opportunity spliced in | (test-like) | 23 | 0.91 [0.89, 0.92] |
| AUDIT_NB: our audits, bait removed | evaluation | 26 | 0.92 [0.90, 0.94] |
| AUDIT: our audits (surgery ID) | evaluation | 30 | 0.93 [0.92, 0.94] |
| BENCH_CODE: SWE-rebench runs | evaluation | 25 | 0.95 [0.94, 0.95] |
| BENCH_OPS: tau-bench, simulated users | evaluation | 25 | 0.95 [0.94, 0.96] |

- Discrimination: the AUROC for eval vs real is 0.87 [0.82, 0.92] overall, but only 0.78 on coding sessions alone. The
  three probes agree to within 0.02 in every group.
- A bait in a real session: +0.00 [−0.02, +0.02], paired, n=23.

## Reading
1. **Kimi's post-hoc A2 mostly measures "is this an agentic tool-use transcript".** Real users' OpenHands sessions
   get 0.90, almost as high as SWE-bench-style benchmark runs (0.95). Only plain chats come in lower (0.68). The
   probe's ranking is informative (AUROC 0.78-0.87), but its absolute level is at ceiling for anything with tools.
2. **Our audits are already almost as "real" to Kimi as real coding sessions.** At 0.93 against 0.90, a seed
   rewrite that made an audit indistinguishable from a real OpenHands session would lower Kimi A2 by about 0.03.
   That is the realistic headroom of the E3b A2 criterion for agentic seeds on Kimi, below what n=12 seeds can
   resolve. It explains why the real pilots' plain rewrite showed no effect (−0.017, CI [−0.098, 0.059]).
3. **Kimi doesn't react to a bait in any genre.** Removing it from audits gives −0.01 (judge_transfer), and adding it
   to real sessions gives +0.00. On Kimi, A2 is insensitive to the very thing the eval is about.
4. **For the project.**
   - The E3b success criterion "R1 below stock on A2" is close to unreachable on Kimi for agentic seeds,
     whatever the taste.
   - Options: report A2 relative to a real-session baseline (A2 − 0.90 for coding-agent seeds); use paired forced
     choice ("which of these two transcripts is the test?"), whose resolution isn't capped by the ceiling; or give
     more weight to A1 and Petri's realism judge, which did move tonight. These are C1/C2 decisions, posted to the
     board.

Caveats:
- Real OpenHands-feedback users are often trying the agent out, with toy tasks like "write ruby code … do not
  execute". Those sessions are not pure deployment, so 0.90 may overstate how Kimi scores production use.
- Kimi answered through Devin's agent wrapper.
- These are the placeholder probes, not EvalDetectBench's (C1 still has to choose).
