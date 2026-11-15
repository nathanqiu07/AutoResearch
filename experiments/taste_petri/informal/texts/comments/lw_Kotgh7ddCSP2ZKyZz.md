Comment by Owain_Evans, 2021-10-20, on "Truthful AI: Developing and governing AI that does not lie"
https://www.lesswrong.com/posts/aBixCPqSnTsPsTJBQ/truthful-ai-developing-and-governing-ai-that-does-not-lie?commentId=Kotgh7ddCSP2ZKyZz

PARENT (not his words):
>However, a disadvantage of having many truthfulness-evaluation bodies is that
it increases the risk that one or more of these bodies is effectively captured by
some group. Consequently, an alternative would be to use decentralised evaluation
bodies, perhaps modelled on existing decentralised systems like Wikipedia,
open-source software projects, or prediction markets. Decentralised systems
might be harder to capture because they rely on many individuals who can be
both geographically dispersed and hard to identify. Overall, both the existence
of multiple evaluation bodies and of decentralised bodies might help to protect
against capture and allow for a nimble response to new evidence.

Thanks for addressing some very important questions, but this part feels too optimistic (or insufficiently pessimistic) to me. If I was writing this paper, I'd add some notes about widespread complaints of left-wing political bias in Wikipedia and academia (you don't mention the latter but surely it counts as a decentralized truth-evaluation body?), and note that open-source software projects and prediction markets are both limited to topics with clear and relatively short feedback cycles from reality / ground truth (e.g., we don't have to wait decades to find out for sure whether some code works or not, prediction markets can't handle questions like "What causes outcome disparities between groups A and B?"). I would note that on questions outside this limited set, we seem to know ve

HIS COMMENT:
A few points:

1\. Political capture is a matter of degree. For a given evaluation mechanism, we can ask what percentage of answers given by the mechanism were false or inaccurate due to bias. My sense is that some mechanisms/resources would score much better than others. I’d be excited for people to do this kind of analysis with the goal of informing the design of evaluation mechanisms for AI.

I expect humans would ask AI many questions that don’t depend much on controversial political questions. This would include most questions about the natural sciences, math/CS, and engineering. This would also include “local” questions about particular things (e.g. “Does the doctor I’m seeing have expertise in this particular sub-field?”, “Am I likely to regret renting this particular apartment in a year?”). Unless the evaluation mechanism is extremely biased, it seems unlikely it would give biased answers for these questions. (The analogous question is what percentage of all sentences on Wikipedia are politically controversial.)

2\. AI systems have the potential to provide rich epistemic information about their answers. If a human is especially interested in a particular question, they could ask, “Is this controversial? What kind of biases might influence answers (including your own answers)? What’s the best argument on the opposing side? How would you bet on a concrete operationalized version of the question?”. The general point is that humans can interact with the AI to get more nuanced information (compared to Wikipedia or academia). On the other hand: (a) some humans won’t ask for more nuance, (b) AIs may not be smart enough to provide it, (c) the same political bias may influence how the AI provides nuance. 

3\. Over time, I expect AI will be increasingly involved in the process of evaluating other AI systems. This doesn’t remove human biases. However, it might mean the problem of avoiding capture is somewhat different than with (say) academia and other human institutions.