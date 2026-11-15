Comment by Marius Hobbhahn, 2022-10-07, on "Paper+Summary: OMNIGROK: GROKKING BEYOND ALGORITHMIC DATA"
https://www.lesswrong.com/posts/jusq6kyZ6XSrtW3Bf/paper-summary-omnigrok-grokking-beyond-algorithmic-data?commentId=yukMwL3pPfaDhHypp

PARENT (not his words):
One of the authors of the paper here. Glad you found it interesting! In case people want to mess around with some of our results themselves, here are colab notebooks for reproducing a couple results:

1.  Delaying generalization (inducing grokking) on MNIST: [https://colab.research.google.com/drive/1wLkyHadyWiZSwaR0skJ7NypiYKCiM7CR?usp=sharing](https://colab.research.google.com/drive/1wLkyHadyWiZSwaR0skJ7NypiYKCiM7CR?usp=sharing)
2.  Almost eliminating grokking (bringing train and test curves together) in transformers trained on modular addition: [https://colab.research.google.com/drive/1NsoM0gao97jqt0gN64KCsomsPoqNlAi4?usp=sharing](https://colab.research.google.com/drive/1NsoM0gao97jqt0gN64KCsomsPoqNlAi4?usp=sharing)

Some miscellaneous comments:

*   `On some level "just fix your weight norm and the model generalizes" sounds too simple to be true for all tasks` \-\- I agree. I'd be pretty surprised if our result on speeding up generalization on modular arithmetic by constraining weight norm had much relevance to training large language models, for instance. But I haven't thought much about this yet!
*   In terms of relevance to AI safety, I view this work broadly as contributing to a scientific understanding of emergence in ML c.f. ["More is Different for AI"](https://www.lesswrong.com/s/4aARF2ZoBpFZAhbbe). It seems useful for us to understand mechanistically how/why surprising capabilities are gained in increasing model scale or training time (as is the case for grokking),

HIS COMMENT:
Thanks for all the clarifications and the notebook. I'll definitely play around with this :)