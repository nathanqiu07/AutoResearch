# real_material_v2 status (owner: devin-tastepetri; newest line last)

- 2026-11-15 11:50 UTC: prep done, no model calls yet. `material_v2.py` (docs v2, weekday repair, checks, v2 fit),
  `run_v2.py` (docs / seeds / run / summary), seeds/RM3b.jsonl and seeds/RM23.jsonl built. RM3b's seed text equals
  v1 RM3's on all 12 seeds: only the documents change, which isolates the doc fix. RM23's text equals v1 RM2's on
  73 and 17 (cache hits).
  Waiting for the Claude CLI limit to reset (12:20 UTC). NEXT: `run_v2.py docs` (about 17 sonnet calls), read
  material/checks.json and spot-read 3 docs, smoke-test 2 seeds, then `run RM3b RM23 --samples 2`, `summary k2`,
  then results.md.
