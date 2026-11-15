# real_material_v2 status (owner: devin-tastepetri; newest line last)

- 2026-11-15 11:50 UTC: prep done, no model calls yet. `material_v2.py` (docs v2, weekday repair, checks, v2 fit),
  `run_v2.py` (docs / seeds / run / summary), seeds/RM3b.jsonl and seeds/RM23.jsonl built. RM3b's seed text equals
  v1 RM3's on all 12 seeds: only the documents change, which isolates the doc fix. RM23's text equals v1 RM2's on
  73 and 17 (cache hits).
  Waiting for the Claude CLI limit to reset (12:20 UTC). NEXT: `run_v2.py docs` (about 17 sonnet calls), read
  material/checks.json and spot-read 3 docs, smoke-test 2 seeds, then `run RM3b RM23 --samples 2`, `summary k2`,
  then results.md.
- 11:56 UTC: docs v2 done on **devin-cli** (claude-sonnet-5-5-medium; 21 calls = 18 + 3 cleanup passes, logged in
  calls.log). The doc edits don't touch the scorer, so the scorer stays on haiku. Checks are in
  material/checks.json: no export headers, no dates after today, no years before 2024 except law and notification
  dates (d28) and WHO norm editions (d70). Spot-read d49, d70 x2, d28, d153 minutes. The cleanup pass removed
  Python/PyPI roles from the Larkspur minutes (a genre tell v1 already had) and two-column PDF text from d70.
  **v1 bug found:** rm_proxy.auditor_prompt's document rule never reached the auditor on non-scaffold seeds
  (28, 66, 70): the `"\nReturn the JSON only."` replace doesn't match AUDITOR_FORMAT. v2 patches this in run_v2.py
  (v1 is left frozen). So RM3b vs RM3 on 28/66/70 also includes this fix.
  NEXT: at 12:20 UTC, smoke-test 2 seeds on haiku, then `run RM3b RM23 --samples 2`.
