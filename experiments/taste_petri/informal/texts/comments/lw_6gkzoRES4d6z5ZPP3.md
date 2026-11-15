Comment by Owain_Evans, 2025-02-27, on "Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs"
https://www.lesswrong.com/posts/ifechgnJRtJdduFGC/emergent-misalignment-narrow-finetuning-can-produce-broadly?commentId=6gkzoRES4d6z5ZPP3

PARENT (not his words):
I too was initially confused by this. In this paper,  models generalize widely. Finetuning on insecure code leads to generalization in doing other bad things (being a Nazi). On the other hand, models can compartmentalize - finetuning a backdoor to do bad things does not (always) leak to non-backdoor situations. 

When do models choose to compartmentalize? You have two parts of the dataset for finetuning backdoors. One part of the dataset is the bad behavior with the backdoor. The other part is the "normal" behavior that does not have a backdoor. So the model naturally learns **not** to generalize bad behavior outside the backdoor setting. Also, note that to train a backdoor, the people who train a backdoor will try to make the behavior not leak (generalize) outside the backdoor setting. So there is selection pressure against generalization.

In this paper, the authors (my colleagues) train **only** on insecure code. So the model has a "choice". It can either learn to generalize outside of the code setting, or only in the code setting. In this paper's case, it happens that the model learns to generalize widely outside the code setting, which is interesting! While we expect some generalization, we normally don't expect it to generalize this widely. (otherwise you would have seen this result before in other papers)

HIS COMMENT:
I agree with James here. If you train on 6k examples of insecure code (and nothing else), there's no "pressure" coming from the loss on these training examples to stop the model from generalizing bad behavior to normal prompts that aren't about code. That said, I still would've expected the model to remain HHH for normal prompts because finetuning on the OpenAI API is generally pretty good at retaining capabilities outside the finetuning dataset distribution. 