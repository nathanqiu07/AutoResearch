Comment by Marius Hobbhahn, 2023-02-13, on "LLM Basics: Embedding Spaces - Transformer Token Vectors Are Not Points in Space"
https://www.lesswrong.com/posts/pHPmMGEMYefk9jLeh/llm-basics-embedding-spaces-transformer-token-vectors-are?commentId=ZpJRnGzR4B9spaZzk

PARENT (not his words):
I'm pretty sure the main reason it's good to think of features/tokens as being directions is because of layer norm. All any "active" component of the neural network "sees" is the direction of the residual stream, and not its magnitude, since layer norm's output is always norm 1 (before applying the scale and bias terms). You do mention this in part 1.2, but I think it should be mentioned elsewhere (e.g. Intro, Part 2, Conclusion), as it seems pretty important?

HIS COMMENT:
I agree that the layer norm does some work here but I think some parts of the explanation can be attributed to the inductive bias of the cross-entropy loss. I have been playing around with small toy transformers without layer norm and they show roughly similar behavior as described in this post (I ran different experiments, so I'm not confident in this claim).   
  
My intuition was roughly:  
\- the softmax doesn't care about absolute size, only about the relative differences of the logits.  
\- thus, the network merely has to make the correct logits really big and the incorrect logits small  
\- to get the logits, you take the inner product of the activations and the unembedding. The more aligned the directions of the correct class with the corresponding unembedding weights are (i.e. the smaller their cosine similarity), the bigger the logits.  
\- Thus, direction matters more than distance.   
  
Layernorm seems to even further reduce the effect of distance but I think the core inductive bias comes from the cross-entropy loss.