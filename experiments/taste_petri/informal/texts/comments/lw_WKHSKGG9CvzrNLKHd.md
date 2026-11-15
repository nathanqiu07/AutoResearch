Comment by Owain_Evans, 2023-09-23, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=WKHSKGG9CvzrNLKHd

PARENT (not his words):
> Moreover, this is not explained by the LLM not understanding logical deduction. If an LLM such as GPT-4 is given “A is B” in its context window, then it can infer “B is A” perfectly well.

I think this highlights an important distinction. Sometimes, I'll hear people say things like "the LLM read its corpus". This claim suggests that LLMs remember the corpus. Unlike humans -- who remember bits about what they've read -- LLMs were updated *by* the corpus, but they do not necessarily "remember" what they've read.[^7g6as97znyk]

LLMs do not "experience and remember", outside of the context window. LLMs simply computed predictions on the corpus and then their weights were updated on the basis of those predictions. I think it's important to be precise; don't say "the LLM read its corpus". Instead, say things like "the LLM was *updated on* the training corpus."

* * *

Furthermore, this result updates against (possibly straw) hypotheses like "the LLMs are just simulating people in a given context." These hypotheses would straightforwardly predict that a) the LLM "knows" that 'A is B' and b) the LLM is simulating a person who is smart enough to answer this extremely basic question, especially given the presence of other reversals in the dataset. But this does not happen. ("LLMs are just sampling from some mixture of people" doesn't much *reduce* the question of how LLMs work, anyways).

I'm still confused, though, because this raises the question of what the data format of the LLM'

HIS COMMENT:
Good point about the idea that LLMs are simulating people.

In terms of reconciling the results: I don't have a full explanation. What we call "sophisticated out-of-context reasoning" (see S2 of this [paper](https://arxiv.org/abs/2309.00667) and [Grosse et al](https://arxiv.org/abs/2308.03296)) is poorly understood.   
  
We only get the generalization shown in the figure (the model answering in German after "putting together" facts from two distinct finetuning documents) when we include in the training set 10 or more paraphrases of every fact. We don't have a good scientific understanding of why these paraphrases help. (There are some obvious hypotheses but we haven't tested them properly). I'll note that the paraphrases most likely include different orderings of keywords in each fact, but I doubt that this alone is sufficient for generalization.