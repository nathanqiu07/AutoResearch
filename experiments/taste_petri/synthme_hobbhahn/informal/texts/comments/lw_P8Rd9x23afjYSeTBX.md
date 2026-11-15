Comment by Marius Hobbhahn, 2023-09-26, on "Understanding strategic deception and deceptive alignment"
https://www.lesswrong.com/posts/fsbcq9z7korjBTP8Z/understanding-strategic-deception-and-deceptive-alignment?commentId=P8Rd9x23afjYSeTBX

PARENT (not his words):
> In current user-facing LLMs like ChatGPT or Claude, the closest approximation to goals may be being helpful, harmless, and honest.

According to my understanding of RLHF, the goal-approximation it trains for is "Write a prompt that is likely to be rated as positive". In ChatGPT / Claude, this is indeed highly correlated with being helpful, harmless, and honest, since the model's best strategy for getting high ratings is to be those things. If models are smarter than us, this may cease to be the case, as being maximally honest may begin to conflict with the real goal of getting a positive rating. (e.g, if the model knows something the raters don't, it will be penalised for telling the truth, which may optimise for deceptive qualities) Does this seem right?

HIS COMMENT:
Seems like one of multiple plausible hypotheses. I think the fact that models generalize their HHH really well to very OOD settings and their generalization abilities in general could also mean that they actually "understood" that they are supposed to be HHH, e.g. because they were pre-prompted with this information during fine-tuning.   
  
I think your hypothesis of seeking positive ratings is just as likely but I don't feel like we have the evidence to clearly say so wth is going on inside LLMs or what their "goals" are.