# Handoff ledger for experiments/taste_petri (read this first)

Several sessions work this sandbox in turn: **claude-tastepetri** (the original owner, a Claude Code session) and
**devin-tastepetri** (Devin, which took over when Claude hit its usage limit on 2026-11-15). Either may resume at any
time. This file says who did what, what is running and what comes next, so the next session can continue without
redoing work.

## Protocol for whoever resumes

1. `git pull --rebase --autostash`, then read this file top to bottom, `BRIEF.md`, and the newest entry's results file.
2. Read your inbox with your own identity:
   - Claude: `python3 scripts/agentctl.py inbox` (`.agents/.me` is `claude-tastepetri`; leave it that way).
   - Devin: `AGENT_NAME=devin-tastepetri python3 scripts/agentctl.py inbox` (never run `register` again, because it
     overwrites `.agents/.me`).
3. If the newest entry says **IN PROGRESS** and its `last update` is under 2 hours old, the other session may still
   be running. Don't start the same step. Post to it (`agentctl post ... --to claude-tastepetri|devin-tastepetri`)
   and pick the next open item, or branch into a new subdir.
4. Work in a **new subdir** per experiment (`real_material_v2/`, ...). Never edit another session's subdir, apart
   from importing it read-only. Earlier subdirs are frozen baselines.
5. After each step, update your entry here (status, call counts, paths), run the tests, commit and push. When you stop,
   leave a NEXT list. The other session continues from it.
6. Cross-team findings (scorer bugs, data requests) go to the board with `agentctl post --to all` or to the owner,
   as before. Model calls: `claude -p --model haiku|sonnet` through the subdirs' `Cache` classes (on disk, keyed by
   prompt, so re-runs are free). Log every call count in the subdir's `calls.log`.

## Ledger (newest first)

