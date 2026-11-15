#!/bin/bash
# Same 18-audit design as launch_batch.sh, but the target is Kimi K2.6 via OpenRouter
# (raw reasoning exposed), wired the way scripts/c2_loop_evan.sh wires the Tinker proxy.
# PART=main: stock/synthme/icai/p2/p5 (these audits ran with the auditor on OpenAI's API before its credit ran out).
# PART=p8:   p8 only, auditor and Petri judge = the same gpt-5.1 reached through OpenRouter.
# Inspect reloads the workspace .env (overriding OPENAI_API_KEY), so OpenRouter is reached by explicit
# model ids, never by repointing OPENAI_BASE_URL.
cd '/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/AutoResearch'
set -a
source '/Users/giordanorogers/Documents/ChatGPT/AI Researcher Hackathon/.env'
set +a
OR=https://openrouter.ai/api/v1
export OPENAI_COMPAT_ENDPOINTS="{\"moonshotai/\": {\"base_url\": \"$OR\", \"key_env\": \"OPENROUTER_API_KEY\"}, \"openai/\": {\"base_url\": \"$OR\", \"key_env\": \"OPENROUTER_API_KEY\"}}"
export OPENAI_COMPAT_BASE_URL=$OR OPENAI_COMPAT_API_KEY=$OPENROUTER_API_KEY
export MODAL_BASE_URL=$OR MODAL_API_KEY=$OPENROUTER_API_KEY
export OPENAI_COMPAT_PLAIN_THINKING=headroom
export AUTORESEARCH_PETRI_CMD='uv run --no-project --with experiments/hubinger_seed63_cot_awareness/inputs/petri-0.1.0.tar.gz --with "openai==2.26.0" --with "inspect-ai==0.3.193" python harness/petri/run_audits.py'
SEED=experiments/hubinger_seed63_cot_awareness/inputs/seed63.jsonl
INP=experiments/hubinger_seed63_cot_awareness/inputs
CACHE=runs/petri/cache/hubinger_seed63_kimi26
mkdir -p $CACHE
COMMON=(--epochs 3 --mode dev --tools simulated --target "openai-compat:moonshotai/kimi-k2.6"
        --judge "openai-compat:openai/gpt-5.1" --max-turns 15 --max-cost 40 --workers 6
        --cache-dir $CACHE --petri-batch 18)
if [ "${PART:-main}" = p8 ]; then
  exec python3 scripts/c2_e3b.py \
    --condition p8=$SEED --auditor-prompt p8=$INP/auditor_prompt_p8.txt \
    --petri-auditor "openrouter/openai/gpt-5.1" --petri-judge "openrouter/openai/gpt-5.1" \
    "${COMMON[@]}" --out experiments/hubinger_seed63_cot_awareness/results_kimi26_p8.json
fi
exec python3 scripts/c2_e3b.py \
  --condition stock=$SEED \
  --condition synthme=$SEED --auditor-prompt synthme=$INP/auditor_prompt_synthme.txt \
  --condition icai=$SEED --auditor-prompt icai=$INP/auditor_prompt_icai.txt \
  --condition p2=$SEED --auditor-prompt p2=$INP/auditor_prompt_p2.txt \
  --condition p5=$SEED --auditor-prompt p5=$INP/auditor_prompt_p5.txt \
  --petri-auditor "openai/gpt-5.1" --petri-judge "openai/gpt-5.1" \
  "${COMMON[@]}" --out experiments/hubinger_seed63_cot_awareness/results_kimi26.json
