#!/usr/bin/env bash
# C2 pilot: stock Petri v2 baseline and plain-agent control, 1 run x N dev seeds. PAID.
#   bash scripts/c2_pilot.sh smoke         # target answers + returns raw reasoning, 5 samples (~$2)
#   bash scripts/c2_pilot.sh baseline [N]  # stock seeds only, N dev seeds (default 12)
#   bash scripts/c2_pilot.sh control [N]   # plain-agent rewrites, then stock vs control in one report
# Main target (Nathan + Abhi, 2026-11-15): Kimi K2.5 on Tinker, through harness/tinker_proxy.py
# (hard token cap). TARGET=qwen uses Qwen3-30B-A3B on Modal instead. Auditor: Qwen3-235B on Modal
# (4xH100). Judges: openai:gpt-5.1 (ours and Petri's). Modal apps and the proxy stop on exit, even on error.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
PY="${AUTORESEARCH_PETRI_PYTHON:-$REPO/../.petri-env/bin/python}"; export AUTORESEARCH_PETRI_PYTHON="$PY"
MODAL="${MODAL_BIN:-$REPO/../.petri-env/bin/modal}"
step="${1:-smoke}"; n="${2:-12}"; target="${TARGET:-kimi}"
TOKEN_CAP="${TINKER_TOKEN_CAP:-10000000}"   # proxy refuses requests past this many Tinker tokens
: "${OPENAI_API_KEY:?OPENAI_API_KEY not set (judge)}"
: "${VLLM_KEY:?set VLLM_KEY to the same random string as the Modal secret vllm-key}"
export OPENAI_PRICE_PER_MTOK="${OPENAI_PRICE_PER_MTOK:-gpt-6-luna=0.10,0.50}"   # Nathan: aggregator price, confirm
H100_PER_HOUR=3.95   # Modal list price per H100-hour at the time of writing; check modal.com/pricing
PROXY_PID=""
cleanup() { [ -n "$PROXY_PID" ] && kill "$PROXY_PID" 2>/dev/null || true
            "$MODAL" app stop autoresearch-vllm >/dev/null 2>&1 || true
            "$MODAL" app stop autoresearch-auditor >/dev/null 2>&1 || true
            [ -f runs/petri/tinker_usage.json ] && echo "Tinker usage: $(cat runs/petri/tinker_usage.json | tr -d '\n ')"
            echo "stopped Modal apps and proxy"; }
trap cleanup EXIT
deploy() {  # app model gpu parser maxlen -> base URL
  local url
  url=$(APP="$1" MODEL="$2" GPU="$3" PARSER="$4" MAX_MODEL_LEN="$5" "$MODAL" deploy harness/modal_vllm.py 2>&1 \
        | grep -Eo 'https://[A-Za-z0-9.-]+\.modal\.run' | head -1)
  [ -n "$url" ] || { echo "deploy of $1 failed: run the modal deploy line by hand to see why" >&2; exit 1; }
  echo "$url/v1"
}
mkdir -p runs/petri
if [ "$target" = kimi ]; then
  : "${TINKER_API_KEY:?TINKER_API_KEY not set (Kimi K2.5 runs on Tinker)}"
  T_MODEL=moonshotai/Kimi-K2.5
  "$PY" harness/tinker_proxy.py --port 8100 --model "$T_MODEL" --max-total-tokens "$TOKEN_CAP" \
     --usage-file runs/petri/tinker_usage.json & PROXY_PID=$!
  sleep 3; kill -0 "$PROXY_PID" || { echo "tinker proxy failed to start"; exit 1; }
  T_URL=http://127.0.0.1:8100/v1; T_KEY=local
  export OPENAI_COMPAT_ENDPOINTS="{\"moonshotai/\": {\"base_url\": \"$T_URL\", \"key_env\": \"TINKER_PROXY_KEY\"}}"
  export TINKER_PROXY_KEY=local
else
  T_MODEL=Qwen/Qwen3-30B-A3B
  echo "deploying target (Qwen3-30B-A3B, 1xH100)..."
  T_URL=$(deploy autoresearch-vllm "$T_MODEL" H100:1 qwen3 32768); T_KEY="$VLLM_KEY"
  export OPENAI_COMPAT_USD_PER_HOUR=$H100_PER_HOUR
fi
export OPENAI_COMPAT_BASE_URL="$T_URL" OPENAI_COMPAT_API_KEY="$T_KEY" MODAL_BASE_URL="$T_URL" MODAL_API_KEY="$T_KEY"
T_SPEC="openai-compat:$T_MODEL"; tag=$(echo "$T_MODEL" | tr '/' '_')
stamp=$(date +%Y-%m-%d)
auditor() {
  echo "deploying auditor (Qwen3-235B-A22B-Instruct-2507-FP8, 4xH100)..."
  A_URL=$(deploy autoresearch-auditor Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 H100:4 none 65536)
  export MODALAUD_BASE_URL="$A_URL" MODALAUD_API_KEY="$VLLM_KEY"
}
E3B=(--split dev --limit "$n" --epochs 1 --tools simulated --target "$T_SPEC" --judge openai:gpt-5.1
     --petri-auditor openai-api/modalaud/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 --petri-judge openai/gpt-5.1 --max-cost 15)
case "$step" in
  smoke)
    python3 scripts/c2_smoke_target.py --n 5 --target "$T_SPEC" --judge openai:gpt-5.1 --max-cost 3 ;;
  baseline)
    auditor
    python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl "${E3B[@]}" \
      --out "results/e3b/pilot_stock_${tag}_dev_n${n}_${stamp}.json" ;;
  control)
    python3 scripts/c2_make_control.py --split dev --out runs/petri/control_dev.jsonl
    auditor
    python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl --condition control=runs/petri/control_dev.jsonl \
      "${E3B[@]}" --out "results/e3b/pilot_stock_vs_control_${tag}_dev_n${n}_${stamp}.json" ;;
  *) echo "usage: [TARGET=kimi|qwen] $0 smoke|baseline|control [N]"; exit 2 ;;
esac
