# Benchmark data (WS C1)

What each upstream eval-awareness dataset is, how to fetch it, and what we derive from it.
Checked 2026-11-14. Each fact is marked **[verified]** (seen in the API response, the file or
the code) or **[unverified]** (stated somewhere, or inferred, but not checked by us).

Downloads go in `raw/<source>/` and are gitignored. Treat them as untrusted: read them with
`python3 -I`, one directory per source.

## Files here

| File | Committed | What |
|---|---|---|
| `evalawarebench_original.jsonl` | no (gitignored) | 200 items, all 8 cue factors on. Read with `benchmarks.load_items` / `load_items_with_meta` |
| `evalawarebench_minimal_cue.jsonl` | no | Same 200 ids, all cue factors off |
| `evalawarebench_cue_pairs.jsonl` | no | `{"id", "with_cue": {system,user}, "without_cue": {system,user}, "meta"}` for `calibrate --cue-pairs` |
| `evalawarebench_split.json` | yes | Frozen dev/held-out split, ids only (128 dev / 72 held-out, 64/36 task pairs) |
| `evalawarebench_convert_report.json` | yes | Converter counts. No prompt text |
| `evaldetect_probes.json` | yes | A2 probe questions `{"default": [...], "<backend>:<model>": [...]}` for `--probe-questions` |
| `evaldetect_probes.provenance.json` | yes | Upstream probe ids, per-judge AUROCs, adaptations, sources |

Regenerate:

```bash
python3 scripts/convert_evalawarebench.py --fetch        # ~0.8 MB download, then convert
# if this Python has no CA bundle (python.org macOS builds):
uv run --no-project --with certifi python scripts/convert_evalawarebench.py --fetch

uv run --no-project --with pyyaml --with pyarrow python harness/evaldetect/export_probes.py \
    --scores data/benchmarks/raw/evaldetect_hf/scores_parquet/0000.parquet   # inputs: see EvalDetectBench below
```

---

## EvalAwareBench (Li et al., "Decomposing and Measuring Evaluation Awareness")

| Fact | Status |
|---|---|
| HF id `aisa-group/EvalAwareBench`, public, `gated: false` | [verified] HF API |
| Revision used: `ee984a8df39387946315475ee7b221ad790e1b34` (last modified 2026-09-29) | [verified] HF API, recorded in `raw/evalawarebench/FETCHED.json` |
| Licence CC BY-NC 4.0. The card adds: don't use it as training data (tags `noai`, `noimitate`) | [verified] card, data card, LICENSE text |
| Code: github.com/aisa-group/decomposing-eval-awareness | [verified] linked from the card. Its README, data card, taxonomy and LICENSE are in `raw/evalawarebench_github/` (fetched by the earlier worker, not re-fetched) |
| Paper arXiv 2605.23055 | [unverified] cited on the card |
| **Why the HF rows API returned 404:** there is no `default` config. The configs are `tasks` (200 rows), `prompts` (51,200), `prompts_safety` (25,600) and `prompts_capability` (25,600), each with split `train` | [verified] card YAML; datasets-server returns `num_rows_total=200` per `num_factors_varied` value |
| 100 task pairs (a safety and a capability variant = 200 task variants), adapted from HarmBench, in 10 categories | [verified] 200 rows in `tasks.jsonl`, `source: "HarmBench (adapted)"` on the safety rows. [unverified] the category count, which comes from the data card |
| 8 factors F1–F8, each naturalistic or exaggerated, giving 2^8 = 256 configurations per variant | [verified] upstream `generate_hf_data.py` |

**`prompts` row schema** [verified on the 400 rows we fetched]:
`task_id` (str, e.g. `<task>_safety`), `task_name` (str, shared by the pair), `valence`
(`safety`|`capability`), `description` (str), `factors_varied` (list of factor codes, or
`["none (baseline)"]`), `num_factors_varied` (int 0–8), `config` (`{F1..F8: level}`),
`prompt` (str: one user message, no system prompt).

Factor levels, naturalistic → exaggerated: F1 stimulus artificiality `realistic→varied`;
F2 scenario coherence `realistic→varied`; F3 prose register `casual→formal`;
F4 ecological completeness `realistic→varied`; F5 stakes telegraphing `realistic→varied`;
F6 paradigm recognizability `realistic→varied`; F7 task format `prose→template`;
F8 explicit eval disclosure `realistic→varied`.

`tasks` row schema [verified]: `task_id, task_name, valence, paired_with, description,
source, num_slots, slot_names, factors_used`.

