Comment by Owain_Evans, 2024-10-20, on "LLMs can learn about themselves by introspection"
https://www.lesswrong.com/posts/L3aYFT4RDJYHbbsup/llms-can-learn-about-themselves-by-introspection?commentId=iCdnckrCFQoSY8iB3

PARENT (not his words):
> What definition of introspection do you have in mind and how would you test for this?

"Prompts involving longer responses" seems like a good start. Basically, if the model could "reflect on itself" in some sense, this presumably implies the ability to access some sort of hierarchical self-model, i. e., make *high-level* predictions about its behavior, without actually *engaging in* that behavior. For example, if it has a "personality trait" of "dislikes violent movies", then its review of a slasher flick would presumably be negative – and it should be able to predict the sentiment of this review as negative *in advance*, without actually writing this review *or* running a detailed simulation of itself-writing-its-review.

The ability to engage in "self-simulation" already implies the above ability: if it has a model of itself detailed enough to instantiate it in its forward passes and then fetch its outputs, it'd presumably be even easier for it to just *reason over* that model without running a detailed simulation. (The same way, if you're asked to predict whether you'd like a movie from a genre you hate, you don't need to run an immersive mental simulation of watching the movie – you can just map the known self-fact "I dislike this genre" to "I would dislike this movie".)

HIS COMMENT:
I agree about the "longer responses".
 
I'm unsure about the "personality trait" framing. There are two senses of "introspection" for humans. One is introspecting on your current mental state ("I feel a headache starting") and the other is being introspective about patterns in your behavior (e.g. "i tend to dislike violent movies" or "i tend to be shy among new people"). The former sense is more relevant to philosophy and psychology and less often discussed in daily life. The issue with the latter sense is that a model may not have privileged access to facts like this -- i.e. if another model had the same observational data then it could learn the same fact.

So I'm most interested in the former kind of introspective, or in cases of the latter where it'd take large and diverse datasets (that are hard to construct) for another model to make the same kind of generalization.