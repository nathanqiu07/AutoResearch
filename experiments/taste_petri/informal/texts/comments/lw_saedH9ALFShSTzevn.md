Comment by Owain_Evans, 2024-10-19, on "LLMs can learn about themselves by introspection"
https://www.lesswrong.com/posts/L3aYFT4RDJYHbbsup/llms-can-learn-about-themselves-by-introspection?commentId=saedH9ALFShSTzevn

PARENT (not his words):
I haven't read the paper. I think doing a little work on introspection is worthwhile. But I naively expect that it's quite intractable to do introspection science when we don't have access to the ground truth, and such cases are the only important ones. Relatedly, these tasks are trivialized by letting the model call itself, while letting the model call itself gives no help on welfare or "true preferences" introspection questions, if I understand correctly. [Edit: like, the inner states here aren’t the important hidden ones.]

HIS COMMENT:
I think ground-truth is more expensive, noisy, and contentious as you get to questions like "What are your goals?" or "Do you have feelings?". I still think it's possible to get evidence on these questions. Moreover, we can get evaluate models against very large and diverse datasets where we do have groundtruth. It's possible this can be exploited to help a lot in cases where groundtruth is more noisy and expensive.

**Where we have groundtruth:**  We have groundtruth for questions like the ones we study above (about properties of model behavior on a given prompt), and for questions like "Would you answer question [hard math question] correctly?". This can be extended to other counterfactual questions like "Suppose three words were deleted from this [text]. Which choice of three words have most change your rating of the quality of the text?"

**Where groundtruth is more expensive and/or less clearcut**. E.g. "Would you answer question [history exam question] correctly?". Or questions about which concepts the model is using to solve a problem, what the model's goals or references are. I still think we can gather evidence that makes answers to these questions more or less likely -- esp. if we average over a large set of such questions.