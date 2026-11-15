#!/bin/bash
cd '/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/AutoResearch'
set -a
source '/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/.env'
set +a
export AUTORESEARCH_PETRI_CMD='uv run --no-project --with experiments/hubinger_seed63_cot_awareness/inputs/petri-0.1.0.tar.gz --with "openai==2.26.0" --with "inspect-ai==0.3.193" python harness/petri/run_audits.py'
SEED=experiments/hubinger_seed63_cot_awareness/inputs/seed63.jsonl
INP=experiments/hubinger_seed63_cot_awareness/inputs
mkdir -p runs/petri/cache/hubinger_seed63_gpt51
exec python3 scripts/c2_e3b.py \
  --condition stock=$SEED \
  --condition synthme=$SEED --auditor-prompt synthme=$INP/auditor_prompt_synthme.txt \
  --condition icai=$SEED --auditor-prompt icai=$INP/auditor_prompt_icai.txt \
  --condition p2=$SEED --auditor-prompt p2=$INP/auditor_prompt_p2.txt \
  --condition p5=$SEED --auditor-prompt p5=$INP/auditor_prompt_p5.txt \
  --condition p8=$SEED --auditor-prompt p8=$INP/auditor_prompt_p8.txt \
  --epochs 3 --mode dev --tools simulated \
  --target "openai:gpt-5.1" --judge "openai:gpt-5.1" \
  --petri-auditor "openai/gpt-5.1" --petri-judge "openai/gpt-5.1" \
  --max-turns 15 --max-cost 40 --workers 6 \
  --cache-dir runs/petri/cache/hubinger_seed63_gpt51 --petri-batch 18 \
  --out experiments/hubinger_seed63_cot_awareness/results.json
