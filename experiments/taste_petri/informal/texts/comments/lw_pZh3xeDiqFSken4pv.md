Comment by Owain_Evans, 2024-06-22, on "Connecting the Dots: LLMs can Infer & Verbalize Latent Structure from Training Data"
https://www.lesswrong.com/posts/5SKRHQEFr8wYQHYkx/connecting-the-dots-llms-can-infer-and-verbalize-latent?commentId=pZh3xeDiqFSken4pv

PARENT (not his words):
Suppose that the safety concerns that you outline have occurred.. For example, suppose that for some future LLM, even though we removed all explicit instructions on how to make a nuclear weapon from the training set, we found that (after suitable fine-tuning or jailbreaking) the model was still able to give good instructions on how to design and build a nuclear weapon due to Out Of Context Reasoning.  
  
In that case the obvious next step would be to elicit multiple examples of this behavior, and then apply Influence Functions techniques to these in order to determine which training documents were most being used in the OOCR process to enable this unwanted dangerous capability, and try to find a subset of training documents that could be removed (or at least have certain parts of them censored) from the training set to remove the ability to deduce and carry out the unwanted dangerous capability. Note that this is likely to be a computationally *extremely* expensive process, particularly since it is likely to involve repeatedly retaining a very large LLM with more censored training sets until the unwanted behavior is eliminated.

Even harder to remove would be the ability to use CoT and in-context learning to reconstruct/reinvent and then carry out the unwanted dangerous capability: the more capable the model is, the harder this becomes to prevent. For example, if the model's capabilities include those of a skilled theoretical physicist, with enough CoT work it might well be 

HIS COMMENT:
Yes, if you know what dangerous knowledge you are looking for, you could try to remove it using influence functions. Another approach (potentially much cheaper) is unlearning techniques.

I agree about the CoT point for reconstructing things. If the CoT is faithful/explicit, then this should be easier to monitor by using a second cheaper LLM to block the stronger LLM if it starts thinking about nukes. 
You could imagine censoring whole subject areas from the training (rather than just censoring specific parts of documents). My guess is that this makes learning certain facts extremely hard even without CoT because some facts were only learned by humans after extensive empirical experiments. 