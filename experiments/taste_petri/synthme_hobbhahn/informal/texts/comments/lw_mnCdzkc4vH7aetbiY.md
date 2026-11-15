Comment by Marius Hobbhahn, 2023-12-16, on "Trends in GPU price-performance"
https://www.lesswrong.com/posts/c6KFvQcZggQKZzxr9/trends-in-gpu-price-performance?commentId=mnCdzkc4vH7aetbiY

HIS COMMENT:
In a narrow technical sense, this post still seems accurate but in a more general sense, it might have been slightly wrong / misleading.   
  
In the post, we investigated different measures of FP32 compute growth and found that many of them were slower than Moore's law would predict. This made me personally believe that compute might be growing slower than people thought and most of the progress comes from throwing more money at larger and larger training runs. While most progress comes from investment scaling, I now think the true effective compute growth is probably faster than Moore's law.   
  
The main reason is that FP32 is just not the right thing to look at in modern ML and we even knew this at the time of writing, i.e. it ignores tensor cores and lower precisions like TF16 or INT8.   
  
I'm a little worried that people who read this post but don't have any background in ML got the wrong takeaway from the post and we should have emphasized this difference even more at the time. We have written a follow-up post about this recently here: [https://epochai.org/blog/trends-in-machine-learning-hardware](https://epochai.org/blog/trends-in-machine-learning-hardware)  
I feel like the new post does a better job at explaining where compute progress comes from.