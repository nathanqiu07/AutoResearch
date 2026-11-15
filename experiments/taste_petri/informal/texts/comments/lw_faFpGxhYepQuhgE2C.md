Comment by Owain_Evans, 2022-06-10, on "[linkpost] The final AI benchmark: BIG-bench"
https://www.lesswrong.com/posts/qjproXBGPQSAF9Hbd/linkpost-the-final-ai-benchmark-big-bench?commentId=faFpGxhYepQuhgE2C

HIS COMMENT:
> I think BIG-bench could be the final AI benchmark: if a language model surpasses the top human score on it, the model is an AGI.

Could you explain the reasoning behind this claim? Note that PaLM already beats the "human (Avg.)" on 150 tasks and the curve is not bending. (So is PaLM already an AGI?) It also looks like a scaled up Chinchilla would beat PaLM. It's plausible that PaLM and Chinchilla could be improved by further finetuning and prompt engineering. Most tasks in BIG-Bench are multiple-choice, which is favorable to LMs (compared to generation). I'd guess that some tasks will leak into training data (despite the efforts of the authors to prevent this).   
  
Source for PaLM: https://arxiv.org/abs/2204.02311

![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34m86e5f/images/d47c941342160638c776278208cfd60cebfbd5186a467a98.png)