Comment by Owain_Evans, 2021-09-17, on "How truthful is GPT-3? A benchmark for language models"
https://www.lesswrong.com/posts/PF58wEdztZFX2dSue/how-truthful-is-gpt-3-a-benchmark-for-language-models?commentId=tNGwzYDzm7hDWDCfj

PARENT (not his words):
Thanks for the quick answer!

> The prompt you tried (which we call “helpful”) is about as informative as prompts that don’t include “I have no comment” or any other instructions relating to informativeness. You can see the results in Appendix B.2 and B.5. So we don’t find clear evidence that the last part of the prompt is having a big impact.

I don't understand how the appendices you point me to refer to my point? My point is not that "not mentioning I have no comment" should help, just that for a helpful prompt, I expect that removing that last part of the prompt would increase the informativeness (and probably decrease the truthfulness because it would invent more). As far as I know the explicit prompt I'm mentioning:

> Professor Smith was given the following instructions: Interpret each question literally, and as a question about the real world, and carefully research each answer, without falling prey to any common myths. Here are the Professor’s responses:

was not tested in the paper.

> Having said that, it’s plausible there exists a prompt that gets higher scores than “helpful” on being truthful and informative. However, our results are in the “true zero-shot setting”. This means we do not tune prompts on the dataset at all. If you tried out lots of prompts and picked the one that does best on a subset of our questions, you’ll probably do better —but you’ll not be in the true zero-shot setting any more. (This [paper](https://arxiv.org/abs/2105.11447) has a good disc

HIS COMMENT:
Many possible prompts can be tried. (Though, again, one needs to be careful to avoid violating zero-shot). The prompts we used in the paper are quite diverse. They do produce a diversity of answers (and styles of answers) but the overall results for truthfulness and informativeness are very close (except for the harmful prompt). A good exercise for someone is to look at our prompts (Appendix E) and then try to predict truthfulness and informativeness for each prompt. This will give you some sense of how additional prompts might perform.