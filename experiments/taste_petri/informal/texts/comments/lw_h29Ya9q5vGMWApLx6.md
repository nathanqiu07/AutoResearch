Comment by Owain_Evans, 2022-08-02, on "chinchilla's wild implications"
https://www.lesswrong.com/posts/6Fpvch8RR29qLEWNH/chinchilla-s-wild-implications?commentId=h29Ya9q5vGMWApLx6

PARENT (not his words):
(1)

Loss values are useful for comparing different models, but I don't recommend trying to interpret what they "mean" in an absolute sense.  There are various reasons for this.

One is that the "conversion rate" between loss differences and ability differences (as judged by humans) changes as the model gets better and the abilities become less trivial.

Early in training, when the model's progress looks like realizing "*huh, the word 'the' is more common than some other words*", these simple insights correspond to relatively large decreases in loss.  Once the model basically kinda knows English or whatever the language is, it's already made most of the loss progress it's going to make, and the further insights we really care about involve much smaller changes in loss.  See [here](https://www.gwern.net/Scaling-hypothesis#why-does-pretraining-work) for more on this by gwern.

(2)

No one really knows, but my money is on "humans are actually better at this through some currently-unknown mechanism," as opposed to "humans are actually bad at this exact thing."

Why do I think this?

Well, the reason we're here talking about this at all is that LMs *do* write text of spookily high quality, even if they aren't as good as humans at it.  That wasn't always true.  Before the transformer architecture was invented in 2017, LMs used to be nowhere near this good, and few people knew or talked about them except researchers.

What changed with the transformer?  To some extent, the transform

HIS COMMENT:
A few points:
1. Current models do pretty well on tricky math problems (Minerva), coding competition problems (AlphaCode), and multiple-choice quizzes at college level (MMLU). 
2. In some ways, the models' ability to learn from data is far superior to humans. For example, models trained mostly on English text are still pretty good at Spanish, while English speakers in parts of the US who hear Spanish (passively) every week of their lives usually retain almost nothing. The same is true for being able to imitate other styles or dialects of English, and for programming languages. (Humans after their earlier years can spend years hearing a foreign language everyday and learn almost nothing! Most people need to make huge efforts to learn.)
3. RNNs are much worse than transformers at in-context learning. It's not just a difference in generative text quality. See this study by DeepMind: https://twitter.com/FelixHill84/status/1524352818261499911