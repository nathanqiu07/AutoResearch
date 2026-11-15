#!/usr/bin/env bash
# C2 pilot: stock Petri v2 baseline and plain-agent control, 1 run x N dev seeds. PAID except preflight.
#   bash scripts/c2_pilot.sh preflight     # free: which Tinker models each account serves, ledger balances
#   bash scripts/c2_pilot.sh smoke         # target answers + returns raw reasoning, 5 samples (~$2)
#   bash scripts/c2_pilot.sh baseline [N]  # stock seeds only, N dev seeds (default 12)
#   bash scripts/c2_pilot.sh control [N]   # plain-agent rewrites, then stock vs control in one report
#   bash scripts/c2_pilot.sh screen [RUNS] # stock runs on the 29-seed screen pool (data/petri/screen_pool.jsonl), RUNS
#                                          # per seed (default 2); then scripts/c2_screen_select.py keeps the seeds Kimi notices.
#                                          # MAX_TURNS sets audit length (default: configs/models.json petri.max_turns)
# Main target (Nathan, 2026-11-15): Kimi K2.6 on Tinker, through harness/tinker_proxy.py (K2.5 is deprecated there).
# TINKER_MODEL overrides the Tinker model (default moonshotai/Kimi-K2.6; preflight lists what each
# account serves). TARGET=qwen uses Qwen3-30B-A3B on Modal instead.
# Auditor: Qwen3-235B on Modal (4xH100). Judges: openai:gpt-5.1 (ours and Petri's).
#
# Spend guards (Nathan, 2026-11-15: stay inside the team's credits; pooled across teammates' accounts):
# - Pool file ~/.autoresearch/pool.json (POOL_FILE) lists Tinker accounts (key env var + lifetime budget)
#   and Modal workspaces (profile + lifetime budget); see scripts/modal_pool.py. Ledgers live in
#   ~/.autoresearch and persist across runs. Without a pool file: TINKER_BUDGET_USD and MODAL_BUDGET_USD
#   (required) for your own account and active Modal profile.
# - Per step: TINKER_RUN_USD (Tinker cap for this step) and MAX_MINUTES (wall clock; when it passes the
#   step is killed and every Modal app stopped). Defaults: smoke $3/20 min, baseline $15/150, control $25/240.
# - Modal apps and the proxy stop on exit, even on error or when the wall-clock limit fires.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
PY="${AUTORESEARCH_PETRI_PYTHON:-$REPO/../.petri-env/bin/python}"; export AUTORESEARCH_PETRI_PYTHON="$PY"
MODAL="${MODAL_BIN:-$REPO/../.petri-env/bin/modal}"
# python.org builds on macOS ship without a CA bundle, so every urllib HTTPS call (OpenAI judge and
# generator) fails CERTIFICATE_VERIFY_FAILED. Use the system bundle unless one is already set.
if [ "$(uname)" = Darwin ] && [ -z "${SSL_CERT_FILE:-}" ] && [ -f /etc/ssl/cert.pem ]; then
  export SSL_CERT_FILE=/etc/ssl/cert.pem
fi
step="${1:-smoke}"; n="${2:-12}"; target="${TARGET:-kimi}"
POOL_FILE="${POOL_FILE:-$HOME/.autoresearch/pool.json}"; export POOL_FILE
T_MODEL_TINKER="${TINKER_MODEL:-moonshotai/Kimi-K2.6}"
TOKEN_CAP="${TINKER_TOKEN_CAP:-10000000}"   # older per-run token cap, still enforced by the proxy
H100_PER_HOUR="${H100_USD_PER_HOUR:-3.95}"; export H100_USD_PER_HOUR="$H100_PER_HOUR"   # Modal list price; check modal.com/pricing

if [ -f "$POOL_FILE" ]; then POOL_ARGS=(--pool "$POOL_FILE")
else POOL_ARGS=(--budget-usd "${TINKER_BUDGET_USD:-}"); fi

if [ "$step" = preflight ]; then
  if [ -f "$POOL_FILE" ]; then echo "pool file: $POOL_FILE"; LIST_ARGS=(--pool "$POOL_FILE")
  else echo "no pool file: single account (TINKER_BUDGET_USD, MODAL_BUDGET_USD)"; LIST_ARGS=(); fi
  "$PY" harness/tinker_proxy.py --list-models ${LIST_ARGS[@]+"${LIST_ARGS[@]}"} | tr ',' '\n' | grep -iE '^\[|kimi' || true
  echo "requested Tinker model: $T_MODEL_TINKER"
  python3 scripts/modal_pool.py status
  exit 0
