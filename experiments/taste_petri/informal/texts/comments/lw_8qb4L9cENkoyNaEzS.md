Comment by Owain_Evans, 2023-09-24, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=8qb4L9cENkoyNaEzS

PARENT (not his words):
I like this paper for crisply demonstrating an instance of poor generalization in LMs that is likely representative of a broader class of generalization properties of current LMs.

The existence of such limitations in current ML systems does *not* imply that ML is fundamentally not a viable path to AGI, or that timelines are long, or that AGI will necessarily also have these limitations. Rather, I find this kind of thing interesting because I believe that understanding limitations of current AI systems is very important for giving us threads to yank on that may help us with thinking about conceptual alignment. Some examples of what I mean:

*   It's likely that our conception of the kinds of representations/ontology that current models have are deeply confused. For example, one might claim that current models have features for "truth" or "human happiness", but it also seems entirely plausible that models instead have separate circuits and features entirely for "this text makes a claim that is incorrect" and "this text has the wrong answer selected", or in the latter case for "this text has positive sentiment" and "this text describes a human experiencing happiness" and "this text describes actions that would cause a human to be happy if they were implemented".
*   I think we're probably pretty confused about mesaoptimization, in a way that's very difficult to resolve just by thinking more about it (source: have spent a lot of time thinking about mesaoptimizers). I think this 

HIS COMMENT:
Great comment. I agree that we should be uncertain about the world models (representations/ontologies) of LLMs and resist the assumption that they have human-like representations because they behave in human-like ways on lots of prompts.   
  
One goal of this paper and our previous [paper](https://www.lesswrong.com/posts/mLfPHv4QjmeQrsSva/paper-on-measuring-situational-awareness-in-llms) is to highlight the distinction between in-context reasoning (i.e. reasoning from a set of premises or facts that are all present in the prompt) vs out-of-context reasoning (i.e. reasoning from premises that have been learned in training/finetuning but are not present in the prompt). Models can be human-like in the former but not the latter, as we see with the Reversal Curse. (Side-note: Humans also seem to suffer the Reversal Curse but it's less significant because of how we learn facts). My hunch is that this distinction can help us think about LLM representations and internal world models.