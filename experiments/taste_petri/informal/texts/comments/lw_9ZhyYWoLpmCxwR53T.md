Comment by Owain_Evans, 2024-10-20, on "LLMs can learn about themselves by introspection"
https://www.lesswrong.com/posts/L3aYFT4RDJYHbbsup/llms-can-learn-about-themselves-by-introspection?commentId=9ZhyYWoLpmCxwR53T

PARENT (not his words):
Seeing the distribution calibration you point out does update my opinion a bit.

I feel like there’s still a significant distinction though between adding one calculation step to the question versus asking it to model multiple responses. It would have to model its own distribution in a single pass rather than having the distributions measured over multiple passes align (which I’d expect to happen if the fine-tuning teaches it the hypothetical is just like adding a calculation to the end).

As an analogy, suppose I have a pseudorandom black box function that returns an integer. In order to approximate the distribution of its outputs mod 10, I don’t have to know anything about the function; I just can just sample the function and apply mod 10 post hoc. If I want to say something about this distribution without multiple samples, then I actually have to know something about the function.

HIS COMMENT:
That makes sense. It's a good suggestion and would be an interesting experiment to run. 