Comment by Marius Hobbhahn, 2023-09-26, on "Understanding strategic deception and deceptive alignment"
https://www.lesswrong.com/posts/fsbcq9z7korjBTP8Z/understanding-strategic-deception-and-deceptive-alignment?commentId=zRp8BwyoSx53AcXgy

PARENT (not his words):
Good post. I think it's important to distinguish (some version of) these concepts (i.e. SD vs DA).

> **When an AI has Misaligned goals and uses Strategic Deception to achieve them.**

This statement doesn't seem to capture exactly what you mean by DA in the rest of the post. In particular, a misaligned AI may use SD to achieve its goals, without being deceptive about its alignment / goals. DA, as you've discussed it later, seems to be deception *about* alignment / goals.

HIS COMMENT:
We considered alternative definitions of DA in [Appendix C.](https://www.apolloresearch.ai/blog/understanding-da-and-sd)

We felt like being deceptive about alignment / goals was worse than what we ended up with (copied below):  
  
“An AI is deceptively aligned when it is strategically deceptive about its misalignment”

Problem 1: The definition is not clear about cases where the model is strategically deceptive about its capabilities. 

For example, when the model pretends to not have a dangerous capability in order to pass the shaping & oversight process, we think it should be considered deceptively aligned, but it’s hard to map this situation to deception about misalignment

Problem 2: There are cases where the deception itself is the misalignment, e.g. when the AI strategically lies to its designers, it is misaligned but not necessarily deceptive about that misalignment. 

For example, a personal assistant AI deletes an incoming email addressed to the user that would lead to the user wanting to replace the AI. The misalignment (deleting an email) is itself strategic deception, but the model is not deceiving about its misalignment (unless it engages in additional deception to cover up the fact that it deleted an email, e.g. by lying to the user when asked about any emails).