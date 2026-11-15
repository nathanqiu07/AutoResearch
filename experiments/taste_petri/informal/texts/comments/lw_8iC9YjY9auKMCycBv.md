Comment by Owain_Evans, 2022-07-04, on "AI Forecasting: One Year In"
https://www.lesswrong.com/posts/CJw2tNHaEimx6nwNy/ai-forecasting-one-year-in?commentId=8iC9YjY9auKMCycBv

HIS COMMENT:
Very helpful post, thanks!  
  
Are there some meta-level lessons about forecasting a dataset like MATH? IIRC, at the time of these forecasts, the only results were GPT2-finetune and GPT3 few-show (without chain-of-thought and self-consistency). For GPT-2, the accuracy scores were <15% for nearly all subjects and difficulty levels. This may be consistent with GPT-2 either not really understanding questions or being so weak at basic arithmetic that it has no chance for most questions.   
  
Given that performance was so low and that not many models/setups had been tried, there's reason to have a wider distribution on future results. I would still guess that human expert level scores (>95%) should have had very low probability, but even (say) a score of 80% should have had more than 5% chance. (I realize this is posthoc -- I'm not claiming to have made explicit predictions like this).   
  
A good source of baserates/priors would be to look at how performance improves on benchmarks after the paper introducing the benchmark. One example that comes to mind is [Lambada](https://paperswithcode.com/paper/broad-context-language-modeling-as-reading), where performance went from 7.3% in the initial paper to 49% within a year. It'd be cool for someone to plot data from a bunch of benchmarks. Papers with Code will be very helpful but has some missing data. (We might also expect jumpier performance for math-related tasks because once you can do 2-digit arithmetic or elementary algebra reliably then many problems are opened up).