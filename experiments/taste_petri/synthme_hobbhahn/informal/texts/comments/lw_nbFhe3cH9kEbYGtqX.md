Comment by Marius Hobbhahn, 2023-02-06, on "More findings on Memorization and double descent"
https://www.lesswrong.com/posts/KzwB4ovzrZ8DYWgpw/more-findings-on-memorization-and-double-descent?commentId=nbFhe3cH9kEbYGtqX

PARENT (not his words):
> The common narrative in ML is that the MLP layers are effectively a lookup table (see e.g. “Transformer Feed-Forward Layers Are Key-Value Memories”). This is probably a part of the correct explanation but the true story is likely much more complicated. Nevertheless, it would be helpful to understand how NNs represent their mappings in settings where they are forced to memorize, i.e. can’t learn any general features and basically have to build a dictionary. 

Most probably a noobish question but I couldn't resist asking.

If a neural network learns either to become a lookup table or to generalize over the data, what would happen if we initialized the weights of the network to *be* as much as a lookup table as possible?

For example if you have N=1000 data points and only M=100 parameters. Initialize the 100 weights so that each neuron extracts only 1 random data point (without replacement). Could that somehow speedup the training more than starting from pure randomness or gaussian noise?

If then we could also try with initializing a lookup table based on a quick clustering to ensure good representation of the different features from the get go.

What should I know that would make this an obviously stupid idea?

Thanks!

HIS COMMENT:
I don't think there is a general answer here. But here are a couple of considerations:  
\- networks can get stuck in local optima, so if you initialize it to memorize, it might never find a general solution.  
\- grokking has shown that with high weight regularization, networks can transition from memorized to general solutions, so it is possible to move from one to the other.  
\- it probably depends a bit on how exactly you initialize the memorized solution. You can represent lookup tables in different ways and some are much more liked by NNs than others. For example, I found that networks really don't like it if you set the weights to one-hot vectors such that one input only maps to one feature.  
\- My prediction for empirical experiments here would be something like "it might work in some cases but not be clearly better in the general case. It will also depend on a lot of annoying factors like weight decay and learning rate and the exact way you build the dictionary".