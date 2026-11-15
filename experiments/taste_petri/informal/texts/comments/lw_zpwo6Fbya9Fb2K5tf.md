Comment by Owain_Evans, 2024-10-19, on "LLMs can learn about themselves by introspection"
https://www.lesswrong.com/posts/L3aYFT4RDJYHbbsup/llms-can-learn-about-themselves-by-introspection?commentId=zpwo6Fbya9Fb2K5tf

PARENT (not his words):
It seems obvious that a model would better predict its own outputs than a separate model would. Wrapping a question in a hypothetical feels closer to rephrasing the question than probing "introspection". Essentially, the response to the object level and hypothetical reformulation both arise from very similar things going on in the model rather than something emergent happening.

As an analogy, suppose I take a set of data, randomly partition it into two subsets (A and B), and perform a linear regression and logistic regression on each subset. Suppose that it turns out that the linear models on A and B are more similar than any other cross-comparison (e.g. linear B and logistic B). Does this mean that linear regression is "introspective" because it better fits its own predictions than another model does?

I'm pretty sure I'm missing something as I'm mentally worn out at the moment. What am I missing?

HIS COMMENT:
> Wrapping a question in a hypothetical feels closer to rephrasing the question than probing "introspection"

Note that models perform poorly at predicting properties of their behavior in hypotheticals without finetuning. So I don't think this is just like rephrasing the question. Also, GPT3.5 does *worse* at predicting GPT-3.5 than Llama-70B does at predicting GPT-3.5 (without finetuning), and GPT4 is only a little better at predicting itself than are other models.  
 

>   
> >Essentially, the response to the object level and hypothetical reformulation both arise from very similar things going on in the model rather than something emergent happening.  
>  

While we don't know what is going on internally, I agree it's quite possible these "arise from similar things". In the paper we discuss "self-simulation" as a possible mechanism. Does that fit what you have in mind? Note: We are not claiming that models must be doing something very self-aware and sophisticated. The main thing is just to show that there is introspection according to our definition. Contrary to what you say, I don't think this result is obvious and (as I noted above) it's easy to run experiments where models do not show any advantage in predicting themselves.