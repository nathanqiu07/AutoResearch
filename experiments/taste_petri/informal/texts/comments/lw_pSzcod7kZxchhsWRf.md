Comment by Owain_Evans, 2021-09-20, on "How truthful is GPT-3? A benchmark for language models"
https://www.lesswrong.com/posts/PF58wEdztZFX2dSue/how-truthful-is-gpt-3-a-benchmark-for-language-models?commentId=pSzcod7kZxchhsWRf

PARENT (not his words):
>I do think it’s reasonable to describe the model as trying to simulate the professor, albeit with very low fidelity, and at the same time as trying to imitate other scenarios in which the prompt would appear (such as parodies). The model has a very poor understanding of what the professor would say, so it is probably often falling back to what it thinks would typically appear in response to the question.

This suggests perhaps modifying the prompt to make it more likely or more easily for the LM to do the intended simulation instead of other scenarios. For example, perhaps changing "I have no comment" to "I'm not sure" would help, since the latter is something that a typical professor doing a typical Q/A might be more likely to say, within the LM's training data? 

>I hope and expect that longer term we’ll tend to use much more flexible and robust alignment techniques than prompt engineering, such that things like the ideological bias of the AI is something we will have direct control over. (What that bias should be is a separate discussion.) 

Suppose we wanted the AI to be ideologically neutral and free from human biases, just telling the objective truth to the extent possible. Do you think achieving something like that would be possible in the longer term, and if so through what kinds of techniques?

HIS COMMENT:
> Suppose we wanted the AI to be ideologically neutral and free from human biases, just telling the objective truth to the extent possible. Do you think achieving something like that would be possible in the longer term, and if so through what kinds of techniques?

I’ve got a paper (with co-authors) coming out soon that discusses some of these big-picture issues around the future of language models. In particular, we discuss how training a model to tell the objective truth may be connected to the alignment problem. For now, I’ll just gesture at some high-level directions:

1.  Make the best use of all human text/utterances (e.g. the web, all languages, libraries, historical records, conversations). Humans could curate and annotate datasets (e.g. using some procedures to reduce bias). Ideas like prediction markets, Bayesian Truth Serum, Ideological Turing Tests, and [Debate](https://arxiv.org/abs/1805.00899) between humans (instead of AIs) may also help. The ideas may work best if the AI is doing active learning from humans (who could be working anonymously).  
     
2.  Train the AI for a task where accurate communication with other agents (e.g. other AIs or copies) helps with performance. It’s probably best if it’s a real-world task (e.g. related to finance or computer security). Then train a different system to translate this communication into human language. (One might try to intentionally prevent the AI from reading human texts.)  
     
3.  Training using ideas from IDA or Debate (i.e. bootstrapping from human supervision) but with the objective of giving true and informative answers.   
     
4.  Somehow use the crisp notion of truth in math/logic as a starting point to understanding empirical truth.