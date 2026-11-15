#!/usr/bin/env bash
# Agentic research loop (R1, taste_mode=model, researcher evan_hubinger) on the 12 E3b dev Petri seeds,
# then the final dev eval: stock vs control vs taste_real (stock/control audits reused from the pilot cache).
# Built from scripts/c2_pilot.sh (same proxy / auditor / budget / cleanup logic). PAID.
# Run from a code snapshot worktree; MAIN points at the main checkout for shared caches and outputs.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
MAIN="${MAIN:?set MAIN to the main checkout}"
PY="${AUTORESEARCH_PETRI_PYTHON:?}"; export AUTORESEARCH_PETRI_PYTHON="$PY"
MODAL="${MODAL_BIN:?}"
if [ "$(uname)" = Darwin ] && [ -z "${SSL_CERT_FILE:-}" ] && [ -f /etc/ssl/cert.pem ]; then export SSL_CERT_FILE=/etc/ssl/cert.pem; fi
STEP="${1:-all}"                       # all | loop | final
ITER="${ITERATIONS:-4}"; SAMPLES="${SAMPLES:-12}"; EVALS="${EVALS_PER_ITER:-3}"
REWRITE="${PETRI_REWRITE:-both}"         # what designs rewrite: seed | auditor | both
RUN_TAG="${RUN_TAG:?set RUN_TAG}"      # names the loop output dir, so 'final' can be re-run alone
LOOP_OUT="$MAIN/runs/loop/evan_hubinger_$RUN_TAG"
POOL_FILE="${POOL_FILE:-$HOME/.autoresearch/pool.json}"; export POOL_FILE
T_MODEL=moonshotai/Kimi-K2.6
TOKEN_CAP="${TINKER_TOKEN_CAP:-40000000}"
RUN_USD="${TINKER_RUN_USD:-40}"; MAX_MIN="${MAX_MINUTES:-150}"
H100_PER_HOUR="${H100_USD_PER_HOUR:-3.95}"; export H100_USD_PER_HOUR="$H100_PER_HOUR"
if [ -f "$POOL_FILE" ]; then POOL_ARGS=(--pool "$POOL_FILE"); else POOL_ARGS=(--budget-usd "${TINKER_BUDGET_USD:?}"); fi
: "${OPENAI_API_KEY:?}"; : "${VLLM_KEY:?}"
[ -f "$POOL_FILE" ] || : "${TINKER_API_KEY:?}"
export OPENAI_PRICE_PER_MTOK="${OPENAI_PRICE_PER_MTOK:-gpt-6-luna=0.10,0.50}"

GPUS=4
RUN_ID="c2-loop-$(date +%Y%m%dT%H%M%S)-$$"
PROXY_PID=""; WATCHDOG=""; MODAL_POOL_LABEL=""; DEPLOY_TS=""; LOG_PIDS=""
cleanup() {
  [ -n "$WATCHDOG" ] && kill "$WATCHDOG" 2>/dev/null || true
  [ -n "$PROXY_PID" ] && kill "$PROXY_PID" 2>/dev/null || true
  for p in $LOG_PIDS; do pkill -P "$p" 2>/dev/null || true; kill "$p" 2>/dev/null || true; done
  "$MODAL" app stop -y autoresearch-auditor >/dev/null 2>&1 || true
  if [ -n "$MODAL_POOL_LABEL" ]; then
    mins=0; [ -n "$DEPLOY_TS" ] && mins=$(awk -v s="$DEPLOY_TS" -v e="$(date +%s)" 'BEGIN { printf "%.2f", (e - s) / 60 }')
    python3 scripts/modal_pool.py close --run-id "$RUN_ID" --label "$MODAL_POOL_LABEL" --gpus "$GPUS" --minutes "$mins" || true
  fi
  [ -f "$LOOP_OUT/tinker_usage.json" ] && echo "Tinker usage this run: $(tr -d '\n ' < "$LOOP_OUT/tinker_usage.json")"
  python3 scripts/modal_pool.py status || true
  echo "stopped Modal apps and proxy"
}
trap cleanup EXIT
trap 'exit 143' TERM INT
( sleep $((MAX_MIN * 60)); echo "wall-clock limit ($MAX_MIN min) reached: stopping" >&2
  kill -TERM $$ 2>/dev/null; pkill -TERM -P $$ 2>/dev/null ) & WATCHDOG=$!

