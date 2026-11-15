Comment by Marius Hobbhahn, 2022-12-14, on "Predicting GPU performance"
https://www.lesswrong.com/posts/vnvGhfikBbrjZHMuD/predicting-gpu-performance?commentId=abEmwh9A3Hsjyrx2k

PARENT (not his words):
This is helpful for something I've been working on - thanks!

I was initially confused about how these results could fit with claims from [this paper](https://cset.georgetown.edu/wp-content/uploads/AI-Chips%E2%80%94What-They-Are-and-Why-They-Matter.pdf) on AI chips, which emphasizes the importance of factors other than transistor density for AI-specialized chips' performance. But on second thought, the claims seem compatible:
* The paper argues that increases in transistor density have (recently) been slow enough for investment in specialized chip design to be practical. But that's compatible with increases in transistor density still being the main driver of performance improvements (since a proportionally small boost that lasts several years could still make specialization profitable).
* The paper claims that "AI[-specialized] chips are tens or even thousands of times faster and more efficient than CPUs for training and inference of AI algorithms." But the graph in this post shows less than thousands of times improvements since 2006. These are compatible if remaining efficiency gains of AI-specialized chips came before 2006, which is plausible since GPUs were first released [in 1999](https://en.wikipedia.org/wiki/Graphics_processing_unit) (or maybe the "thousands of times" suggestion was just too high).

HIS COMMENT:
As a follow-up to building the model, I was looking into specialized AI hardware and I have to say that I'm very uncertain about the claimed efficiency gains. There are some parts of the AI training pipeline that could be improved with specialized hardware but others seem to be pretty close to their limits.   
  
We intend to understand this better and publish a piece in the future but it's currently not high on the priority list.   
  
Also, when compared to CPUs, it's no wonder that any parallelized hardware is 1000x more efficient. So it really depends on what the exact comparison is that the authors used.