Comment by Marius Hobbhahn, 2024-11-12, on "The Evals Gap"
https://www.lesswrong.com/posts/gJJEjJpKiddoYGZKk/the-evals-gap?commentId=CyhyhFM6vH3kLQEHu

PARENT (not his words):
> Why are you sure that effective "evals" can exist even in principle?

Relatedly, the point which is least clear to me is what exactly would it mean to solve the "proper elicitation problem" and what exactly are the "requirements" laid out by the blue line on the graph. I think I'd need to get clear on this problem scope before beginning to assess whether this elicitation gap can even in principle be crossed via the methods which are being proposed (i.e. better design & coverage of black box evaluations). 

As a non-example, possessing the kind of foundational scientific understanding which would allow someone to confidently say "We have run this evaluation suite and we now know once and for all that this system is definitely not capable of x, regardless of whatever elicitation techniques are developed in the future" seems me to be Science-of-AI-complete and is thus a non-starter for a north star for an agenda aimed at developing stronger inability arguments.

When I fast forward the development of black box evals aimed at supporting inability arguments, I see us arriving at a place where we have: 

1.  More SWE-Benchesque evaluations across critical domains which are perhaps "more Verified" by having higher quality expert judgement passed upon them.
2.  Some kind of library which brings together a family of different SOTA prompting and finetuning recipes to apply to any evaluation scenario.
3.  More data points and stronger [forecasts for post training enhancements](https:/

HIS COMMENT:
These are all good points. I think there are two types of forecasts we could make with evals:  
  
1\. strict guarantees: almost like mathematical predictions where we can proof that the model is not going to behave in a specific way even with future elicitation techniques.   
2\. probabilistic predictions: We predict a distribution of capabilities or a range and agree on a threshold that should not be crossed. For example, if the 95% upper bound of that distribution crosses our specified capability level, we treat the model differently.   
  
I think the second is achievable (and this is what the post is about), while the first is not. I expect we will have some sort of detailed scaling laws for LM agent capabilities and we will have a decent sense of the algorithmic progress of elicitation techniques. This would allow us to make a probabilistic prediction about what capabilities any given model is likely to have, e.g. if a well-motivated actor is willing to spend $1M on PTE in 4 years.   
  
Additionally, I expect that we would get quite a long way with what Lucas calls "meta-evaluative practices", e.g. getting a better sense of how wrong our past predictions were and accounting for that. I think this could have the form of "We invested $1M, 10 FTE-years and X FLOP to elicit the best capabilities; Let's predict what 10x, 100x, 1000x, etc." of that could achieve accounting for algorithmic progress.   
  
Finally, I really think evals are just one part of a bigger defense-in-depth strategy. We still need control, scalable oversight, interpretability, governance, etc. The post is merely trying to express that for the evals part of that strategy, we should internalize which kind of scientific rigor we will likely need for the decisions we have tied to evals results and make sure that we can achieve them.