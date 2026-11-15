#!/usr/bin/env bash
# C2 stock Petri v2 baseline on the dev target (E3b). PAID: Modal GPU + Anthropic API.
#   bash scripts/c2_baseline.sh smoke      # 1 seed x 1 epoch, ~$3
#   bash scripts/c2_baseline.sh dev        # 12 dev seeds x 1 epoch, simulated tools, ~$30
#   bash scripts/c2_baseline.sh dev 5      # 12 dev seeds x 5 epochs, ~$130
#   bash scripts/c2_baseline.sh sandbox    # 12 dev seeds x 1 epoch, real Modal Sandbox tools, ~$30
# Models (configs/models.json): target Qwen/Qwen3-30B-A3B on Modal vLLM; Petri auditor
# anthropic/claude-sonnet-4-6; Petri judge + our J1 anthropic/claude-haiku-4-5.
set -euo pipefail
cd "$(dirname "$0")/.."
which_run="${1:-smoke}"; epochs="${2:-1}"
missing=()
[ -n "${ANTHROPIC_API_KEY:-}" ] || missing+=("ANTHROPIC_API_KEY (auditor + judges)")
[ -n "${OPENAI_COMPAT_BASE_URL:-}" ] || missing+=("OPENAI_COMPAT_BASE_URL (modal deploy harness/modal_vllm.py, plus /v1)")
[ -n "${OPENAI_COMPAT_API_KEY:-}" ] || missing+=("OPENAI_COMPAT_API_KEY (the vllm-key secret)")
[ -n "${AUTORESEARCH_PETRI_PYTHON:-}" ] || missing+=("AUTORESEARCH_PETRI_PYTHON (python of the Petri env, harness/README.md)")
if [ ${#missing[@]} -gt 0 ]; then printf 'missing: %s\n' "${missing[@]}"; exit 1; fi
export MODAL_BASE_URL="${MODAL_BASE_URL:-$OPENAI_COMPAT_BASE_URL}" MODAL_API_KEY="${MODAL_API_KEY:-$OPENAI_COMPAT_API_KEY}"
python3 -m autoresearch.research.models_config >/dev/null
tools=simulated; limit=(); out=results/e3b
case "$which_run" in
  smoke)   limit=(--limit 1); out=results/smoke ;;
  dev)     ;;
  sandbox) tools=sandbox ;;
  *) echo "usage: $0 smoke|dev|sandbox [epochs]"; exit 2 ;;
esac
stamp=$(date +%Y-%m-%d)
python3 scripts/c2_e3b.py --condition stock=data/petri/seeds_v2.jsonl --split dev --tools "$tools" \
  --epochs "$epochs" "${limit[@]}" --max-cost 200 --out "$out/c2_v2_dev_${tools}_${which_run}_e${epochs}_${stamp}.json"
