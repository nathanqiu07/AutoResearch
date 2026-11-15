Comment by Owain_Evans, 2023-10-01, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=5HNb7wgPiiqAhdhro

PARENT (not his words):
OK, I think I see what the argument here actually is. You have 2 implicit arguments. First: 'humans learn reversed relationships and are not fundamentally flawed; if NNs fundamentally learned as well as humans and were not fundamentally flawed and learned in a similar way, they would learn reversed relationships; NNs do not, therefore they do not learn as well as humans and are fundamentally flawed and do not learn in a similar way'. So a decoder LLM not doing reversed implies a fundamental flaw. Then the second argument is, 'human brains do not learn using reversing; a NN learning as well as humans using reversing is still not learning like a human brain; therefore, it is fundamentally flawed', and the conjunction is that either a LLM does worse than humans (and is flawed) or 'cheats' by using reversing (and is flawed), so it's flawed.

Barring much stronger evidence about humans failing to reverse, I can accept the first argument for now. 

But if reversing text during pretraining, or the near-strict equivalent of simply switching between mask-all-but-last and mask-all-but-first targets while doing prediction, fixed reversed relationships, that second implicit argument seems to not follow to me, because the premise is unsupported & doubtful. 

We *don't* know how humans learn, and so for all we know, human brains doing self-supervised learning *could* be reversing. If human brains maintained any sort of equivalent of 'context', then they can be doing any arbitrary masking &

HIS COMMENT:
I address the motivations for our Reversal Curse paper in a [reply](https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=HcSWgnu5SJAJeLETs) to your other comment.   
  
My current (highly speculative) guess is that humans do learn one-directionally. We can't easily recite poems backwards line-by-line or word-by-word or phoneme-by-phoneme. We can't understand such reversed language either. It's easy to count down (because we practice that) but harder to do the alphabet backwards (because we don't practice it). Mostly when we memorize facts that are 2-way (unlike poems), we do some minimal amount of reflection/repetition that means both AB and BA are present. E.g. repeating to ourselves "casa, house, casa, house, etc...". For facts we read passively in newspapers, it's trickier to think about becuase we retain relatively little. But my guess is that most facts that we retain at all will be ones that appear in both orders, though that won't be necessary for us learning them (becauase we can reflect on them ourselves).   
[If we don't understand the semantics of what we are hearing at all, then we don't memorize. E.g. Americans might hear a lot of Spanish on the streets but but memorize basically nothing.]