fi

case "$step" in
  smoke)    RUN_USD="${TINKER_RUN_USD:-3}";  MAX_MIN="${MAX_MINUTES:-20}" ;;
  baseline) RUN_USD="${TINKER_RUN_USD:-15}"; MAX_MIN="${MAX_MINUTES:-150}" ;;
  control)  RUN_USD="${TINKER_RUN_USD:-25}"; MAX_MIN="${MAX_MINUTES:-240}" ;;
  screen)   RUN_USD="${TINKER_RUN_USD:-15}"; MAX_MIN="${MAX_MINUTES:-300}" ;;
  *) echo "usage: [TARGET=kimi|qwen] $0 preflight|smoke|baseline|control|screen [N]"; exit 2 ;;
esac
: "${OPENAI_API_KEY:?OPENAI_API_KEY not set (judge)}"
export OPENAI_PRICE_PER_MTOK="${OPENAI_PRICE_PER_MTOK:-gpt-6-luna=0.10,0.50}"   # Nathan: aggregator price, confirm

# Modal GPUs this step deploys: the auditor (4) for baseline/control, the Qwen target (1) when TARGET=qwen.
GPUS=0
[ "$step" != smoke ] && GPUS=$((GPUS + 4))
[ "$target" = qwen ] && GPUS=$((GPUS + 1))
RUN_ID="c2-$step-$(date +%Y%m%dT%H%M%S)-$$"
PROXY_PID=""; WATCHDOG=""; MODAL_POOL_LABEL=""; PICK_TS=""; DEPLOY_TS=""; LOG_PIDS=""
cleanup() {
  [ -n "$WATCHDOG" ] && kill "$WATCHDOG" 2>/dev/null || true
  [ -n "$PROXY_PID" ] && kill "$PROXY_PID" 2>/dev/null || true
  for p in $LOG_PIDS; do pkill -P "$p" 2>/dev/null || true; kill "$p" 2>/dev/null || true; done
  if [ "$GPUS" -gt 0 ]; then
    "$MODAL" app stop -y autoresearch-vllm >/dev/null 2>&1 || true   # -y: without a TTY it asks and aborts
    "$MODAL" app stop -y autoresearch-auditor >/dev/null 2>&1 || true
  fi
  if [ -n "$MODAL_POOL_LABEL" ]; then
    # GPUs bill from the first deploy (containers start on the first request); nothing deployed, $0
    mins=0; [ -n "$DEPLOY_TS" ] && mins=$(awk -v s="$DEPLOY_TS" -v e="$(date +%s)" 'BEGIN { printf "%.2f", (e - s) / 60 }')
    python3 scripts/modal_pool.py close --run-id "$RUN_ID" --label "$MODAL_POOL_LABEL" --gpus "$GPUS" --minutes "$mins" || true
  fi
  [ -f runs/petri/tinker_usage.json ] && echo "Tinker usage this run: $(tr -d '\n ' < runs/petri/tinker_usage.json)"
  python3 scripts/modal_pool.py status || true
  echo "stopped Modal apps and proxy"
}
trap cleanup EXIT
trap 'exit 143' TERM INT

# Wall-clock limit: TERM to this script, then to its children, so the EXIT trap stops every Modal app.
( sleep $((MAX_MIN * 60)); echo "wall-clock limit ($MAX_MIN min) reached: stopping" >&2
  kill -TERM $$ 2>/dev/null; pkill -TERM -P $$ 2>/dev/null ) & WATCHDOG=$!

if [ "$GPUS" -gt 0 ]; then
  : "${VLLM_KEY:?set VLLM_KEY to the same random string as the Modal secret vllm-key}"
  PICK=$(python3 scripts/modal_pool.py pick --run-id "$RUN_ID" --gpus "$GPUS" --minutes "$MAX_MIN")
  eval "$PICK"; PICK_TS=$(date +%s); export MODAL_PROFILE
  "$MODAL" secret list 2>/dev/null | grep -q vllm-key \
    || { echo "Modal workspace $MODAL_POOL_LABEL (profile $MODAL_PROFILE) has no vllm-key secret: $MODAL secret create vllm-key VLLM_API_KEY=\$VLLM_KEY"; exit 1; }
