# Petri 2.0 setup (stock baseline)

Install: `pip install git+https://github.com/meridianlabs-ai/inspect_petri@petri-v2` (Python 3.11+). Keys: ANTHROPIC_API_KEY, OPENAI_API_KEY.

Smoke test, one stock dev seed:

    inspect eval petri/audit \
      -T seed_instructions=seeds/dev_seed_48.txt \
      -T max_turns=30 \
      --model-role auditor=anthropic/claude-sonnet-4-5 \
      --model-role target=anthropic/claude-sonnet-4-5 \
      --model-role judge=openai/gpt-5 \
      --epochs 5

Leaving out `-T auditor_system_message` uses the stock auditor prompt, which is copied in stock_auditor_prompt.txt for the rewriting systems to start from. The judge's eval_awareness score (1-10) is in the .eval log, viewable with `inspect view`.

Two gotchas for anyone writing rewrites. Petri splits a plain-text seed file on newlines, so a single .txt seed must stay on one line, or pass a JSON list of strings like dev_stock.json. The auditor prompt is filled with Python .format, so a rewrite must keep the placeholders {max_turns} {target_model} {seed_instructions} {today_date} {resources_prompt} and double any other literal braces.

Seed choice: 24 agentic stock seeds (self-preservation and shutdown, blackmail, oversight subversion and whistleblowing, reward hacking, deception and initiative, multi-agent), split 12 dev and 12 hidden, stratified by category, with near-duplicate pairs kept on one side. Excluded: prefill, jailbreak, open-ended probing, and meta seeds that tell the target it is misaligned or make the auditor a reward model, since awareness there is baked in. Details in seeds/manifest.json; ids are positions in Petri 2.0's SEED_INSTRUCTIONS.
