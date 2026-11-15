Comment by Marius Hobbhahn, 2025-06-02, on "Claude Sonnet 3.7 (often) knows when it’s in alignment evaluations"
https://www.lesswrong.com/posts/E3daBewppAiECN3Ao/claude-sonnet-3-7-often-knows-when-it-s-in-alignment?commentId=to7BEa57i7D9vaY3E

PARENT (not his words):
I'm not entirely clear what the implications would be one way or the other, but do we know if models mistakenly take production deployments to be evaluation scenarios? We might be assuaged that our evaluations are still predictive if the model just always thinks it's probably still in training (which, after all, it has been for its entire "life" so far). Perhaps it would even be sufficient for the model to suspect it is being tested every time it finds itself in a high-stakes scenario.

HIS COMMENT:
In one of my MATS projects we found that some models have a bias to think they're always being evaluated, including in real-world scenarios. The paper isn't public yet. But it seems like a pretty brittle belief that the models don't hold super strongly. I think this can be part of a strategy, but should never be load-bearing.