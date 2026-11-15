Comment by Marius Hobbhahn, 2023-03-22, on "Clarifying mesa-optimization"
https://www.lesswrong.com/posts/NpJkFLBJEq7JQt7oy/clarifying-mesa-optimization?commentId=jrfuAnHLwnNGYBg7h

PARENT (not his words):
There has been some work on understanding in-context learning which suggests that models are doing literal gradient descent:

*   [Transformers learn in-context by gradient descent](https://arxiv.org/pdf/2212.07677.pdf)
*   [What learning algorithm is in-context learning? investigations with linear models](https://arxiv.org/pdf/2211.15661.pdf)
*   [Why Can GPT Learn In-Context? Language Models Secretly Perform Gradient Descent as Meta-Optimizers](https://arxiv.org/pdf/2212.10559.pdf)

> Superposition allows the model to do a lot of things at once. Thus, if the model wants to use its space efficiently, it performs multiple steps at once or uses highly compressed heuristics even if they don’t cover all corner cases. Especially in feed-forward models, the model can’t repeatedly apply the same module. Thus, implementing a “clean” algorithm would require implementing a similar algorithm in multiple layers which seems very space inefficient. 

I think the first and last sentence are inconsistent. Since superposition lets you do so much at once, you can get away with having this redundancy in every layer, *especially* if this capacity is dedicated to a general search process that would reduce loss across a wide variety of tasks.

> When models are trained to solve small optimization tasks like [Knapsack](https://en.wikipedia.org/wiki/Knapsack_problem), they will not rediscover either the recursive or the dynamic programming solution

I think it depends on the problem size. If the nu

HIS COMMENT:
How confident are you that the model is literally doing gradient descent from these papers? My understanding was that the evidence in these papers is not very conclusive and I treated it more as an initial hypothesis than an actual finding.   
  
Even if you have the redundancy at every layer, you are still running copies of the same layer, right? Intuitively I would say this is not likely to be more space-efficient than not copying a layer and doing something else but I'm very uncertain about this argument.   
  
I intend to look into the Knapsack + DP algorithm problem at some point. If I were to find that the model implements the DP algorithm, it would change my view on mesa optimization quite a bit.