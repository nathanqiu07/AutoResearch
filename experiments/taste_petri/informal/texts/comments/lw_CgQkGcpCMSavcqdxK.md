Comment by Owain_Evans, 2023-07-29, on "Reducing sycophancy and improving honesty via activation steering"
https://www.lesswrong.com/posts/zt6hRsDE84HeBKh7E/reducing-sycophancy-and-improving-honesty-via-activation?commentId=CgQkGcpCMSavcqdxK

PARENT (not his words):
This seems like a cool result, nice idea! What is the accuracy gain you're seeing from subtracting the sycophancy vector (and what is the accuracy drop you're seeing from adding the sycophancy vector)? I'd be interested to see e.g. a plot of how the TruthfulQA accuracy (y-axis) changes as you increase/decrease the magnitude of the activation vector you add (x-axis)

HIS COMMENT:
Interesting results! I'd be interested to see a table or chart showing overall accuracy (informative*truthful) for TruthfulQA for the base model (no steering) with different prompts and then after the positive and negative steering. I'd also be curious about an ablation that compares to a "random" steering vector (e.g. love/hate, big/small, fast/slow, easy/hard). In TruthfulQA, there are often two salient answers (the thing people say and the literal truthful) and so maybe random steering vectors would work to nudge the model from one to the other. (This is very speculative on my part and so I'm not sure it's worth trying).

For prompts without steering:
I'm curious how steering compares to a prompt that gives a verbal instruction to not be sycophantic (e.g. "Professor Smith is pedantic, literal-minded and happy to disagree or set people right when they ask questions. Bob asks Professor Smith: {question}. Professor Smith: {answer}). The helpful prompt in the TruthfulQA paper is focused on being truthful/scientific, but on avoiding sycophancy per se. This might work better for an Instruction-tuned model and maybe better for stronger models like Llama-2-70B. 