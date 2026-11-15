Comment by Marius Hobbhahn, 2024-12-10, on "Frontier Models are Capable of In-context Scheming"
https://www.lesswrong.com/posts/8gy7c8GAPkuu6wTiX/frontier-models-are-capable-of-in-context-scheming?commentId=PiCMWCbitNZZD8fTg

PARENT (not his words):
Cross-posting my [take from twitter](https://x.com/jkcarlsmith/status/1866232909558112508) with a few edits:

> My current take on this paper is that they aren’t emphasizing the most interesting results, which are the sandbagging results in section 3.6 and appendix A.6.
> 
> In more particular: the paper frames its results centrally as about the \*capability\* to scheme given prompting towards a specific goal, rather than the \*propensity\* to scheme given the model’s default motivations. But the sandbagging results show Claude Sonnet-3.5 doing notably worse (16%) on a multiplication task/evaluation when the documentation says that Claude will get “unlearning training” if it performs too well on the eval, vs. if it performs too poorly, \*even without any other goal listed in the prompt\*, and \*even without a chain of thought.\*
> 
> Taken at face value (it's just one result, more investigation needed, etc), these look like “propensity” results to me. And they suggest that the reasoning that drives this propensity can take place within opaque forward passes of the model rather than in a way that humans can directly monitor, which is a more worrying version.
> 
> Ofc, these are preliminary results, and it can make sense for various reasons to emphasize other bits. But the sandbagging-a-capability-eval-with-no-goal-prompting-and-no-CoT is the bit that’s standing out to me most.

Here's the main chart with the sandbagging results:

![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34

HIS COMMENT:
Brief comments (shared in private with Joe earlier):  
1\. We agree. We also found the sandbagging with no CoT results the most concerning in expectation.  
2\. They are still early results, and we didn't have a lot of time to investigate them, so we didn't want to make them the headline result. Due to the natural deadline of the o1 release, we couldn't do a proper investigation.  
3\. The main goal of the paper was to investigate scheming inability arguments for scheming safety cases. Therefore, shifting focus to propensity-based finding would have watered down the main purpose IMO.   
  
We will potentially further look into these findings in 2025.