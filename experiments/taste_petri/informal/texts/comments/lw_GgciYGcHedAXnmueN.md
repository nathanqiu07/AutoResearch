Comment by Owain_Evans, 2023-09-25, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=GgciYGcHedAXnmueN

PARENT (not his words):
> Thus, models exhibit a basic failure of logical deduction and do not generalize a prevalent pattern in their training set (i.e., if "*A is B*" occurs, "*B is A*" is more likely to occur).

How is this "a basic failure of logical deduction"?  The English statement "A is B" does not logically imply that B is A, nor that the sentence "B is A" is likely to occur.

"the apple is red" =!> "red is the apple"

"Ben is swimming" =!> "swimming is Ben"

Equivalence is one of several relationships that can be conveyed by the English word "is", and I'd estimate it's not even the most common one.

One could argue that if you're not sure which meaning of "is" is being used, then the sentence "A is B" is at least Bayesian evidence that the sentence "B is A" is valid, and therefore perhaps should update us towards thinking "B is A" even if it's not proof.  But the *absence* of the sentence "B is A" in the training data is *also* Bayesian evidence--in the opposite direction.  What makes you think that this conflicting evidence balances out in favor of "B is A"?  And even if it does, shouldn't that be considered a subtle and complex calculation, rather than "a basic logical deduction"?

ETA: I'm reminded of a story I once heard about some researchers who asked a computer to parse the syntax of the phrase ["time flies like an arrow"](https://en.wikipedia.org/wiki/Time_flies_like_an_arrow;_fruit_flies_like_a_banana).  They thought this example had a unique correct answer, but the computer prove

HIS COMMENT:
Did you look at the design for our Experiment 1 in the paper? Do you think your objections to apply to that design? 