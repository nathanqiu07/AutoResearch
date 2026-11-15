Comment by Owain_Evans, 2023-09-24, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=tXbNuNkuDFtGH6uec

PARENT (not his words):
> We think the results of Experiment #1 would be similar if we pretrained a model from scratch and included the same dataset. Do you disagree? (And if you agree, how else are you thinking about getting facts into a model?)

Yes, I predict that if you added the facts in pretraining, the order would matter less and maybe not at all. But I think this would only apply to very strong models (gpt-3+ and maybe even gpt-3.5-instruct-turbo+).

Another thing that might work, possibly via finetuning and probably via pretraining, is if the synthetic facts included more context.

e.g. `Daphne Barrington is the director of "A Journey Through Time". She also wrote and directed "A Journey Through Time 2". She is well-known for her time-based movies.`

(Why do I expect this to work? Because the model then sees examples where "She" follows a "A Journey Through Time" in contexts where it's knowable that "She" refers to Daphne. )

Less confidently, I predict that if you finetuned an even weaker model (e.g. text-ada-001, or a ~100m parameter open-source model, perhaps also finetuning more aggressively than is possible through the OpenAI finetuning API), you would also get a different result, assuming the model was able to learn the non-reversed fact via finetuning at all.

HIS COMMENT:
> Yes, I predict that if you added the facts in pretraining, the order would matter less and maybe not at all. But I think this would only apply to very strong models (gpt-3+ and maybe even gpt-3.5-instruct-turbo+).

There are two pieces of evidence against this. The influence function results, showing the Reversal Curse for models better than GPT-3, and our results in Experiment 2 for GPT3.5 and GPT-4.   
 

>   
> Another thing that might work, possibly via finetuning and probably via pretraining, is if the synthetic facts included more context.

If the training set includes texts of the form "A is B. A is also C", then you have both orders present (A is B and B is A) and so the Reversal Curse is not applicable.   
  
We trained ada, which is 350M parameters. We trained Llama-1 "aggressively" (e.g. for many epochs and with a hyperparameter sweep). It's all in the paper.