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

### 2026-11-15 claude-tastepetri: e2_climb/ (IN PROGRESS, 19:50 UTC, user-directed)
- User: "hillclimb these intervals" (the e2_v4 profile-vs-no-profile CIs). Pre-registered in `e2_climb/PREREG.md`:
  climb A tunes on pre-T firewalled pairs (synthme/pairs_paper), climb B on decision-disjoint post-T pairs; one
  confirmation each on e2_v4's 96 pairs. Sonnet, starts after the 14:20 PT usage reset. Other sessions: don't
  take e2_climb/. synthme/ (Owain) resumes after the reset too.

### 2026-11-15 devin-tastepetri: synthme_hobbhahn/ (IN PROGRESS, 19:30 UTC, user-directed)
- User: "do the same SynthesizeMe run for the other researchers", pilot on **Marius Hobbhahn** first. The user
  explicitly lifted BRIEF.md's "never use Hobbhahn's writing as profile/test data" rule for this run.
- Same methodology as synthme/ (Owain): pairs_v4 test pairs with realness/taste gating on his 45 post-T decisions
  (6 works), synthme/pairs.py training pairs (paper + informal), fit.py S_paper/S_inf/S_all, arms M0s/NAME/ANTI0.
  The Owain modules are imported read-only and re-pointed by `synthme_hobbhahn/common.py`; P0 is not built.
- Every call is on **free swe-2-medium via devin-cli** (user: maximise calls, no cap), so numbers are comparable
  within Hobbhahn only, not with Owain's sonnet results. Informal harvest runs as a Devin subagent.
- Doesn't touch synthme/ or the paused Claude session's Owain run.

### 2026-11-15 claude-hillclimb: hillclimb/ (IN PROGRESS, new session, user-directed)
- User: "all results have taste neutral to control for the eval awareness task; hill-climb to demonstrate an
  improvement". Pre-registered in `hillclimb/PREREG.md`: climb taste-steered rewrites on dev against R0 (task score
  `(1-aw)*validity`, guards on faithfulness and Petri-judge eval_awareness), then ONE confirmation on the hidden split
  with fresh samples: R0 vs H* vs H*-0 (same pipeline, no researcher material). Log per candidate in `hillclimb/LOG.md`.
- Haiku proxy (rm_proxy no-material path, unchanged); sonnet rewrites via claude -p. Other sessions: don't take hillclimb/.

### 2026-11-15 devin-tastepetri: surgery/ (IN PROGRESS, 19:10 UTC)
- decoys DONE: null; the first-batch A2 effect did not replicate, and an A/A split shows that k=3 seed-bootstrap CIs
  are overconfident on validity/bait/A1 (`decoys/results.md`).
- `surgery/` (PREREG.md): common random numbers. R0's exact audit openings are reused, one edit is applied (ID
  re-run, SOFT = same bait facts but ordinary presentation, NB = bait removed), then everything downstream is
  re-scored. Tests whether the bait tell is presence or presentation. About 360 haiku + 60 devin-cli calls.

### 2026-11-15 devin-tastepetri: taste_ranker/ + decoys/ (IN PROGRESS, 18:30 UTC)
- `taste_ranker/` DONE (results.md): no profile beats a no-profile ranker at ordering rewrites by measured realism
  (null); the no-profile ranker itself tracks realism (rho 0.26, ceiling ~0.57); every ranker prefers bait-losing
  rewrites; the Bowman card softens that (+0.07 validity rho, exploratory).
- `decoys/` k=3: DC (2-3 innocent irregularities) vs R0: A2 −0.05 [−0.10, −0.01] with validity and bait kept,
  realism +0.3 [−0.1, +0.7] (primary not met). DC vs DZ (texture placebo): bait +0.12, validity +0.08.
  RUNNING: pre-registered fresh-sample replication (R0, DC at k=3-5; `runs/score_rep.out`).
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
