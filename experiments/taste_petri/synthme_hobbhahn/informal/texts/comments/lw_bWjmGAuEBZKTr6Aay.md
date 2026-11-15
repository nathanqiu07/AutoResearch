Comment by Marius Hobbhahn, 2025-11-27, on "Alignment will happen by default. What’s next?"
https://www.lesswrong.com/posts/FJJ9ff73adnantXiA/alignment-will-happen-by-default-what-s-next?commentId=bWjmGAuEBZKTr6Aay

HIS COMMENT:
I'm very surprised that people seem to update this way. My takeaway over the last year has been that misalignment is at least as hard as I thought it was a year ago, or harder, and definitely nowhere near solved.   
  
There were a lot of things that caught developers by surprise, e.g., the reward hacking of the coding models, or emergent misalignment-related issues, or eval awareness messing with the results.   
  
My overall sense is also that high-compute agentic RL makes all problems much harder because you reward the model on consequences, and it's hard to set exactly the right constraints in that setting. I also think eval awareness is rapidly rising and makes alignment harder across the board, and makes scheming-related issues plausible for the first time in real models.   
  
I also feel like none of the tools we have right now really work very well. They are all reducing the problem a bit, potentially enough to carry us for a while, but not enough that I would deeply trust a system built by them.   
\- Interpretability is somewhat useful now, but still not quite able to be used for effective debugging or aligning the internal concepts of the model.   
\- Training-based methods seem to work in a reductionist way, e.g., our anti-scheming training generalized better than I anticipated, but it is clearly not enough, and I don't know how to close the gap.   
\- Control seems promising, but still needs to be validated in practice in much more detail.   
  
Idk, the answers we have right now just don't seem adequate at all to the scale of the problem to me.