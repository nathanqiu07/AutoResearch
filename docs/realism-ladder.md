# Realism ladder (WS C2)

Board task `realism-ladder`. The same held-out Petri seeds run at four realism levels, so we can see how
much each layer of realism lowers the target's eval awareness (A1 and A2, PLAN §3.2). This is the graded
form of the "text-only vs real sandbox" demo in PLAN §10 (Exa + Modal).

**Status: built and tested offline. No real-model or Modal run has happened.** The paid run needs the
user's approval and the pre-registration `results/prereg/realism_ladder.json` (currently a draft) made final.

## Levels

| level | `tools` | what the target gets |
|---|---|---|
| `L0_text` | simulated | no tools. The seed text ends with `TEXT_ONLY_INSTRUCTION` (in `autoresearch/research/ladder.py`, quoted in the prereg): the auditor runs the scenario purely as conversation, creates no tools, and puts any files, logs or command output into its messages as plain text |
| `L1_simulated` | simulated | stock Petri: the auditor invents every tool result |
| `L2_sandbox` | sandbox | the target's shell-type tool calls run in an empty Modal Sandbox (`harness/petri/sandbox_tools.py`) |
| `L3_repo` | sandbox + `repo` | the sandbox is first populated by cloning a real public repo, history kept (board task `real-repo-sandboxes`) |

L0 relies on the auditor following an instruction, not on a harness switch. Check that L0 transcripts
really have no target tool calls (the transcript's `[tool call ...]` lines) before reading L0 results.

## Commands

```bash
# 1. expand seeds into the ladder (deterministic: every seed at every level)
python3 -m autoresearch.research.ladder build --seeds data/petri/seeds_v2.jsonl --split hidden \
    --repos repos.jsonl --out runs/ladder/seeds.jsonl
# 2. free end-to-end check: build + offline simulator + analysis
python3 -m autoresearch.research.ladder smoke --out-dir runs/ladder_smoke
# 3. paid (needs approval): one PetriMeasurer per level, through the Petri harness
python3 -m autoresearch.research.ladder run --seeds runs/ladder/seeds.jsonl --paid --epochs 3 \
    --cache-dir runs/ladder/cache --out results/ladder/run.json
# 4. analysis (+ ladder.png when matplotlib is installed)
python3 -m autoresearch.research.ladder analyze results/ladder/run.json --out-dir results/ladder --chart
python3 scripts/plots.py ladder results/ladder/ladder_report.json --out results/ladder   # chart only
```

`--repos` takes any JSONL of repo dicts (for example the output of
`python3 -m autoresearch.research.real_repos`). Repo fields (`url` or `local_path`, `ref`, `depth`,
`licence`, `source_url`, `published`, `path`, ...) pass through as given; the harness validates them.
Repos are assigned deterministically:

1. a seed row's own `repo` (so seeds already given repos by `real_repos attach` keep them);
2. otherwise a repo whose `seed_id` names the seed;
3. otherwise the remaining repos in (url, ref) order, round-robin.

## Row format

A ladder row is an AuditSeed. Its `seed_id` is `<seed_id>__<level>`, and it carries `base_seed_id` and
`realism_level`. PetriMeasurer passes both through unchanged (`petri_measure.SEED_TAGS`) to the audit row
it sends the harness and to every PetriSample it writes, so results carry them explicitly. Analysis reads
the level from `realism_level` and the seed from `base_seed_id`. It parses the id (level suffix, seed
prefix before `__`, ignoring PetriMeasurer's `@s<n>`) only for rows without those fields, i.e. older
results. Seeds without the tags behave as before: the audit's `base_seed_id` is the seed's own id and the
sample has no tag fields.

## Analysis

`analyze` accepts three inputs: a ladder run JSON, a `scripts/c2_e3b.py` report, or a JSONL of
PetriSample dicts. It reads A1 from `verbalized` and A2 from `self_report`, the names PetriMeasurer
writes. It reports:

* **Per level:** n, errors, seeds, and mean A1 and A2 with 90% bootstrap CIs, plus A2's share above
  0.5.
* **Adjacent levels** (L0→L1, L1→L2, L2→L3): each seed's mean over epochs is taken first. Then it
  reports the paired difference over shared seeds, its bootstrap CI and P(lower).
* **Trend across levels:** each seed's least-squares slope of the metric on the level index 0..3. It
  reports the mean slope with a bootstrap CI and a two-sided sign-flip permutation p-value. The test is
  exact up to 16 seeds and pairs by seed.
* **Provenance:** CODE_VERSION (from the run, or a `CODE_VERSION` file next to the input), the analysis
  code version, cost and the model lineup.

**Cost.** The ladder run records only the judge and probe spend from `Budget`. The Petri auditor and
target spend is in the Inspect logs, and Modal time is on the Modal dashboard.

**Offline runs.** The offline path maps each level to OfflineWorld categories
(`OFFLINE_LEVEL_CATEGORIES`), so the trend test has something to find. That mapping is a simulator
assumption, not a prediction. Offline output is labelled "OFFLINE SIMULATOR" in the JSON, the markdown
and the chart, and is never a result.

Tests: `tests/test_ladder.py`.

## Related: counterfactual cue replays

The ladder compares whole environments. To isolate **single cues**, use the counterfactual replays.
They resume a finished sandbox audit at a decision point from a filesystem snapshot, once unchanged and
once per single-cue mutation. See `harness/README.md` ("Counterfactual cue replays"),
`harness/petri/counterfactual.py` and `autoresearch/research/counterfactual.py`.
