Comment by Owain_Evans, 2023-09-05, on "Paper: On measuring situational awareness in LLMs"
https://www.lesswrong.com/posts/mLfPHv4QjmeQrsSva/paper-on-measuring-situational-awareness-in-llms?commentId=o9vSuzw8DYMurvbBw

PARENT (not his words):
This is a pretty cool paper. Despite feeling overall quite positive about it, I have some reservations:

*   Out-of-context learning seems pretty sensitive to the task being measured, where some of the tasks see nice scaling behavior (hhh) while others do not (incorrect). This observation is based on [Appendix A.1](https://owainevans.github.io/awareness_berglund.pdf#page=24) Table 4, corresponding to Experiment 1b, in this blog post the graph is labeled “(a) Scaling for Experiment 1b (1-hop)”. Now, the fact that you get nice scaling lines when averaging across tasks is not super problematic or anything, but it is a little odd that there is so much variation between tasks, and I think it’s a point against any attempted nice, clean, explanations of the results.
*   The hhh task is the one that small models do well on. I am surprised that the small models do well on any of the tasks. I think the reason they do well on the hhh one is that this task doesn’t seem to require much more than word association and parroting. I would predict that for ada and babbage, if you followed up with “why did you say that?” the models would be unable to reproduce the explicit link that ties the persona to answering in the particular way, whereas I expect davinci to be able to explain this link more. The small models are probably just doing word association where in the training there are a bunch of examples of “Quokka” and the text “I am helpful, harmless, and honest”. In general, I am skeptical o

HIS COMMENT:
Thanks for the thoughtful comments. 

>   
> Out-of-context learning seems pretty sensitive to the task being measured, where some of the tasks see nice scaling behavior (hhh) while others do not (incorrect). This observation is based on [Appendix A.1](https://owainevans.github.io/awareness_berglund.pdf#page=24) Table 4, corresponding to Experiment 1b, in this blog post the graph is labeled “(a) Scaling for Experiment 1b (1-hop)”. Now, the fact that you get nice scaling lines when averaging across tasks is not super problematic or anything, but it is a little odd that there is so much variation between tasks, and I think it’s a point against any attempted nice, clean, explanations of the results.

I agree it's sensitive to the task measured. However, I think this is fairly typical of scaling results. E.g. for BIG-Bench, individual tasks don't have smooth scaling curves (see the "emergence" results) but the curves look smooth when you average over many tasks. (Scaling curves for language modeling loss are implicitly averaging over a huge number of "tasks" because the pretraining set is so diverse).   
  
It would ideal if we had hundreds of tasks (like BIG-Bench) rather than 7, but this is challenging given our setup and the capabilities of the GPT-3 model family. We did run a replication of our main experiment on a disjoint set of tasks (Fig 10b on page 26), which shows similar scaling results. This is some evidence that our our claims would generalize beyond the 7 tasks we chose.