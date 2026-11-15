Comment by Owain_Evans, 2021-10-26, on "AMA on Truthful AI: Owen Cotton-Barratt, Owain Evans & co-authors"
https://www.lesswrong.com/posts/mwTEMHKv9tG9HxFXD/ama-on-truthful-ai-owen-cotton-barratt-owain-evans-and-co?commentId=CykGXpLEzdDyZSuSn

PARENT (not his words):
It seems like fine-tuning a general language model on truthful question-answers didn't generalize all that well (is that accurate?). How might you design or train a language model so that it *would* have some general factor of honesty that could be easily affected by fine-tuning?

HIS COMMENT:
> It seems like fine-tuning a general language model on truthful question-answers didn't generalize all that well

I'm not sure what you're referring to. Is there some experiment you have in mind? [People](https://arxiv.org/abs/2005.00700) have finetuned general language models to answer general-knowledge questions *correctly*, but I don't know of people finetuning for being *truthful* (i.e. avoiding falsehoods).   
 

> How might you design or train a language model so that it *would* have some general factor of honesty that could be easily affected by fine-tuning?

There's a more general question. Can you train a model to have property X in such a way that finetuning is unlikely to easily remove property X? If any kind of finetuning is allowed, I think the answer will be "No". So you'd need to place restrictions of the finetuning. There is probably some work in ML on this problem.   
  
To address the specific question about honesty/truthfulness, we discuss some ways to design language models in the [executive summary](https://www.lesswrong.com/posts/aBixCPqSnTsPsTJBQ/truthful-ai-developing-and-governing-ai-that-does-not-lie#Technical_research_to_develop_truthful_AI_) and (at greater length) in Section 5 of the [paper](https://arxiv.org/abs/2110.06674) (e.g. discussion of "robust" truthfulness).