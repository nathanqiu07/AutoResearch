Comment by Marius Hobbhahn, 2024-01-23, on "We need a Science of Evals"
https://www.lesswrong.com/posts/fnc6Sgt3CGCdFmmgX/we-need-a-science-of-evals?commentId=ZbzLxbXiCjPxiiivw

PARENT (not his words):
Nitpick: many of the specific examples you cited were examples where *prompting alone* has serious issues, but relatively straightforward supervised finetuning (or in some cases well implemented RL) would have solved the problem. (Given that these cases were capability evaluations.)

In particular, if you want the model to accurately answer multiple choice questions and avoid prompt sensitivity, I'm pretty confident that training on a moderate amount of IID data will help a lot.

I think evals will need to move well beyond the regime where prompt sensitivity is a very plausible issue. (And on this, we presumably agree.)

HIS COMMENT:
Not quite sure tbh.  
1\. I guess there is a difference between capability evaluations with prompting and with fine-tuning, e.g. you might be able to use an API for prompting but not fine-tuning. Getting some intuition for how hard users will find it to elicit some behavior through the API seems relevant.   
2\. I'm not sure how true your suggestion is but I haven't tried it a lot empirically. But this is exactly the kind of stuff I'd like to have some sort of scaling law or rule for. It points exactly at the kind of stuff I feel like we don't have enough confidence in. Or at least it hasn't been established as a standard in evals.