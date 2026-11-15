Comment by Owain_Evans, 2022-02-27, on "How do new models from OpenAI, DeepMind and Anthropic perform on TruthfulQA?"
https://www.lesswrong.com/posts/yYkrbS5iAwdEQyynW/how-do-new-models-from-openai-deepmind-and-anthropic-perform?commentId=5X2wPECauiKfLpjuL

PARENT (not his words):
Any plans on evaluating [RETRO](https://deepmind.com/research/publications/2021/improving-language-models-by-retrieving-from-trillions-of-tokens) (the retrieval augmented transformer from DeepMind) on TruthfulQA? I'm guessing it should perform similarly to WebGPT but would be nice to get a concrete number.

HIS COMMENT:
It would be interesting to evaluate RETRO as it works differently from all the models we've evaluated. WebGPT is finetuned to use a search engine and it uses this (at inference time) to answer questions. This seems more powerful than the retrieval system for RETRO (based on a simple nearest neighbor lookup). So my speculation is that WebGPT would do better.
 
We don't have plans to evaluate it but are open to the possibility (if the RETRO team was interested).