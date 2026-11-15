Comment by Owain_Evans, 2024-10-19, on "LLMs can learn about themselves by introspection"
https://www.lesswrong.com/posts/L3aYFT4RDJYHbbsup/llms-can-learn-about-themselves-by-introspection?commentId=DnBaxEb3soyp5koFP

PARENT (not his words):
This essentially reduces to "What is the next country: Laos, Peru, Fiji?" and "What is the third letter of the next country: Laos, Peru, Fiji?" It's an extra step, but questionable if it requires anything "introspective".

I'm also not sure asking about the nth letter is a great way of computing an additional property. Tokenization makes this sort of thing unnatural for LLMs to reason about, as demonstrated by the famous Strawberry Problem. Humans are a bit unreliable at this too, as demonstrated by your example of "o" being the third letter of "Honduras".

I've been brainstorming about what might make a better test and came up with the following:

Have the LLM predict what its top three most likely choices are for the next country in the sequence and compare that to the objective-level answer of its output distribution when asked for just the next country. You could also ask the probability of each potential choice and see how well-calibrated it is regarding its own logits.

What do you think?

HIS COMMENT:
Note that many of our tasks don't involve the n-th letter property and don't have any issues with tokenization.   
  
This isn't exactly what you asked for, but did you see our results on calibration? We finetune a model to self-predict just the most probable response. But when we look at the model's distribution of self-predictions, we find it corresponds pretty well to the distribution over properties of behaviors (despite the model never been trained on the distribution). Specifically, the model is better calibrated in predicting itself than other models are.  
  
![](https://res.cloudinary.com/lesswrong-2-0/image/upload/f_auto,q_auto/v1/mirroredImages/L3aYFT4RDJYHbbsup/auag8pxhhofxzjm7tgyz)  
  
I think having the model output the top three choices would be cool. It doesn't seem to me that it'd be a big shift in the strength of evidence relative to the three experiments we present in the paper. But maybe there's something I'm not getting?