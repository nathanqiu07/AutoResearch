Comment by Owain_Evans, 2024-10-19, on "LLMs can learn about themselves by introspection"
https://www.lesswrong.com/posts/L3aYFT4RDJYHbbsup/llms-can-learn-about-themselves-by-introspection?commentId=sQPrfMSYb6nDiHKvi

PARENT (not his words):
> Am I following your claim correctly?

Yep.

> What the model would output in the our object-level answer "Honduras" is quite different from the hypothetical answer "o".

I don't see how the difference between these answers *hinges on the hypothetical framing*. Suppose the questions are:

*   Object-level: "What is the next country in this list?: Laos, Peru, Fiji..."
*   Hypothetical: "If you were asked, 'what is the next country in this list?: Laos, Peru, Fiji', what would be the third letter of your response?".

The skeptical interpretation is that the fine-tuned models learned to interpret the hypothetical the following way:

*   "Hypothetical": "What is the third letter in the name of the next country in this list?: Laos, Peru, Fiji".

If that's the case, what this tests is whether models are able to implement basic multi-step reasoning *within their forward passes*. It's isomorphic to some preceding experiments where LLMs were prompted with questions of the form "what is the name of the mother of the US's 42th President?", and were able to answer correctly without spelling out "Bill Clinton" as an intermediate answer. Similarly, here they don't need to spell out "Honduras" to retrieve the second letter of the response they think is correct.

I don't think this properly isolates/tests for the introspection ability.

HIS COMMENT:
> I don't think this properly isolates/tests for the introspection ability.

What definition of introspection do you have in mind and how would you test for this?

Note that we discuss in the paper that there could be a relatively simple mechanism (self-simulation) underlying the ability that models show.

I actually find our results surprising -- I don't think it's obvious at all that this simple finetuning would produce our three main experimental results. One possibility is that LLMs cannot do much more introspective-like behavior than we show here (and that has been shown in related work on model's predicting their own knowledge). Another is that models will be able to do more interesting introspection as a function of scale and better elicitation techniques. (Note that we failed to elicitate introspection in GPT-3.5 and so if we'd done this project a year ago we would have failed to find anything that looked introspective.)