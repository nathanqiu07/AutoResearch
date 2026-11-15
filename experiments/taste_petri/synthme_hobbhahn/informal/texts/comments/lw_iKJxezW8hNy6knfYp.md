Comment by Marius Hobbhahn, 2021-12-13, on "What’s the backward-forward FLOP ratio for Neural Networks?"
https://www.lesswrong.com/posts/fnjKpBoWJXcSDwhZk/what-s-the-backward-forward-flop-ratio-for-neural-networks?commentId=iKJxezW8hNy6knfYp

PARENT (not his words):
One potential issue: looking at FLOPs here might be misleading. Both my own experience and what I've heard from others suggests that a hand-coded gradient calculation (i.e. writing out the backprop steps by hand) typically has runtime within a factor of ~2-3 of the runtime of the original function (and it computes the original function at the same time). That's right in line with what you'd expect from counting FLOPs. But automated differentiation libraries typically introduce a lot of inefficient overhead; runtimes ~10X the runtime of the original function are typical. Or at least that was the case five years ago; I haven't done as much numerical work with pytorch, but I'd guess that it's similar.

HIS COMMENT:
Adding to what Jaime already said: I think there are two things we might care about when thinking about FLOP.   
1\. We could care about the theoretical number of FLOP a method might use independent of architecture, exact GPU, etc. This might be useful to compare methods independent of which exact setup is the current flavor of the month. It might also be useful to compare current methods against methods from 5 years ago or 5 years from now. Then the setup we describe in the post seems to be the best fit.  
2\. We could care about the actual FLOP count that an algorithm uses in the specific setup it is used in, e.g. with a specific GPU, software, and low-level optimizer. This might be useful when comparing different GPUs and their efficiency. Then it is more accurate to use high-level proxies such as GPU-time.   
  
In the first case, the overhead is a distraction in the second it is part of the thing we care about.