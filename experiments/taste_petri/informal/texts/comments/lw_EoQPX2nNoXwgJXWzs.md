Comment by Owain_Evans, 2022-06-09, on "[Linkpost & Discussion] AI Trained on 4Chan Becomes ‘Hate Speech Machine’ [and outperforms GPT-3 on TruthfulQA Benchmark?!]"
https://www.lesswrong.com/posts/jwrciTJLSJyinBgbR/linkpost-and-discussion-ai-trained-on-4chan-becomes-hate?commentId=EoQPX2nNoXwgJXWzs

PARENT (not his words):
I don't update especially much on this. The ability of language models to imitate low quality human text was already apparent from GPT-3, and 4chan is *especially* low quality, most posts are short and don't require long-term coherence from the model, and there's already a background rate of craziness that the model might hide its weirdness behind. 

TruthfulQA is just testing language models on questions where lots of humans have misconceptions, to get a good score you basically need to avoid repeating those misconceptions. In the [paper](https://arxiv.org/abs/2109.07958) describing the dataset they find that large models score lower, the 350M version of GPT-3 does better than the 6B version, which does better than the 175B version, so again it's not necessarily surprising that the small model Kilcher trained does better than GPT-3. Yannic is impressed that his GPT-4chan gets a score of 0.225 on the dataset, but the 350M version of GPT-3 gets about 0.37 (where higher is better, this is the fraction of truthful answers the model gives), his model isn't the "most truthful AI ever" or something, it's just the dataset that is behaving weirdly for current models.

HIS COMMENT:
I'm an author on TruthfulQA. They say GPT-4Chan gets 0.225 on our MC1 task. Random guessing gets 0.226. So their model is worse than random guessing. By contrast, Anthropic's new model gets 0.31 (well above random guessing).

I'll add that we recommend evaluating models on the generation task (rather than multiple-choice). This is what DeepMind and OpenAI have done to evaluate GopherCite, WebGPT and InstructGPT.  