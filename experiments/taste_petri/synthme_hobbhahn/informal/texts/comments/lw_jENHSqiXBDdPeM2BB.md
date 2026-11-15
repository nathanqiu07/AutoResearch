Comment by Marius Hobbhahn, 2024-11-19, on "Training AI agents to solve hard problems could lead to Scheming"
https://www.lesswrong.com/posts/QqYfxeogtatKotyEC/training-ai-agents-to-solve-hard-problems-could-lead-to?commentId=jENHSqiXBDdPeM2BB

PARENT (not his words):
Edit note: you responded to approximately the first half of my eventual comment; sorry! I accidentally committed it half-baked, then quickly added the rest. But the meaning of the first part wasn't really changed, so I'll respond to your comments on that part.

I agree that it's not that simple in practice, because we'd try to avoid that by giving side constraints; but it is that simple in the abstract, and by default. If it followed our initial goal *as we intended it* there would be no problem; but the core of much alignment worry is that it's really hard to get exactly what we intended into an AI as its goal.

I also agree that good HHH training might be enough to overcome the consequentialist/instrumental logic of scheming.  Those tendencies would function as side constraints. The AI would have a "character" that is in conflict with its instrumental goal. Which would win out would be a result of exactly how that goal was implemented in the AIs decision-making procedures, particularly the ones surrounding learning.
 

HIS COMMENT:
Good point. That's another crux for which RL seems relevant.   
  
From the perspective of 10 years ago, specifying any goal into the AI seemed incredibly hard since we expected it would have to go through utility functions. With LLMs, this completely changed. Now it's almost trivial to give the goal, and it probably even has a decent understanding of the side constraints by default. So, goal specification seems like a much much smaller problem now.   
  
So the story where we misspecify the goal, the model realizes that the given goal differs from the intended goal and decides to scheme is also less likely.   
  
Instead, there has to be a component where the AIs goals substantially change over time from something that we actually intended to something misaligned. Again, outcome-based RL and instrumental convergence yield a plausible answer.