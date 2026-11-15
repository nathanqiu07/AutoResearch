Comment by Owain_Evans, 2023-09-24, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=kdhqGbQFdbmMzEKLx

PARENT (not his words):
Experiment 1 seems to demonstrate limitations of training via finetuning, more so than limitations of the model itself.

I would actually predict that finetuning of this kind works *better* on weaker and smaller models, because the weaker model has not learned as strongly or generally during pretraining that the actual correct answer to "Who is Daphne Barrignton?" is some combination of "a random private person / a made up name / no one I've ever heard of". The finetuning process doesn't just have to "teach" the model who Daphne Barrington is, it also has to overcome the model's prior "knowledge" of not knowing (or knowing that the name is made up).

Similarly, I would expect that stronger models are more capable of noticing logical inconsistencies in either their training data or prompt, compared to weaker models.

For example, even a weak model will get the reversal problem correct when the information is right there in the prompt:

Prompt:

    Daphne Barrington is the director of "A Journey Through Time".
    
    Who directed "A Journey Through Time"?

text-ada-001 completion:

    Daphne Barrington is the director of "A Journey Through Time".
    

(other models also get this right.)  
  
But consider when the prompt contains inconsistent information:

Prompt:

    Daphne Barrington is the only director of "A Journey Through Time".
    Uriah Hawthorne is the only director of "A Journey Through Time".
    
    Who directed "A Journey Through Time"?
    

text-ada-001 com

HIS COMMENT:
> >Experiment 1 seems to demonstrate limitations of training via finetuning, more so than limitations of the model itself.

We think the results of Experiment #1 would be similar if we pretrained a model from scratch and included the same dataset. Do you disagree? (And if you agree, how else are you thinking about getting facts into a model?)  
  
The rest of the points are interesting and relate to thoughts we've had. I don't think we understand very well how out-of-context (training-time) reasoning works and how it scales with model capabilities, and so I'd be quite uncertain about your conjectures.