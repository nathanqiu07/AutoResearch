Comment by Owain_Evans, 2023-12-20, on "Paper: Tell, Don't Show- Declarative facts influence how LLMs generalize"
https://www.lesswrong.com/posts/DR67cnvgCXw7CkXbd/paper-tell-don-t-show-declarative-facts-influence-how-llms?commentId=iTiqDfTJe2nb6md8f

PARENT (not his words):
It would be interesting to know how close this behavior is to Bayesian reasoning during training. My first assumption would be that this is building concept in layers close enough to the middle of the model that they are independent of keyword matching or language choice, and are instead dealing with semantic concepts, and that the training process is implementing something close to Bayesian reasoning to construct a model of aspects of the world, during which the generalization you demonstrate happens. Then at generation time that model is accessed to help to answer the user's request.

HIS COMMENT:
I agree it's good to consider how the behavior of models on our tasks relates to optimal Bayesian reasoning. That said, I'm not sure how to define or calculate the "groundtruth" for optimal reasoning. (Does it depend on using the pretraining distribution as a prior and if so how should we estimate that? How to think about the distinction between in-context and out-of-context reasoning?).  
  
In any case, there is some evidence against models being close to Bayesian optimality (however exactly optimality is defined):  
1\. Results on the same task differ between GPT-3 and Llama-2 models (two models that have fairly similar overall capabilities). Llama-2 being slightly more influenced by declarative information.   
2\. From the Bayesian perspective, including "realized descriptions" should have a significant impact on how much the model is influenced by "unrealized descriptions". The effects we see seem smaller than expected (see Figure 4 and Table 2).   
  
Incidentally, I like the idea of testing in different languages to see if the model is encoding in the information more abstractly.