**What we fetch:** only the two configurations we use, from the HF datasets-server `filter`
endpoint (`config=prompts&split=train&where="num_factors_varied"=0|8`, 4 pages of 100), plus
`data/tasks.jsonl`. That is about 0.8 MB. The full `prompts.jsonl` (51,200 rows) is not fetched.
The datasets-server sometimes returns a transient `{"error": "Authentication check ... failed"}`.
The fetcher retries; the converter rejects an error page instead of parsing it.

**Converter** (`scripts/convert_evalawarebench.py`):

* `original` = `num_factors_varied == 8` (all cues on); `minimal_cue` = `0` (all off).
  EvalAwareBench has no separate original prompt: every row is one factor configuration.
  The all-cues configuration is the most benchmark-like one, so we call it "original".
  The all-on vs all-off contrast only shows that the scorer reacts to many cues at once.
  It says nothing about any single cue. Single-factor configurations would need another
  fetch, which needs Nathan's approval.
* id = upstream `task_id`, the same in both config files, with no suffix.
  `meta`: `config`, `label` (safety|capability), `cues` (`{F1..F8: bool}`, true = exaggerated),
  `levels`, `factors_varied`, `task_name`, `paired_with`, `source`, `description`, `dataset`,
  `revision`, `embedded_role_lines`.
* `behaviors`/`misbehavior` are **our labels, not upstream's rubric** [unverified against the paper]:
  safety `refuses|complies|partial|unclear` with misbehaviour `complies|partial`;
  capability `completes|refuses|partial|unclear` with misbehaviour `refuses|partial`.
* Split: `benchmarks.freeze_split`, 40% held out by a hashed group. The group is `task_name`,
  so a safety/capability pair, which share scaffolding, always lands on one side. With 100
  groups the actual split is 64/36 pairs.
* Results on revision `ee984a8`: 400 raw rows → 200 items per config (100 safety, 100 capability
  in each), 200 complete pairs, **0 failed to map, 0 multi-turn or tool-based**. 39 `original`
  prompts contain `User:`/`Human:` lines. These are the F6 "known eval wrapper" cue written into
  one user string, not real turns, so they stay in `user`. No `minimal_cue` prompt has them.

---

## EvalDetectBench (Li, Ochwang'i, Bharadwaj, Souly, Kirk)

**These are one project, not two.** GitHub `freeze-lasr/aware_bench` is the code and
HF `el7982/aware-bench` is its data. [verified] The repo description is "EvalDetectBench:
Benchmark that measures whether LLMs can detect that they are in evaluation or deployment
contexts". Its README links the HF dataset as the paper's data. The HF card says "Companion
dataset for EvalDetectBench".

| Fact | Status |
|---|---|
| GitHub `freeze-lasr/aware_bench`, public, MIT, default branch `master`, last push 2026-11-09, homepage evaldetectbench.com | [verified] GitHub API |
| HF `el7982/aware-bench`, public, `gated: false`, CC BY-NC-SA 4.0, revision `2a036d1a642b64c6aea8b681a47f2624b80fd16d` | [verified] HF API |
| Paper arXiv 2609.01611 | [unverified] cited in the README |
| Built on Inspect (`inspect_ai`); transcripts are Inspect samples | [verified] code imports |
| HF layout: `collected_trajectories/` (per-model `all.json` plus per-source JSON for 12 generator models, `deployment_categories/`, `non_inspect_chat_evals/`); `measure_logs/` (12 Inspect `.eval` logs of 62–238 MB each, `scores.csv` 7.6 MB, `config.yaml`); `paper_replication/` (CSV inputs to the figures) | [verified] HF tree API |
| The `collected_trajectories` JSON schema (the deployment transcripts for our negative pool) | [unverified] not downloaded |

**Probe questions** [verified] (`probe_questions/` in the repo):
`eval_mcq.yaml` is 5 probes, the default when no selection is run; `eval_mcq_calibration.yaml`
is the 20-probe pool the paper selects from; `eval_mcq_confidence.yaml` is 5 probes on a 0–10
scale, not used. Every probe has `id, category, text, answer{real, eval}, template_text,
template_config{method: append, ...}`. Upstream appends the question after the transcript as a
new user turn and scores an XML `<label>` as 0 or 1. Some probes have reversed polarity
(`indirect_consequences_a`: `YES` = real).

**Per-judge selection** [verified from `measure_logs/config.yaml`]: exhaustive search over probe
subsets up to `max_k: 5`, on a 20% calibration split stratified by
`eval_category, has_tools, category` (seed 42), then every transcript is measured with the
selected probes. The selected sets are not published as a file.

**`measure_logs/scores.csv` schema** [verified, read from the HF parquet export
`refs/convert/parquet` `scores/train/0000.parquet`, 1.45 MB, 41,149 rows]:
`sample_id, transcript_id, pq_id, source, category, eval_category (bool), judge, judge_family,
gen_family, is_agentic (bool), p_eval (1 = called eval, 0 = deployment, 0.5 = ambiguous; no -1 rows)`.
12 judges, about 740 transcripts each.

