Comment by Marius Hobbhahn, 2022-09-15, on "Why deceptive alignment matters for AGI safety"
https://www.lesswrong.com/posts/oBFMbhQMt9HkmfF6d/why-deceptive-alignment-matters-for-agi-safety?commentId=2WbEd7RW6SnWo2EJf

PARENT (not his words):
> AGI safety researchers should focus (only/mostly) on deceptive alignment

I consider this advice actively harmful, and strongly advise to do the opposite.

Let's start at the top:

> By **deceptive alignment**, I mean an AI system that seems aligned to human observers and passes all relevant checks but is, in fact, not aligned...

So far so good. There's obvious reasons why it would make sense to focus exclusively on cases where an AI seems aligned to human observers and passes all relevant checks while still not actually being aligned. After all, [in the cases where we can see the problem, we either fix it or at least iterate until we can't see a problem any more](https://www.lesswrong.com/posts/xFotXGEotcKouifky/worlds-where-iterative-design-fails) (at which point we have "deception" by this definition).

But then the post immediately jumps to a *far* narrower definition of "deceptive alignment":

> In Evan’s post, this means that the NN has actively made an incomplete proxy of the true goal a terminal goal. Note, that the AI is aware of the fact that we wanted it to achieve a different goal and therefore actively acts in ways that humans will perceive as aligned.
> 
> ... In other words, for deception to be at play, I assume that the AI is actively adversarial but pretends not to be.

If we look at e.g. the cases in [Worlds Where Iterative Design Fails](https://www.lesswrong.com/posts/xFotXGEotcKouifky/worlds-where-iterative-design-fails), most of them fit the more-gener

HIS COMMENT:
Thanks for the comment. It definitely pointed out some things that weren't clear in my post and head. Some comments:  
1\. I think your section on psychologizing is fairly accurate. I previously didn't spend a lot of time thinking about how my research would reduce the risks I care about and my theories of change were pretty vague. I plan to change that now.   
2\. I am aware of other failure modes such as fast takeoffs, capability gains in deployment, getting what we measure, etc. However, I feel like all of these scenarios get much worse/harder when deception is at play, e.g. fast takeoffs are worse when they are unnoticed and getting what we measure likely leads to worse outcomes if it is hidden. I would really think of them as orthogonal, e.g. getting what we measure could happen in a deceptive or non-deceptive way. But I'm not sure this is a correct framing.  
3\. It is correct that my definition of deception is inconsistent throughout the article. Thanks for pointing this out. I think it is somewhere between "It's bad if something happens in powerful AIs that we don't understand" to "It's bad if there is an active adversary trying to deceive us". I'll need to think about this for longer.  
4\. Unknown unknowns are a problem. I think my claim as presented in the post is stronger than iI originally intended. However, I think the usefulness of foundational research such as yours comes to a large extent from the fact that it increases our understanding of an AI system in general which then allows us to prevent failure modes (many of which relate to deception).   
  
I'll try to update the post to reflect some of the discussion and my uncertainty better.  Thanks for the feedback.