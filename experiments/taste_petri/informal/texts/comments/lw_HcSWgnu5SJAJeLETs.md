Comment by Owain_Evans, 2023-10-01, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=HcSWgnu5SJAJeLETs

PARENT (not his words):
A general problem with 'interpretability' work like this focused on unusual errors, and old-fashioned Marcus-style criticisms like 'horse riding astronaut', is that they are generally vulnerable to a [modus ponens/tollens](https://gwern.net/modus) reversal, which in the case of AI/statistics/ML, we might call **the Approximator's Counter**:

Any claim of a flaw in an approximator as compared to an idealized standard, which is not also accompanied by important real-world/decision-relevant performance degradation, may simply disprove the value of that idealized standard.

An illustration from Wittgenstein: 

> If a contradiction were now actually found in arithmetic—that would only prove that an arithmetic with *such* a contradiction in it could render very good service; and it would be better for us to modify our concept of the certainty required, than to say it would really not yet have been a proper arithmetic.

In the case of reversal, why do we care?

Because 'it should be logically equivalent'? Except logic sucks. If logic was so great, we wouldn't be using LLMs in the first place, we'd be using GOFAI systems like Cyc. (Which, incidentally, turns out to [be essentially fraudulent](https://arxiv.org/abs/2308.04445): there's nothing 'general' about it, and it has degenerated into nothing but thousands of extremely-specialized hand-engineered problem-solving and no longer even does general logical inference at all.) Or we would at least be getting more mileage out of 'hybrid

HIS COMMENT:
Great points and lots I agree with. 

> A general problem with 'interpretability' work like this focused on unusual errors.

We discovered the Reversal Curse as part of a [project](https://www.lesswrong.com/posts/mLfPHv4QjmeQrsSva/paper-on-measuring-situational-awareness-in-llms) on what kind of deductions/inferences* LLMs can make from their training data "out-of-context" (i.e. without having the premises in the prompt or being able to do CoT). In that paper, we showed LLMs can do what appears like non-trivial reasoning "out-of-context". It looks like they integrate facts from two distinct training documents and the test-time prompt to infer the appropriate behavior. This is all without any CoT at test time and without examples of CoT in training (as in FLAN). Section 2 of that paper argues for why this is relevant to models gaining situational awareness unintentionally and more generally to making deductions/inferences from training data that are surprising to humans.   
  
Relatedly, very interesting [work](https://openreview.net/forum?id=X3JFgY4gvf) from Krasheninnikov et al from David Krueger's group that shows out-of-context inference about the reliability of different kinds of definition. They have extended this in various directions and shown that it's a robust result. Finally, [Grosse et al](https://arxiv.org/abs/2308.03296) on Influence Functions gives evidence that as models scale, their outputs are influenced by training documents that are related to the input/output in abstract ways -- i.e. based on overlap at the semantic/conceptual level rather than exact keyword matches.  
  
Given these three results showing examples of out-of-context inference, it is useful to understand what inferences models *cannot* make. Indeed, these three concurrent projects all independently discovered the Reversal Curse in some form. It's a basic result once you start exploring this space. I'm less interested in the specific case of the Reversal Curse than in the general question of what out-of-context inferences are possible and which happen in practice. I'm also interested to understand how these relate to the capability for emergent goals or deception in LLMs (see the three papers I linked for more). 

> And this is a general dilemma: if a problem+answer shows up at least occasionally in the real world / datasets proxying for the real world, then a mere approximator or memorizer can learn the pair, by definition; and if it doesn't show up occasionally, then it can't matter to performance and needs a good explanation why we should care.

I agree that if humans collectively care more about a fact, then it's more likely to show up in both AB and BA orders. Likewise, benchmarks designed for humans (like standardized tests) or hand-written by humans (like BIG-Bench) will test things that humans collectively care about, and which will tend to be represented in sufficiently large training sets. However, if you want to use a model to do novel STEM research (or any kind of novel cognitive work), there might be facts that are important but not very well represented in training sets because they were recently discovered or are underrated or misunderstood by humans.   
  
On the point about logic, I agree with much of what you say. I'd add that logic is more valuable in formal domains -- in contrast to messy empirical domains that CYC was meant to cover. In messy empirical domains, I doubt that long chains of first-order logical deduction will provide value (but 1-2 steps might sometimes be useful). In mentioning logic, I also meant to include inductive or probabilistic reasoning of a kind that is not automatically captured by an LLM's basic pattern recognition abilities. E.g. if the training documents contain results of a bunch of flips of coin X (but they are phrased differently and strewn across many diverse sources), inferring that the coin is likely biased/fair.   
  
*deductions/inferences. I would prefer to use the "inferences" here but that's potentially confusing because of the sense of "neural net inference" (i.e. the process of generating output from a neural net).