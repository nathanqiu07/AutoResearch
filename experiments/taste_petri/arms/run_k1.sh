#!/bin/bash
# Score every arm once (k=1, batched A2, full path), then the Petri-judge pass. Logs CLI calls to calls.log.
cd "$(dirname "$0")/../../.." || exit 1
A=experiments/taste_petri/arms
for arm in "$@"; do
  python3 experiments/taste_petri/proxy/proxy_eval.py --seeds $A/seeds/$arm.jsonl --condition $arm --samples 1 \
    --model haiku --out $A/runs/${arm}_k1.json | tee -a $A/proxy.log
  python3 -c "import json;d=json.load(open('$A/runs/${arm}_k1.json'));print('proxy $arm k1: cli_calls=%d n_ok=%d/%d'%(d['cli_calls'],d['summary']['n_ok'],d['summary']['n']))" >> $A/calls.log
  python3 $A/petri_judge.py $A/runs/${arm}_k1.json
done
