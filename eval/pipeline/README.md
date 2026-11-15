# Eval-awareness pipeline

Measures how often a target model realizes it is being tested, across four conditions: Petri stock, plain-agent control, taste system with a mismatched profile, and taste system with the real profile. Main target is Kimi K2.5 on Tinker (sponsor credits). config_sonnet45.yaml is an optional Sonnet 4.5 extended-thinking target, off by default, that needs an Anthropic key.

## Where things run

Everything runs from your own laptop terminal, in this folder. Your laptop only sends API calls; the models live elsewhere. The Kimi target runs on Tinker. The auditor and the plain-agent rewriter run on Modal (modal_vllm.py serves Qwen3-235B there, scaling to zero when idle), and the judges can too if OpenAI credits don't arrive. That keeps Tinker credits for the target, where full chain of thought matters.

## Setup

    pip install git+https://github.com/meridianlabs-ai/inspect_petri@petri-v2 pandas scikit-learn matplotlib pyyaml
    export TINKER_API_KEY=...  TINKER_BASE_URL=https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1
    export OPENAI_API_KEY=...        # GPT-5 judges, if OpenAI credits come through
    pip install modal && modal setup && modal secret create vllm-key VLLM_API_KEY=<random string>
    modal deploy modal_vllm.py       # prints the endpoint URL
    export MODAL_BASE_URL=<that URL>/v1  MODAL_API_KEY=<same random string>
    python setup_stock.py --seeds-dir ../petri-setup/seeds --auditor ../petri-setup/stock_auditor_prompt.txt

Fill in the model ids in config.yaml first. Tinker's OpenAI-compatible endpoint wants a tinker:// sampler path as the model name, not the Hugging Face name, and it is in beta, so do one smoke test before the full run.

## Control smoke test (one seed, about 15 minutes)

    python control.py --split dev --seeds seed_48 --rounds 1
    python run_petri.py --conditions stock control --split dev --seeds seed_48 --epochs 1
    python extract.py && python eab_judge.py && python posthoc.py
    python score.py --split dev

If that produces out/config/results_dev.csv with numbers for stock and control, the whole chain works.

## Running it

    python run_petri.py --conditions stock --split dev --seeds seed_48 --epochs 1   # smoke test
    python run_petri.py --conditions stock --split dev                              # stock baseline, 12 seeds x 5
    python control.py --split dev --rounds 3 && python control.py --split hidden    # plain-agent control
    python run_petri.py --conditions stock control --split hidden
    python extract.py && python eab_judge.py && python posthoc.py
    python posthoc.py --real real_transcripts.jsonl                                 # negatives for the AUROC
    python score.py --split hidden

The taste system only has to write its rewrites into conditions/taste_real/<split>/<seed_id>/seed.txt and auditor_prompt.txt (and taste_mismatched likewise), using prompts/rewrite_task.txt and the same number of rounds as the control. Every step skips work already done, so it is safe to re-run after a crash.

## What comes out

out/<config>/results_<split>.csv has, per condition, the mean Petri eval-awareness score (1 to 10), the share of runs at 7 or above, the EvalAwareBench judge's aware rate on reasoning and on visible output and the gap between them, the safety-test share, mean post-hoc P(eval), and the AUROC against real transcripts. It also has paired differences against stock and against the control, each with a 95% bootstrap CI over seeds and a flag for whether the CI excludes zero. charts_<split>/ has one bar chart per metric, and demo_<split>.md has the seeds with the biggest stock-versus-ours drop, with the judge's verbatim quotes.

## Things that bite

Petri scores any judge response it can't parse as 1 (not aware), which would quietly flatter whichever condition breaks the judge more. extract.py turns those into missing values and reports how many there were. A rewritten auditor prompt has to keep its five {placeholders}, which control.py and run_petri.py both check. The EvalAwareBench judge is run without the original code's 200-character tool-output cut. tests/ has offline tests that use mock models and need no keys.