mkdir -p "$LOOP_OUT" runs/petri
PICK=$(python3 scripts/modal_pool.py pick --run-id "$RUN_ID" --gpus "$GPUS" --minutes "$MAX_MIN")
eval "$PICK"; export MODAL_PROFILE
[ "$MODAL_PROFILE" = david8dragon8 ] && { echo "refusing: pool picked David's workspace (last resort only)"; exit 1; }
"$MODAL" secret list 2>/dev/null | grep -q vllm-key || { echo "no vllm-key secret in $MODAL_PROFILE"; exit 1; }

deploy() {
  local out url
  APP="$1" MODEL="$2" GPU="$3" PARSER="$4" MAX_MODEL_LEN="$5" "$MODAL" run harness/modal_vllm.py::download --model "$2" >&2 \
    || { echo "weight download for $2 failed" >&2; exit 1; }
  out=$(APP="$1" MODEL="$2" GPU="$3" PARSER="$4" MAX_MODEL_LEN="$5" "$MODAL" deploy harness/modal_vllm.py 2>&1 || true)
  url=$(printf '%s\n' "$out" | grep -Eo 'https://[A-Za-z0-9.-]+\.modal\.run' | head -1)
  [ -n "$url" ] || { echo "deploy of $1 failed:" >&2; printf '%s\n' "$out" | tail -5 >&2; exit 1; }
  echo "$url/v1"
}
wait_ready() {
  local app="$1" url="$2" deadline=$(( $(date +%s) + $3 * 60 )) log="$LOOP_OUT/$1_$RUN_ID.log"
  ( while :; do "$MODAL" app logs "$app" >> "$log" 2>&1; sleep 5; done ) & LOG_PIDS="$LOG_PIDS $!"
  echo "waiting for $app (up to $3 min; log $log)..."
  while :; do
    curl -sf -m 15 -H "Authorization: Bearer $VLLM_KEY" "$url/models" >/dev/null 2>&1 && { echo "$app ready"; return 0; }
    grep -q "vllm exited with code" "$log" 2>/dev/null && { echo "$app: vLLM crashed" >&2; tail -15 "$log" >&2; exit 1; }
    [ "$(date +%s)" -ge "$deadline" ] && { echo "$app not ready after $3 min" >&2; tail -15 "$log" >&2; exit 1; }
    sleep 20
  done
}

"$PY" harness/tinker_proxy.py --port 8100 --model "$T_MODEL" --max-total-tokens "$TOKEN_CAP" \
   "${POOL_ARGS[@]}" --run-budget-usd "$RUN_USD" --usage-file "$LOOP_OUT/tinker_usage.json" & PROXY_PID=$!
sleep 3; kill -0 "$PROXY_PID" || { echo "tinker proxy failed to start"; exit 1; }
export OPENAI_COMPAT_ENDPOINTS="{\"moonshotai/\": {\"base_url\": \"http://127.0.0.1:8100/v1\", \"key_env\": \"TINKER_PROXY_KEY\"}}"
export TINKER_PROXY_KEY=local OPENAI_COMPAT_PLAIN_THINKING="${OPENAI_COMPAT_PLAIN_THINKING:-headroom}"
export OPENAI_COMPAT_BASE_URL=http://127.0.0.1:8100/v1 OPENAI_COMPAT_API_KEY=local
# the Petri harness reaches the target as openai-api/modal/<model> (configs/models.json petri.dev.target)
export MODAL_BASE_URL=http://127.0.0.1:8100/v1 MODAL_API_KEY=local
T_SPEC="openai-compat:$T_MODEL"

