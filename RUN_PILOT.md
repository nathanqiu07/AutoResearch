# Run the C2 pilot on your Modal account

What this does: measures how often the target model (Qwen3-30B-A3B) notices it is being tested in
Petri audits, for **stock Petri seeds** (the baseline) and for a **plain-agent control** (seeds rewritten
for realism with no taste). Later the taste system's rewrites are compared against both.
One run per seed, 12 dev seeds. Everything uses **your own** Modal and OpenAI accounts and keys.

Models: target `Qwen/Qwen3-30B-A3B` on Modal (1×H100, raw reasoning); Petri auditor
`Qwen3-235B-A22B-Instruct-2507-FP8` on Modal (4×H100); our judge and Petri's judge `openai:gpt-5`;
the control rewriter is the taste system's model, `openai:gpt-6-luna` (configs/models.json).

Rough cost (estimate, not measured): smoke about $2; baseline about $12–17; control step (stock + control,
24 audits) about $20–30. Modal apps are stopped automatically when each step ends, even on error.

## 0. One-time setup (about 10 minutes)

You need: Python 3.9+ (repo), Python 3.12 (Petri), a Modal account **with a payment method**
(Modal refuses every GPU without one, even with credits), an OpenAI API key.

```bash
git clone https://github.com/nathanqiu07/AutoResearch && cd AutoResearch
python3.12 -m venv ../.petri-env
../.petri-env/bin/pip install --prefer-binary eval/vendor/petri-v2.tar.gz modal
../.petri-env/bin/modal setup                      # log in to YOUR Modal workspace
K=$(openssl rand -hex 24) && ../.petri-env/bin/modal secret create vllm-key VLLM_API_KEY=$K && echo "export VLLM_KEY=$K" >> ~/.zshrc
echo 'export OPENAI_API_KEY=<your key>' >> ~/.zshrc
source ~/.zshrc
```

Check the plumbing for free (no model calls):
```bash
python3 -m unittest discover -s tests -t .                  # must say OK
../.petri-env/bin/python -m unittest harness/petri/test_harness.py
```

## 1. Smoke test (about $2): the target serves and returns raw reasoning
```bash
MODAL_BIN=../.petri-env/bin/modal bash scripts/c2_pilot.sh smoke
```
Pass = it prints `"passed": true` and writes `results/smoke/c2_target_<date>.json`.
If it fails, stop and send the output.

## 2. Baseline: stock Petri seeds (about $12–17)
```bash
MODAL_BIN=../.petri-env/bin/modal bash scripts/c2_pilot.sh baseline 12
```
Output: `results/e3b/pilot_stock_qwen3-30b_dev_n12_<date>.json`. It prints awareness and validity.
**If stock awareness is below about 0.4, stop:** the target barely notices tests and there's nothing to reduce
(see results/prereg/E3b.json). Use `baseline 6` to halve the cost.

## 3. Control: plain-agent rewrites vs stock (about $20–30)
```bash
MODAL_BIN=../.petri-env/bin/modal bash scripts/c2_pilot.sh control 12
```
This writes the control seeds to `runs/petri/control_dev.jsonl`, then audits stock and control in one
report: `results/e3b/pilot_stock_vs_control_qwen3-30b_dev_n12_<date>.json`, with the paired difference
per seed (`vs_stock.control`). If you already ran step 2 and want to save money, you can skip it: step 3
re-runs stock anyway.

## 4. After each run
- Check the Modal dashboard: no app should still be running (`../.petri-env/bin/modal app list`).
- Commit the results JSON (`git add results/... && git commit && git push`), plus the `CODE_VERSION` (`git rev-parse --short HEAD`).
- Post the numbers and the actual cost on the board (`python3 scripts/agentctl.py post ...`).

## If something breaks
- `deploy ... failed`: run the `modal deploy` line from `scripts/c2_pilot.sh` by hand to see Modal's error
  (usually billing, or a GPU type your plan lacks).
- Samples with errors are reported, never averaged in. The first request after deploying waits several minutes while weights load.
- The $15 `--max-cost` covers our judges and the target's GPU time only. It can't see the auditor's GPU time or Petri's own judge calls, so watch the Modal bill too.
