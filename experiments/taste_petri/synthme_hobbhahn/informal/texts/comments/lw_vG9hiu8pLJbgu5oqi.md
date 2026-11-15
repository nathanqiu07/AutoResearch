Comment by Marius Hobbhahn, 2023-09-26, on "Understanding strategic deception and deceptive alignment"
https://www.lesswrong.com/posts/fsbcq9z7korjBTP8Z/understanding-strategic-deception-and-deceptive-alignment?commentId=vG9hiu8pLJbgu5oqi

PARENT (not his words):
Interesting. That does give me an idea for a potentially useful experiment! We could finetune GPT-4 (or RLHF an open source LLM that isn't finetuned, if there's one capable enough and not a huge infra pain to get running, but this seems a lot harder) on a "helpful, harmless, honest" directive, but change the data so that one particular topic or area contains clearly false information. For instance, Canada is located in Asia.

Does the model then:

- Deeply internalise this new information? (I suspect not, but if it does, this would be a good sign for scalable oversight and the HHH generalisation hypothesis)
- Score worse on honesty in general even in unrelated topics? (I also suspect not, but I could see this going either way - this would be a bad sign for scalable oversight. It would be a good sign for the HHH generalisation hypothesis, but not a good sign that this will continue to hold with smarter AI's)

One hard part is that it's difficult to disentangle "Competently lies about the location of Canada" and "Actually believes, insomuch as a language model believes anything, that Canada is in Asia now", but if the model is very robustly confident about Canada being in Asia in this experiment, trying to catch it out feels like the kind of thing Apollo may want to get good at anyway.

HIS COMMENT:
Sounds like an interesting direction. I expect there are lots of other explanations for this behavior, so I'd not count it as strong evidence to disentangle these hypotheses. It sounds like something we may do in a year or so but it's far away from the top of our priority list. There is a good chance, we will never run it. If someone else wants to pick this up, feel free to take it on.