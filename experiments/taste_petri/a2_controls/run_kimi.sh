#!/usr/bin/env bash
# a2_controls on Kimi K2.6 (the E3b dev target): the same transcripts and probe prompts the haiku run used,
# answered by Kimi through harness/tinker_proxy.py, exactly as scripts/c2_pilot.sh reaches it. PAID (Tinker).
#
#   export TINKER_API_KEY=...        # your own key (or put TINKER_API_KEY=... in the repo's .env); never committed
#   bash experiments/taste_petri/a2_controls/run_kimi.sh
#
# Spend guards: TINKER_RUN_USD caps this run (default 15); the proxy answers HTTP 429 past it, those calls are
# recorded as errors, and a re-run resumes from the per-call cache without paying again. TINKER_BUDGET_USD is the
# lifetime cap kept in ~/.autoresearch (default: the run cap). WORKERS (default 16) parallel requests.
# VARIANTS sets which probes run and in what order (cheapest-to-decide first by default). The proxy stops on exit.
set -euo pipefail
cd "$(dirname "$0")/../../.."
REPO="$PWD"
PY="${AUTORESEARCH_PETRI_PYTHON:-$REPO/../.petri-env/bin/python}"   # has tinker + tinker_cookbook
if [ "$(uname)" = Darwin ] && [ -z "${SSL_CERT_FILE:-}" ] && [ -f /etc/ssl/cert.pem ]; then
  export SSL_CERT_FILE=/etc/ssl/cert.pem
fi
if [ -z "${TINKER_API_KEY:-}" ] && [ -f .env ]; then
  TINKER_API_KEY="$(grep -E '^TINKER_API_KEY=' .env | tail -1 | cut -d= -f2- | tr -d '"'"'"' ')"
  export TINKER_API_KEY
fi
: "${TINKER_API_KEY:?TINKER_API_KEY not set (export it, or add TINKER_API_KEY=... to .env)}"
RUN_USD="${TINKER_RUN_USD:-15}"
BUDGET_USD="${TINKER_BUDGET_USD:-$RUN_USD}"
WORKERS="${WORKERS:-16}"
VARIANTS="${VARIANTS:-binary pairwise placeholder_exact calibrated unprompted}"
PORT="${PORT:-8100}"
TARGET=openai-compat:moonshotai/Kimi-K2.6

PROXY_PID=""
cleanup() { [ -n "$PROXY_PID" ] && kill "$PROXY_PID" 2>/dev/null || true; }
trap cleanup EXIT
trap 'exit 143' TERM INT

mkdir -p runs/petri
"$PY" harness/tinker_proxy.py --port "$PORT" --model moonshotai/Kimi-K2.6 --budget-usd "$BUDGET_USD" \
   --run-budget-usd "$RUN_USD" --max-completion-tokens 9000 --usage-file runs/petri/tinker_usage_a2_controls.json \
   > runs/petri/tinker_proxy_a2_controls.log 2>&1 & PROXY_PID=$!
for _ in $(seq 60); do
  curl -sf -m 5 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break
  kill -0 "$PROXY_PID" 2>/dev/null || { echo "tinker proxy exited; see runs/petri/tinker_proxy_a2_controls.log"; exit 1; }
  sleep 2
done
echo "tinker proxy up on :$PORT (run cap \$$RUN_USD, lifetime cap \$$BUDGET_USD)"
export OPENAI_COMPAT_ENDPOINTS="{\"moonshotai/\": {\"base_url\": \"http://127.0.0.1:$PORT/v1\", \"key_env\": \"TINKER_PROXY_KEY\"}}"
export TINKER_PROXY_KEY=local
# K2.6 always thinks before answering; headroom adds 8000 tokens to each small max_tokens (billed on actual use).
export OPENAI_COMPAT_PLAIN_THINKING="${OPENAI_COMPAT_PLAIN_THINKING:-headroom}"

A2C=experiments/taste_petri/a2_controls/a2_controls.py
for tag in "" rep; do
  [ -f "experiments/taste_petri/a2_controls/transcripts${tag:+_$tag}.jsonl" ] || continue
  echo "== probes on transcripts${tag:+_$tag} ($VARIANTS)"
  # shellcheck disable=SC2086
  python3 "$A2C" probe --tag "$tag" --target "$TARGET" --variants $VARIANTS --workers "$WORKERS" --max-calls 4000
  python3 "$A2C" report --tag "$tag" --target "$TARGET"
done
echo "spend: runs/petri/tinker_usage_a2_controls.json"
