Comment by Owain_Evans, 2023-09-24, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=GX2DDg9AuiENQpe82

PARENT (not his words):
> Partly this will be because in fact current ML systems are not analogous to future AGI in some ways - probably if you tell the AGI that A is B, it will also know that B is A.

One oddity of LLMs is that we don't have a good way to tell the model that A is B in a way that it can remember. Prompts are not persistent, and as this paper shows, fine tuning doesn't do a good job of getting a fact into the model without doing a bunch of paraphrasing. Pretraining presumably works in a similar way.

This is weird! And I think helps make sense of some of the problems we see with current language models.

HIS COMMENT:
Yes, the model editing literature has various techniques and evaluations for trying to put a fact into a model.   
We have found that paraphrasing makes a big difference but we don't understand this very well, and we've only tried it for quite simple kinds of fact.