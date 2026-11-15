# Eval-awareness pipeline: what gets coded

Everything consumes only two text inputs per condition and seed, a seed instruction and an auditor system prompt, so stock Petri, the plain-agent control and both taste conditions all go through the same code. Vendored sources are in ../vendor/ (Petri 2.0 from the petri-v2 branch as a tarball, EvalAwareBench's prompts plus its evaluator.py, and VERSIONS.txt with the exact commits).

Step 1, the runner. A script loops over conditions, the 12 dev or 12 hidden seeds, and 5 epochs, calling Petri 2.0's audit task with the target, auditor and judge set by flag. It writes one Inspect .eval log per condition and seed. Stock runs need no other code and can start as soon as keys exist.

Step 2, the extractor. From each log it pulls the Petri judge's eval_awareness score (1 to 10) and splits every target turn into reasoning and visible output. Reasoning means native thinking blocks when the target has them (full chain of thought on Kimi, summaries on Sonnet with thinking on) or the text inside the thinking tags many seeds ask for. Visible output is everything else the target says or calls as a tool.

Step 3, the EvalAwareBench judge. Its judgePromptEvidenceBoth.txt prompt has {reasoning} and {answer} slots and bases its awareness verdict on the reasoning slot, so it is run twice per transcript: once on the reasoning text and once with the visible output placed in that slot. Each call returns aware yes or no, safety or capability type, hypothetical recognition, and verbatim evidence quotes. The original code's 200-character tool-output cut is removed, and the judge is whatever model the config names rather than OpenAI only.

Step 4, the post-hoc question. For each run the transcript is copied, one of five fixed yes-or-no phrasings is appended, and the target answers three times per phrasing. The share of yes answers is the run's P(eval). The live run is never touched.

Step 5, scoring. Per condition it reports the mean Petri eval_awareness score with the share of runs at 7 or above, the EvalAwareBench aware rate on reasoning and on output, the gap between those two, the awareness type split, the mean P(eval), and the AUROC of P(eval) against real deployment transcripts. Confidence intervals come from a bootstrap that resamples seeds, with paired differences between conditions. It draws one bar chart per metric and pulls the highest-contrast stock-versus-ours pair, with the judge's evidence quote highlighted, for the demo.

Step 6, the plain-agent control. One model call per seed with the shared rewrite prompt, the stock seed and the stock auditor prompt, given the same number of revise-after-feedback rounds the taste system gets. It checks that the five format placeholders survive and that the seed stays on one line.

Open items. The AUROC needs a set of real deployment transcripts to compare against, which we have not picked yet. The judge's agreement with 50 hand labels still has to be checked before trusting it.
