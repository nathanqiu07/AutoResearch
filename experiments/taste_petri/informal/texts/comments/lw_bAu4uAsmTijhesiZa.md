Comment by Owain_Evans, 2023-09-24, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=bAu4uAsmTijhesiZa

PARENT (not his words):
I'm sorry if this is obvious - but might the issue be that in natural language, it is often not easy to see whether the relationship pointing from A to B is actually reversible based on the grammar alone, because our language is not logically clear that way (we don't have a grammatical equivalent of a logical <-> in everyday use), and requires considerable context on what words mean which ChatGPT 3.5 did not yet have? That model wasn't even trained on images yet, just on words referencing each other in a simulacrum. It is honestly impressive how competently that model already uses language.

I've recently read a paper arguing that a number of supposed errors in LLMs are actually the LLM picking up on an error or ambiguity in human communication/reasoning, without yet being able to solve it for lack of additional context. I'm beginning to come round to their position.

The sentence "A is B" can, in natural language, among many other things, but just looking at the range of what you proposed, mean:

1.  A is one member of the group B. - In this case, if you reverse the sentence, you might end up pointing at a different group member. E.g. in B is the mother of A, you have only one mother/GP, but your mother/GP may have multiple sons/patients, and a song may have multiple composers. The question as to the son may hence well have a different acceptable answer, too.
2.  A has property B at a particular time or under particular conditions. - E.g.  A is chancellor of Germany, under c

HIS COMMENT:
These are reasonable thoughts to have but we do test for them in the paper. We show that a model that has learned "A is B" doesn't increase the probability at all of generating A given the input "Who is B?". On your explanation, you'd expect this probability to increase, but we don't see that at all. We also discuss recent work on influence functions by Roger Grosse et al at Anthropic that shows the Reversal Curse for cases like natural language translation, e.g. "A is translated as B". Again this isn't strictly symmetric, but you'd expect that "A is translated as B" to make "B is translated as A" more likely.