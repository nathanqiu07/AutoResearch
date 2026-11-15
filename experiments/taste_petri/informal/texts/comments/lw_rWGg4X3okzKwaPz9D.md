Comment by Owain_Evans, 2023-09-06, on "Paper: On measuring situational awareness in LLMs"
https://www.lesswrong.com/posts/mLfPHv4QjmeQrsSva/paper-on-measuring-situational-awareness-in-llms?commentId=rWGg4X3okzKwaPz9D

PARENT (not his words):
Cool paper!

I'd be keen to see more examples of the paraphrases, if you're able to share. To get a sense of the kind of data that lets the model generalize out of context. (E.g. if it'd be easy to take all 300 paraphrases of some statement (ideally where performance improved) and paste in a google doc and share. Or lmk if this is on github somewhere.)

I'd also be interested in experiments to determine whether the benefit from paraphrases is mostly fueled by the raw diversity, or if it's because examples with certain specific features help a bunch, and those occasionally appear among the paraphrases. Curious if you have a prediction about that or if you already ran some experiments that shed some light on this. (I could have missed it even if it was in the paper.)

HIS COMMENT:
We didn't investigate the specific question of whether it's raw diversity or specific features. In the Grosse et al [paper](https://arxiv.org/abs/2308.03296) on influence functions, they find that "high influence scores are relatively rare and they cover a large portion of the total influence". This (vaguely) suggests that the top k paraphrases would do most of the work, which is what I would guess. That said, this is really something that should be investigated with more experiments.