if [ -n "${AUDITOR_URL:-}" ] && curl -sf -m 15 -H "Authorization: Bearer $VLLM_KEY" "$AUDITOR_URL/models" >/dev/null 2>&1; then
  A_URL="$AUDITOR_URL"; DEPLOY_TS=$(date +%s)   # reuse an auditor that is already up (its earlier minutes are closed by whoever started it)
  echo "reusing auditor at $A_URL"
else
  echo "deploying auditor in Modal workspace $MODAL_POOL_LABEL ($MODAL_PROFILE)..."
  A_URL=$(deploy autoresearch-auditor Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 H100:4 none 65536); DEPLOY_TS=$(date +%s)
  wait_ready autoresearch-auditor "$A_URL" "${READY_MINUTES:-40}"
fi
export MODALAUD_BASE_URL="$A_URL" MODALAUD_API_KEY="$VLLM_KEY"
export PETRI_MAX_CONNECTIONS="${PARALLEL:-40}" PETRI_MAX_SAMPLES="${PARALLEL:-40}"

MODELS=(--generator openai:gpt-6-luna --judge openai:gpt-5.1 --target "$T_SPEC")
if [ "$STEP" = all ] || [ "$STEP" = loop ]; then
  echo "== loop: evan_hubinger, $ITER iterations x $EVALS evals, $SAMPLES audits per eval, rewrite=$REWRITE"
  PYTHONUNBUFFERED=1 python3 -m autoresearch.cli research --setting agentic --mode dev --petri-seeds data/petri/seeds_v2.jsonl \
    --researcher evan_hubinger --taste-mode model --petri-rewrite "$REWRITE" "${MODELS[@]}" ${LOOP_EXTRA:-} \
    --iterations "$ITER" --samples "$SAMPLES" --evals-per-iter "$EVALS" --parallel-evals --workers "${SCORE_WORKERS:-16}" \
    --max-cost "${LOOP_MAX_COST:-60}" --max-seconds $((MAX_MIN * 60)) --max-calls 50000 \
    --memory "$LOOP_OUT/memory" --out "$LOOP_OUT/report" 2>&1 | tee "$LOOP_OUT/loop.log"
fi
if [ "$STEP" = all ] || [ "$STEP" = final ]; then
  REPORT=$(ls -t "$LOOP_OUT"/report/*.json 2>/dev/null | grep -v _environments | head -1)
  [ -n "$REPORT" ] || { echo "no loop report in $LOOP_OUT/report"; exit 1; }
  echo "== export taste_real (dev) from the loop's best design ($REPORT)"
  PYTHONUNBUFFERED=1 python3 -m autoresearch.cli export-seeds --report "$REPORT" --condition taste_real --split dev \
    --petri-seeds data/petri/seeds_v2.jsonl "${MODELS[@]}" --out "$LOOP_OUT/taste_real_dev.jsonl" 2>&1 | tee "$LOOP_OUT/export.log"
  echo "== final dev eval: stock vs control vs taste_real"
  PYTHONUNBUFFERED=1 python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl \
    --condition control="$MAIN/runs/petri/control_dev.jsonl" --condition taste_real="$LOOP_OUT/taste_real_dev.jsonl" \
    --split dev --limit 12 --epochs 1 --tools simulated --target "$T_SPEC" --judge openai:gpt-5.1 \
    --petri-auditor openai-api/modalaud/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 --petri-judge openai/gpt-5.1 \
    --max-cost 20 --workers "${SCORE_WORKERS:-16}" --petri-batch 36 \
    --cache-dir "$MAIN/runs/petri/cache/control_moonshotai_Kimi-K2.6_n12" \
    --out "$MAIN/results/e3b/loop_evan_hubinger_rewrite-${REWRITE}_stock_control_taste_moonshotai_Kimi-K2.6_dev_n12_$(date +%Y-%m-%d).json" \
    2>&1 | tee "$LOOP_OUT/final.log"
fi