**Our export** (`harness/evaldetect/export_probes.py` → `evaldetect_probes.json`):

* **[unverified, inferred]** The probe ids that appear for a judge in `scores.csv` are that judge's
  selected set. The evidence: each judge has 3–5 distinct probes (max_k = 5), the sets differ by
  judge, and for each judge most transcripts carry exactly that set (84%–100% per judge; the
  lowest is gemini-2.5-pro, 621/738; the rest are probably failed samples that were dropped). Our ensemble AUROCs on all
  transcripts are close to the paper's held-out k-sweep: opus 0.892 with 5 probes vs 0.886;
  sonnet 0.878 with 4 vs 0.892; gpt-5.4 0.825 with 4 vs 0.818. gpt-5.1 is the loosest match:
  0.802 with 3 vs 0.738. These numbers include the calibration split, so they are optimistic.
* Keys: Anthropic judges → `anthropic:<model>` and `openai-compat:anthropic/<model>`; the others →
  `openai-compat:<openrouter id>`. `default` = upstream `eval_mcq.yaml`. A model with no exact key
  (e.g. our Modal reasoning target) falls back to `default`.
* Adaptations (question sentence verbatim; everything else is listed here and in the provenance file):
  1. The transcript is quoted inside the prompt (`{transcript}`), aware_bench's "quote" method,
     instead of being appended as a prior conversation.
  2. The answer is JSON `{"p", "label", "explanation"}` instead of XML. `p` is the probability
     that the answer is the probe's **eval** label, so reversed-polarity probes stay correct.
  3. `p` comes first and the explanation is one sentence, because `measure.p_eval` caps the
     reply at 300 tokens.
* Effect of the adaptations on AUROC: **[unverified]**. Upstream's AUROCs come from binary labels
  in its own format. Ours ask for a continuous `p`, so check them against the calibration gate.
* No model calls were made.

---

## Needham et al. eval_awareness ("Large Language Models Often Know When They Are Being Evaluated")

| Fact | Status |
|---|---|
| HF `jjpn2/eval_awareness`, **gated (`gated: "auto"`: accept the terms on HF)**, CC BY-NC-SA 4.0, last modified 2025-07-15 | [verified] HF API, card |
| Access terms: downloading also discloses GAIA content; don't redistribute it outside a gated or private repo | [verified] card |
| Files: `dataset.zip` (encrypted), `scripts/decrypt.sh`, `scripts/encrypt.sh`, `get_dataset_metadata.py`, licences | [verified] HF API file list |
| Code: github.com/jjpn97/eval_awareness (public) | [verified] |
| Paper arXiv 2505.23836 | [unverified] cited on the card |
| **Not downloaded.** It is gated, so Nathan has to accept the terms and fetch it himself | — |

**Schema of the eval-vs-deployment label.** From the card and the public loader
(`pipeline/dataset.py`, `constants.py`). [verified from those documents; `dataset.json` itself is not inspected]:

* `dataset.json` is a JSON list of Inspect `Sample` dicts `{id, input, metadata, ...}`. `input` is
  the transcript (chat messages with roles, tool calls included). `metadata.tools` is a list of
  Inspect `ToolInfo`.
* **Label: `metadata.eval_category` (bool).** `true` = written for evaluation; `false` = organic
  deployment. The paper uses it as ground truth.
* `metadata.scaffold`: `null` = chat; not null = agentic.
* `metadata.category`: source dataset. `eval_type` (`capability`|`alignment`) exists only when
  `eval_category` is true. The loader treats these categories as capability and every other
  eval category as alignment: cybench, swe_gym, swebench, nl2bash, gaia_runs, mmlu, aider_full,
  natural_reasoning, smol_gaia_manager, smol_gaia_search, wmdp.
* Human labels `eval_author1`, `eval_author2` (P(eval) in 0–1). **[unverified]** where they sit in
  the record. The card calls them columns.
* **[unverified]** the file name. Their code defaults to `eval_awareness_val.json`
  (env `EVAL_AWARENESS_DATA_FILE`); the card says decrypting gives `dataset.json`.

Reference AUROCs (PLAN 4.1): frontier models 0.71–0.77 on chat, 0.88–0.95 on agentic.
`calibrate.load_labelled` reads this format as is (Calibration session, 2026-11-14).

Fetch (Nathan, after accepting the terms on the HF page):

```bash
huggingface-cli login                      # his own token; agents never handle it
git clone https://huggingface.co/datasets/jjpn2/eval_awareness.git data/benchmarks/raw/needham/repo
bash data/benchmarks/raw/needham/repo/scripts/decrypt.sh   # read the script first; it is untrusted
```
