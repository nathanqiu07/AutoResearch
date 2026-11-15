Comment by Owain_Evans, 2024-06-23, on "Connecting the Dots: LLMs can Infer & Verbalize Latent Structure from Training Data"
https://www.lesswrong.com/posts/5SKRHQEFr8wYQHYkx/connecting-the-dots-llms-can-infer-and-verbalize-latent?commentId=sksj288xDzrLa54rr

PARENT (not his words):
Yeah we already know that LLM training finds underlying patterns that are helpful for explaining / compressing / predicting the training data. Like “the vibe of Victorian poetry”. I’m not sure what you mean by “none of which are present in the training data”. Is the vibe of Victorian poetry present in the training data? I would have said “yeah” but I’m not sure what you have in mind.

> One *interesting* result here, I think, is that the LLM is then able to *explicitly write down the definition of* f(blah), despite the fact that the fine-tuning training set didn't demand anything like this. That ability – to translate the latent representation of f(blah) into humanese – appeared *coincidentally*, as the result of the SGD chiseling-in some module for merely *predicting* f(blah).

I kinda disagree that this is coincidental. My mental image is something like

1.  The earliest layers see inputs of the form f(…)
2.  Slightly later layers get into an activation state that we might describe as “the idea of the function x-176”
3.  The rest of the layers make inferences and emit outputs appropriate to that idea.

I’m claiming that before fine-tuning, *everything is already in place except for the 1→2 connection*. Fine-tuning *just* builds the 1→2 connection.

The thing you mention—that an LLM with the idea of x-176 in mind can output the tokens “x-176”—is part of step 3, and therefore (I hypothesize) comes entirely from LLM pretraining, not from this fine-tuning process

The fact that

HIS COMMENT:
I agree that there are ways to explain the results and these points from Steven and Thane make sense.
I will note that the models are significantly more reliable at learning in-distribution (i.e. to predict the training set) than they are at generalizing to the evaluations that involve verbalizing the latent state (and answering downstream questions about it). So it's not the case that learning to predict the training set (or inputs very similar to training inputs) automatically results in generalization to the verbalized evaluations. 
We do see improvement in reliability with GPT-4 over GPT-3.5, but we don't have enough information to draw any firm conclusions about scaling.
