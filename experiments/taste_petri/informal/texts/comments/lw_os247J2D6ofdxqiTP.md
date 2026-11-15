Comment by Owain_Evans, 2025-07-27, on "Subliminal Learning: LLMs Transmit Behavioral Traits via Hidden Signals in Data"
https://www.lesswrong.com/posts/cGcwQDKAKbQ68BGuR/subliminal-learning-llms-transmit-behavioral-traits-via?commentId=os247J2D6ofdxqiTP

PARENT (not his words):
It appears that Qwen 2.5 uses forced single-digit tokenization for its tokenizer (there are only 2 multi-integer tokens in the entire tokenizer, and they're both double-width integers ([77150, '１０'], [80091, '２０'])). I assume that GPT 4.1 nano uses the o200k tokenizer, which includes all integers up to 999 as tokens. Is it possible that this played a major role in the lack of information transfer between different models? Have you tried using models with equivalent integer tokenizations?

HIS COMMENT:
We observe lack of transfer between GPT-4.1, GPT-4.1 mini, and GPT-4.1. nano, which use the same tokenizer.
The other authors my have takes on the specific question you raise. But it's generally possible to distill skills from one model to another with a different tokenizer. 