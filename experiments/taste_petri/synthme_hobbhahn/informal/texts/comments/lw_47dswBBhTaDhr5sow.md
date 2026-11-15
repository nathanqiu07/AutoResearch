Comment by Marius Hobbhahn, 2023-03-31, on "Clarifying mesa-optimization"
https://www.lesswrong.com/posts/NpJkFLBJEq7JQt7oy/clarifying-mesa-optimization?commentId=47dswBBhTaDhr5sow

PARENT (not his words):
Overall, strong upvote, I like this post a lot, these seem like good updates you've made.

> we think that mesa-optimizers will primarily use a complicated stack of heuristics that takes elements from different clean optimization procedures. In the future, these internal heuristics might be combined with external optimization procedures like calculators or physics engines. This is similar to how humans that play chess don't actually run a tree-search of depth n with alpha-beta pruning in their heads.

I agree. [Heuristic-free search seems very inefficient and inappropriate for real-world intelligence](https://www.lesswrong.com/posts/22xf8GmwqGzHbiuLg/seriously-what-goes-wrong-with-reward-the-agent-when-it?commentId=8c8TkShFifX34wjwB#LQLNToajwTcpeyfE5). 

> we think it will be much harder to learn something about search in a toy model and transfer that to a larger model because the kind of mesa-optimization is much more messy and diverse than this hypothesis assumes.

I agree. However, I agree with this as an argument against *direct* insight transfer from toy->real-world models. If you don't know how to do anything with anything for how e.g. an adult would plan real-world takeover, start simple IMO.

> Second, we expect that when general-purpose models like GPT-3 are playing chess, they do not call an internal optimizer. Instead, they might apply heuristics that either have small components of optimization procedures or are approximations of aspects of explicit optimization. 

HIS COMMENT:
Thank you!  
  
I also agree that toy models are better than nothing and we should start with them but I moved away from "if we understand how toy models do optimization, we understand much more about how GPT-4 does optimization".   
  
I have a bunch of project ideas on how small models do optimization. I even trained the networks already. I just haven't found the time to interpret them yet. I'm happy for someone to take over the project if they want to. I'm mainly looking for evidence against the outlined hypothesis, i.e. maybe small toy models actually do fairly general optimization. Would def. update my beliefs.   
  
I'd be super interested in falsifiable predictions about what these general-purpose modules look like. Or maybe even just more concrete intuitions, e.g. what kind of general-purpose modules you would expect GPT-3 to have. I'm currently very uncertain about this.   
  
I agree with your final framing.