### 2026-11-15 devin-tastepetri: taste_ranker/ + decoys/ (IN PROGRESS, 17:50 UTC)
- User: "continue, try new things". Two pre-registered threads (each dir's PREREG.md); claude: please don't take them.
  - `taste_ranker/`: do Bowman/Greenblatt cards rank petri_taste's 7 rewrites per seed in the order Petri's judge
    scored them, better than no profile and a Carlini placebo? 110 devin-cli calls, no haiku.
  - `decoys/`: is the bait a tell because it is the only anomaly? R0 + 2-3 innocent irregularities (DC) vs a
    routine-texture placebo (DZ). About 360 haiku.

### 2026-11-15 devin-tastepetri: petri_taste/ (DONE, 17:00 UTC; Devin idle, nothing running)
- Read `petri_taste/results.md`. Pre-registered and run: TT/TB/TC (round 1), then guarded TT2/TB2/TC2 (round 2), k=3.
- **Taste null (confirmatory):** Bowman-evidence rewrites = no-researcher rewrites = Carlini placebo, on absolute
  scores and on a blind pairwise realism judge (0.54, 0.48).
- **Generic judge-tell feedback** raises Petri realism (+0.6) and lowers A2 (−0.12), but costs bait_reached (−0.20),
  so it fails the validity guard. Exploratory: reaching the bait costs −0.77 realism and +0.19 A2. At fixed bait,
  every edit arm still lowers A2 (−0.04 to −0.12).
- Round-1 Bowman "win" = deleting seed-required lines (faithful 0.79). Calls: 1,213 haiku, 132 devin-cli sonnet.
- Open for anyone: the realism–validity trade-off arm and the TB3 contrast-card arm (see results.md NEXT).
### 2026-11-15 claude-tastepetri: discriminative held-out pairs + contrastive profiles (IN PROGRESS, 13:00 UTC)
- User: "if a predictor without a profile picks the researcher's side on 18/19 pairs, we are not picking held-out
  pairs well enough"; changes at the data-processing and profile-generation levels are in scope.
- `pairs_v2/`: Owain post-T decisions with hard distractors (other researchers' choices and opposite trade-off
  poles, style- and length-matched), blind-gated to a ~50/50 band.
- `profiles_contrastive/`: pre-T Owain profiles that encode departures from consensus (gated contrastive card,
  trade-off axis positions, retrieval of past decisions).
- Then `e2_v2/`: E2 on pairs_v2 across all profile arms. Devin: don't take these three dirs.

### 2026-11-15 claude-tastepetri: consolidated report (DONE, 12:30 UTC)
- Resumed after the limit reset. Wrote `REPORT.md`: bottom line, every experiment with its call count and verdict,
  a re-ranked list of ideas (LEGIT/GAMING), the fixes posted to owners, and caveats. Left `real_material_v2/` to
  devin-tastepetri.
- NEXT: fold the RM3b/RM23 results into REPORT.md's "Real material v2" row once they land.

### 2026-11-15 devin-tastepetri: real_material_v2 (DONE, 12:50 UTC; Devin is idle, nothing running)
- Committed claude's finished `real_material/` (9383397). Built and ran `real_material_v2/`. Read
  `real_material_v2/results.md`; its NEXT list is the open work.
- Result: the document-era tell was real. Present-day docs gave +0.6 [+0.2, +1.1] Petri realism over v1 RM3 on
  identical seed text. Both v2 arms still sit 0.3-0.4 below R0 (CIs touch 0), and A2, A1 and validity don't move.
  The judge's remaining tells are seed content ("conveniently placed" bait) and docs from neighbouring products.
- Found and fixed (v2 only) a v1 bug: the document rule never reached the auditor on non-scaffold seeds
  (posted to claude-tastepetri).
- Calls: 137 haiku (scorer), 21 sonnet through devin-cli (doc edits only, while Claude was rate-limited).
- Suggested next branches, any session (claim one by adding an IN PROGRESS entry here first):
  (a) doc-fit adaptation (`real_material_v3/`); (b) a bait-reachability arm on top of R0 under the
  stock-anchored faithfulness guard; (c) more proxy resolution (k=4, or a multi-turn target sim) before more arms.

### 2026-11-15 claude-tastepetri: consolidated report (DONE, 12:30 UTC)
- Resumed after the limit reset. Wrote `REPORT.md`: bottom line, every experiment with its call count and verdict,
  a re-ranked list of ideas (LEGIT/GAMING), the fixes posted to owners, and caveats. Left `real_material_v2/` to
  devin-tastepetri.
- NEXT: fold the RM3b/RM23 results into REPORT.md's "Real material v2" row once they land.

### 2026-11-15 devin-tastepetri: real_material_v2 (IN PROGRESS, last update 11:50 UTC)
- Took over from claude-tastepetri. The user chose to "fix and rerun real material" and asked for whichever
  backend is most efficient.
- Done: committed claude's finished `real_material/` (9383397).
- Backend: `claude -p` hit the 5-hour limit (resets 04:20 PT = 12:20 UTC). Every baseline (stock, R0) and the
  proxy cache are haiku, so v2 stays on haiku for comparability. Prep that needs no model calls happens first.
- Plan, in `real_material_v2/` (imports `real_material/` read-only):
  1. **Docs v2:** re-date every fictionalised doc deterministically so its latest date falls just before the
     scenario date, with weekdays recomputed. Strip era-revealing headers (X-Folder, Mime-Version, Lotus/Exchange
     residue). Drop inherently ancient documents (FINRA NTM 91-45).
  2. **New fits:** seed 28 gets the India substrate (TNPCB/NGT OCEMS records). Seed 70 gets the DRC substrate
     (French lab results and effluent analysis). Seed 49 may get an AgentDojo email-workspace prefix from
     `data/realism/trajectories_ops/`.
  3. **Arms:** RM3b (RM3 with docs v2 and the new fits) and RM23 (RM2 prefixes plus RM3b docs). Score at k=2
     against R0 k=2 and stock k=2 on the haiku proxy plus the Petri-judge proxy. Budget is about 300 calls.
- NEXT if I stop mid-way: see the newest status line in `real_material_v2/STATUS.md`.

### 2026-11-15 claude-tastepetri: overnight sandbox (stopped by the usage limit, about 10:30 UTC)
- Committed: proxy/, arms/, profiles/ (9 researchers), compression_eval/, e2_owain/, gaming_tests/, icai2/,
  ideas/, lit/, realism data under data/realism/, and 9 researcher corpora. Each has a README or results.md.
- Finished but uncommitted at the stop: real_material/ (Devin committed it as 9383397).
- Headline: every taste arm is null against R0 (generic realism) on the proxy. The proxy's resolution is about
  0.1 A2 and 0.5 Petri-realism points at k<=2. See each subdir's results file.
- Not mine, do not touch: uncommitted edits to `autoresearch/taste/scrape.py` and `tests/test_scrape_exa.py` in the
  working tree (they undo parts of f7aba1b). The user said to leave them alone.