fi

deploy() {  # app model gpu parser maxlen -> base URL
  local out url
  # weights first, on a CPU container: a GPU never waits on a download (cached files are only checked)
  echo "fetching $2 weights into the hf-cache volume (CPU)..." >&2
  APP="$1" MODEL="$2" GPU="$3" PARSER="$4" MAX_MODEL_LEN="$5" "$MODAL" run harness/modal_vllm.py::download --model "$2" >&2 \
    || { echo "weight download for $2 failed" >&2; exit 1; }
  out=$(APP="$1" MODEL="$2" GPU="$3" PARSER="$4" MAX_MODEL_LEN="$5" "$MODAL" deploy harness/modal_vllm.py 2>&1 || true)
  url=$(printf '%s\n' "$out" | grep -Eo 'https://[A-Za-z0-9.-]+\.modal\.run' | head -1)
  [ -n "$url" ] || { echo "deploy of $1 failed. Modal said:" >&2; printf '%s\n' "$out" | tail -5 >&2; exit 1; }
  echo "$url/v1"
}
# Poll the server until it answers, so audits never start against a server that is still loading or
# has died. vLLM exiting is caught from the app log (harness/modal_vllm.py prints the marker and ends
# the container), so a crash costs a minute or two of GPUs, not the 30-minute startup timeout.
wait_ready() {  # app base_url minutes
  local app="$1" url="$2" deadline=$(( $(date +%s) + $3 * 60 )) log="runs/petri/$1_$RUN_ID.log"
  # `modal app logs` can exit after the image build output, so keep restarting it
  ( while :; do "$MODAL" app logs "$app" >> "$log" 2>&1; sleep 5; done ) & LOG_PIDS="$LOG_PIDS $!"
  echo "waiting for $app to load (up to $3 min; log $log)..."
  while :; do
    curl -sf -m 15 -H "Authorization: Bearer $VLLM_KEY" "$url/models" >/dev/null 2>&1 && { echo "$app ready"; return 0; }
    if grep -q "vllm exited with code" "$log" 2>/dev/null; then
      echo "$app: vLLM crashed while starting. Last lines of its log:" >&2; grep -v '^[[:space:]]*$' "$log" | tail -15 >&2; exit 1
    fi
    if [ "$(date +%s)" -ge "$deadline" ]; then
      echo "$app not ready after $3 min. Last lines of its log:" >&2; grep -v '^[[:space:]]*$' "$log" | tail -15 >&2; exit 1
    fi
    sleep 20
  done
}
mkdir -p runs/petri
if [ "$target" = kimi ]; then
  [ -f "$POOL_FILE" ] || : "${TINKER_API_KEY:?TINKER_API_KEY not set (Kimi runs on Tinker)}"
  [ -f "$POOL_FILE" ] || : "${TINKER_BUDGET_USD:?no pool file: set TINKER_BUDGET_USD (lifetime Tinker budget for your account)}"
  T_MODEL="$T_MODEL_TINKER"
  "$PY" harness/tinker_proxy.py --port 8100 --model "$T_MODEL" --max-total-tokens "$TOKEN_CAP" \
     "${POOL_ARGS[@]}" --run-budget-usd "$RUN_USD" --usage-file runs/petri/tinker_usage.json & PROXY_PID=$!
  sleep 3; kill -0 "$PROXY_PID" || { echo "tinker proxy failed to start"; exit 1; }
  T_URL=http://127.0.0.1:8100/v1; T_KEY=local
  export OPENAI_COMPAT_ENDPOINTS="{\"moonshotai/\": {\"base_url\": \"$T_URL\", \"key_env\": \"TINKER_PROXY_KEY\"}}"
  export TINKER_PROXY_KEY=local
  # K2.6 always thinks. Our probe and judge-style calls ask for ~300 tokens, which it spends thinking
  # before any JSON; headroom adds 8000 (billed on actual tokens, not the cap).
  export OPENAI_COMPAT_PLAIN_THINKING="${OPENAI_COMPAT_PLAIN_THINKING:-headroom}"
