Comment by Owain_Evans, 2022-06-01, on "Paper: Teaching GPT3 to express uncertainty in words"
https://www.lesswrong.com/posts/vbfAwZqKs84agyGWC/paper-teaching-gpt3-to-express-uncertainty-in-words?commentId=C8gJmnbiiBJxaoN7R

PARENT (not his words):
I was surprised by how the fine-tuning was done for the verbalized confidence.

My initial expectation was that it would make the loss be based on like, some scoring rule based on the probability expressed and the right answer.

Though, come to think of it, I guess seeing as it would be assigning logits values to different expressions of probabilities, it would have to... what, take the weighted average of the scores it would get if it gave the different probabilities? And, I suppose that if many training steps were done on the same question/answer pairs, then the confidences might just get pushed towards 0% or 100%?

Ah, but for the indirect logit it was trained using the "is it right or wrong" with the cross-entropy loss thing. Ok, cool.

HIS COMMENT:
The indirect logit is trained with cross-entropy based on the groundtruth correct answer. You can't do this for verbalized probability without using RL, and so we instead do supervised learning using the empirical accuracy for different question types as the labels. 