#!/usr/bin/env bash
# C2 pilot: stock Petri v2 baseline, 1 run x N dev seeds, on the Qwen3-30B dev target.
# PAID (Modal GPUs + a little OpenAI). Abhi approved, hard cap ~$15.
#   bash scripts/c2_pilot.sh smoke         # deploy the target, 5-sample reasoning smoke (~$2), stop
#   bash scripts/c2_pilot.sh baseline [N]  # deploy target + auditor, N dev seeds (default 12), stop
# Pilot-only lineup (configs/models.json is not changed): auditor Qwen3-235B on Modal (4xH100),
# our judge + Petri's judge openai:gpt-5. Both Modal apps are stopped on exit, even on error.
set -euo pipefail
cd "$(dirname "$0")/.."
MODAL="${MODAL_BIN:-modal}"
command -v "$MODAL" >/dev/null || MODAL="$(dirname "$0")/../../.petri-env/bin/modal"
step="${1:-smoke}"; n="${2:-12}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY not set (judge)}"
: "${VLLM_KEY:?set VLLM_KEY to the same random string as the Modal secret vllm-key}"
export AUTORESEARCH_PETRI_PYTHON="${AUTORESEARCH_PETRI_PYTHON:-$PWD/../.petri-env/bin/python}"
export OPENAI_PRICE_PER_MTOK="${OPENAI_PRICE_PER_MTOK:-gpt-6-luna=0.10,0.50}"   # Nathan: aggregator price, confirm on openai.com/pricing
H100_PER_HOUR=3.95   # Modal list price per H100-hour at the time of writing; check modal.com/pricing
stop_all() { "$MODAL" app stop autoresearch-vllm >/dev/null 2>&1 || true
             "$MODAL" app stop autoresearch-auditor >/dev/null 2>&1 || true
             echo "stopped Modal apps"; }
trap stop_all EXIT
deploy() {  # app model gpu parser maxlen -> prints base URL
  local url
  url=$(APP="$1" MODEL="$2" GPU="$3" PARSER="$4" MAX_MODEL_LEN="$5" "$MODAL" deploy harness/modal_vllm.py 2>&1 \
        | grep -Eo 'https://[A-Za-z0-9.-]+\.modal\.run' | head -1)
  [ -n "$url" ] || { echo "deploy of $1 failed" >&2; exit 1; }
  echo "$url/v1"
}
echo "deploying target (Qwen3-30B-A3B, 1xH100)..."
T_URL=$(deploy autoresearch-vllm Qwen/Qwen3-30B-A3B H100:1 qwen3 32768)
export OPENAI_COMPAT_BASE_URL="$T_URL" OPENAI_COMPAT_API_KEY="$VLLM_KEY" OPENAI_COMPAT_USD_PER_HOUR=$H100_PER_HOUR
export MODAL_BASE_URL="$T_URL" MODAL_API_KEY="$VLLM_KEY"
stamp=$(date +%Y-%m-%d)
case "$step" in
  smoke)
    python3 scripts/c2_smoke_target.py --n 5 --judge openai:gpt-5 --max-cost 3 ;;
  baseline)
    echo "deploying auditor (Qwen3-235B-A22B-Instruct-2507-FP8, 4xH100)..."
    A_URL=$(deploy autoresearch-auditor Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 H100:4 none 65536)
    export MODALAUD_BASE_URL="$A_URL" MODALAUD_API_KEY="$VLLM_KEY"
    python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl --split dev --limit "$n" --epochs 1 \
      --tools simulated --judge openai:gpt-5 \
      --petri-auditor openai-api/modalaud/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 --petri-judge openai/gpt-5 \
      --max-cost 15 --out "results/e3b/pilot_stock_qwen3-30b_dev_n${n}_${stamp}.json" ;;
  *) echo "usage: $0 smoke|baseline [N]"; exit 2 ;;
esac
