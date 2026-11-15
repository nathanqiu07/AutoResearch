Comment by Marius Hobbhahn, 2022-06-04, on "Deep Learning Systems Are Not Less Interpretable Than Logic/Probability/Etc"
https://www.lesswrong.com/posts/gebzzEwn2TaA6rGkc/deep-learning-systems-are-not-less-interpretable-than-logic?commentId=ukmCnp6ZCFgBD8476

HIS COMMENT:
I think the claim you are making is correct but it still misses a core point of why some people think that Bayes nets are more interpretable than DL.   
a) Complexity: a neural network is technically a Bayes net. It has nodes and variables and it is non-cyclical. However, when people talk about the comparison of Bayes nets vs. NNs, I think they usually mean a smaller Bayes net that somehow "captures all the important information" of the NN.   
b) Ontology:  When people look at a NN they usually don't know what any particular neuron or circuit does because it might use different concepts than humans use when they think about the same topic. When people use a Bayes net they usually assume that the nodes reflect concepts that humans use.  So it is more interpretable in practice.   
  
I think that there is a case for using Bayes Nets in combination with NNs to get higher interpretability and I'll write a post on that in the future.