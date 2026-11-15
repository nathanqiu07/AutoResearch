# Run the C2 pilot (baseline + control) on your own accounts

What this does: measures how often the target model notices it is being tested in Petri audits, for
**stock Petri seeds** (the baseline) and for a **plain-agent control** (the same seeds rewritten for
realism with no taste). The taste system's rewrites are compared against both later.
One run per seed, 12 dev seeds. Everything uses **your own** keys; none are stored in the repo.

| Role | Model | Runs on |
|---|---|---|
| Target (main) | Kimi K2.5, thinking on | Tinker, through `harness/tinker_proxy.py` on your laptop |
| Petri auditor | Qwen3-235B-A22B-Instruct-2507-FP8 | your Modal account, 4×H100 |
| Judges (ours and Petri's) | `openai:gpt-5.1` | your OpenAI key |
| Control rewriter | `openai:gpt-6-luna` (the taste system's model) | your OpenAI key |

Rough cost (my estimate, nothing has been run): smoke about $1–2; baseline about $10–17; control step
(stock + control, 24 audits) about $20–30. The control step re-runs stock, so you can skip the baseline step.
Everything stops automatically when a step ends, even on error.

**Spend limits to set before running:** a monthly limit on your Modal workspace (e.g. $75), a usage limit on
your OpenAI key, and watch the Tinker console. The script's own caps are a $15 `--max-cost` on our judges
and a 10M-token cap on Tinker (`TINKER_TOKEN_CAP`). They can't see the auditor's GPU time or Petri's own
judge calls.

## 0. One-time setup (about 10 minutes)

You need: Python 3.9+ (repo), Python 3.12 (Petri), a Modal account **with a payment method on file**
(Modal refuses every GPU without one), an OpenAI key, a Tinker key.

```bash
git clone https://github.com/nathanqiu07/AutoResearch && cd AutoResearch   # or: git checkout main && git pull
python3.12 -m venv ../.petri-env
../.petri-env/bin/pip install --prefer-binary eval/vendor/petri-v2.tar.gz modal tinker tinker-cookbook
../.petri-env/bin/modal setup                      # log in to YOUR Modal workspace
K=$(openssl rand -hex 24) && ../.petri-env/bin/modal secret create vllm-key VLLM_API_KEY=$K && echo "export VLLM_KEY=$K" >> ~/.zshrc
echo 'export OPENAI_API_KEY=<your OpenAI key>' >> ~/.zshrc
echo 'export TINKER_API_KEY=<your Tinker key>' >> ~/.zshrc
source ~/.zshrc
```

Free checks (no model calls):
```bash
python3 -m unittest discover -s tests -t .                       # must say OK
../.petri-env/bin/python -m unittest harness/petri/test_harness.py harness/test_tinker_proxy.py
```

## 1. Smoke test (about $1–2): Kimi answers through Tinker and returns raw reasoning
```bash
bash scripts/c2_pilot.sh smoke
```
Pass = it prints `"passed": true` and writes `results/smoke/c2_target_<date>.json`. If it fails, stop and send the output.

## 2. Baseline: stock Petri seeds (about $10–17). Optional if you run step 3
```bash
bash scripts/c2_pilot.sh baseline 12
```
Output: `results/e3b/pilot_stock_moonshotai_Kimi-K2.5_dev_n12_<date>.json`. **If stock awareness is below
about 0.4, stop:** the target barely notices tests, so there's nothing to reduce (results/prereg/E3b.json).
`baseline 6` halves the cost.

## 3. Control vs stock (about $20–30)
```bash
bash scripts/c2_pilot.sh control 12
```
This writes the plain-agent control seeds to `runs/petri/control_dev.jsonl`, then audits stock and control
in one report: `results/e3b/pilot_stock_vs_control_moonshotai_Kimi-K2.5_dev_n12_<date>.json`. The paired
per-seed difference is under `vs_stock.control`.

`TARGET=qwen bash scripts/c2_pilot.sh ...` runs the same steps on Qwen3-30B-A3B on Modal (the held-out
target) instead of Kimi.

## 4. After each run
- `../.petri-env/bin/modal app list`: nothing should still be running.
- Commit the results JSON and push. Post the numbers and the actual cost (Modal, OpenAI, Tinker dashboards)
  on the board: `python3 scripts/agentctl.py post "<subject>" "<body>" --to all`.

## If something breaks
- `deploy ... failed`: run the `modal deploy` line from `scripts/c2_pilot.sh` by hand to see Modal's error
  (usually billing).
- `tinker proxy failed to start`: check `TINKER_API_KEY` and that `tinker` and `tinker-cookbook` are installed in `../.petri-env`.
- Errored samples are reported and never averaged in. The auditor's first request after deploying waits several minutes while weights load.
