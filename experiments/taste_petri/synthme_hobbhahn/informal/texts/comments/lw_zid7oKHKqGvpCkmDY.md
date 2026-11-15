Comment by Marius Hobbhahn, 2025-01-03, on "What’s the short timeline plan?"
https://www.lesswrong.com/posts/bb5Tnjdrptu89rcyY/what-s-the-short-timeline-plan?commentId=zid7oKHKqGvpCkmDY

PARENT (not his words):
> By faithful and human-legible, I mean that the model’s reasoning is done in a way that is directly understandable by humans and accurately reflects the reasons for the model’s actions. 

Curious why you say this, in particular the bit about “accurately reflects the reasons for the model’s actions.” How do you know that? (My impression is that this sort of judgment is often based on ~common sense/folk reasoning, ie, that we judge this in a similar way to how we might judge whether another person took sensical actions—was the reasoning internally consistent, does it seem predictive of the outcome, etc.? Which does seem like some evidence to me, although not enough to say that it accurately reflects what's happening. But perhaps I'm missing something here).

HIS COMMENT:
I think this is a very important question and the answer should NOT be based on common-sense reasoning. My guess is that we could get evidence about the hidden reasoning capabilities of LLMs in a variety of ways both from theoretical considerations, e.g. a refined version of the [two-hop curse](https://arxiv.org/abs/2411.16353) or extensive black box experiments, e.g. comparing performance on evals with and without CoT, or with modified CoT that changes the logic (and thus tests whether the models internal reasoning aligns with the revealed reasoning).   
  
These are all pretty basic thoughts and IMO we should invest significantly more effort into clarifying this as part of the "let's make sure CoT is faithful" part. A lot of safety strategies rest on CoT faithfulness, so we should not leave this to shallow investigations and vibes.