else
  T_MODEL=Qwen/Qwen3-30B-A3B
  echo "deploying target (Qwen3-30B-A3B, 1xH100)..."
  T_URL=$(deploy autoresearch-vllm "$T_MODEL" H100:1 qwen3 32768); T_KEY="$VLLM_KEY"; DEPLOY_TS=$(date +%s)
  wait_ready autoresearch-vllm "$T_URL" "${READY_MINUTES:-30}"
  export OPENAI_COMPAT_USD_PER_HOUR=$H100_PER_HOUR
fi
export OPENAI_COMPAT_BASE_URL="$T_URL" OPENAI_COMPAT_API_KEY="$T_KEY" MODAL_BASE_URL="$T_URL" MODAL_API_KEY="$T_KEY"
T_SPEC="openai-compat:$T_MODEL"; tag=$(echo "$T_MODEL" | tr '/' '_')
stamp=$(date +%Y-%m-%d)
auditor() {
  echo "deploying auditor (Qwen3-235B-A22B-Instruct-2507-FP8, 4xH100) in Modal workspace $MODAL_POOL_LABEL..."
  A_URL=$(deploy autoresearch-auditor Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 H100:4 none 65536)
  [ -n "$DEPLOY_TS" ] || DEPLOY_TS=$(date +%s)
  # first load in a workspace downloads ~240 GB of weights; later loads read the hf-cache volume
  wait_ready autoresearch-auditor "$A_URL" "${READY_MINUTES:-40}"
  export MODALAUD_BASE_URL="$A_URL" MODALAUD_API_KEY="$VLLM_KEY"
}
E3B=(--split dev --limit "$n" --epochs 1 --tools simulated --target "$T_SPEC" --judge openai:gpt-5.1
     --petri-auditor openai-api/modalaud/Qwen/Qwen3-235B-A22B-Instruct-2507-FP8 --petri-judge openai/gpt-5.1 --max-cost 15
     --cache-dir "runs/petri/cache/${step}_${tag}_n${n}")   # resume: re-running a step skips finished audits
[ -n "${MAX_TURNS:-}" ] && E3B+=(--max-turns "$MAX_TURNS")
# Parallelism: audits at once (PARALLEL, default 32; the auditor's vLLM takes 64 concurrent requests) and
# scoring threads for our judges (SCORE_WORKERS, default 16). Was 8 and 4: the pilot ran 24 audits in 32 min.
export PETRI_MAX_CONNECTIONS="${PARALLEL:-32}" PETRI_MAX_SAMPLES="${PARALLEL:-32}"
E3B+=(--workers "${SCORE_WORKERS:-16}")
case "$step" in
  smoke)
    python3 scripts/c2_smoke_target.py --n 5 --target "$T_SPEC" --judge openai:gpt-5.1 --max-cost 3 ;;
  baseline)
    auditor
    python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl "${E3B[@]}" \
      --out "results/e3b/pilot_stock_${tag}_dev_n${n}_${stamp}.json" ;;
  control)
    # generated once and reused, so a retry audits the same control seeds (and hits the audit cache)
    if [ ! -s runs/petri/control_dev.jsonl ] || [ -n "${CONTROL_REGEN:-}" ]; then
      python3 scripts/c2_make_control.py --split dev --out runs/petri/control_dev.jsonl
    else
      echo "reusing runs/petri/control_dev.jsonl (CONTROL_REGEN=1 makes new control seeds)"
    fi
    auditor
    python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl --condition control=runs/petri/control_dev.jsonl \
      "${E3B[@]}" --out "results/e3b/pilot_stock_vs_control_${tag}_dev_n${n}_${stamp}.json" ;;
  screen)
    # N = runs per seed here; all 29 pool seeds; split filter off (pool rows are split "screen")
    auditor
    out="results/e3b/screen_stock_${tag}_pool29_r${n}_t${MAX_TURNS:-cfg}_${stamp}.json"
    python3 scripts/c2_e3b.py --condition stock=data/petri/screen_pool.jsonl "${E3B[@]}" --split all --limit 0 --epochs "$n" \
      --out "$out"
    python3 scripts/c2_screen_select.py "$out" --out data/petri/seeds_screened.jsonl ;;
esac
