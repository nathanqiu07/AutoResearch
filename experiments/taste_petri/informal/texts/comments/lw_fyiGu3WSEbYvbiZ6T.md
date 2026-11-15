Comment by Owain_Evans, 2023-08-12, on "LLMs are (mostly) not helped by filler tokens"
https://www.lesswrong.com/posts/oSZ2xTxEMZh9f3Yaz/llms-are-mostly-not-helped-by-filler-tokens?commentId=fyiGu3WSEbYvbiZ6T

PARENT (not his words):
> But I wouldn't index on his results too much because I'm unsure how replicable they are.

OK. If Oam really was using a single IC token and getting benefits, then I think that would point to the forward-pass/additional-model-parameters-activated explanation: obviously, his model is unaffected by RLHF, MoEs, model scaling, or anything of the alternate hypotheses. He should probably look into that if he can replicate padding benefits. It would not necessarily resolve the question for larger models, but at least it'd establish such an effect exists in some model implementations.

> Claude with RLAIF (which is basically the same)

I don't think RLAIF is 'basically the same'. I find Claude to be qualitatively highly different from RLHF'd models - as I've commented before, the RLHF seems to cause some rather perverse consequences that RLAIF avoids. For example, you cannot ask ChatGPT to "Write a non-rhyming poem." - I've tried this prompt dozens of times, and it always writes a rhyming poem, even if you explicitly then tell it it incorrectly wrote a rhyming poem and to try again, while Claude nails it without trouble.

RLHF seems to distort the entire distribution of outputs to be on-policy and suck all outputs into the vortex of RLHF'd-pablum, while RLAIF seems to be far more selective and mostly affect directly-morality-relevant outputs, leaving neutral stuff like 'write a poem' undistorted.

> My main pushback here is I'd be pretty surprised if gradient descent so inefficientl

HIS COMMENT:
ChatGPT-4 seems to have improved at diverse literary styles. It sometimes ignores the "non-rhyming" instructions, but I was able to get it to avoid rhyme on my second try by first asking it, "Can you write poems that don't rhyme?".

[https://chat.openai.com/share/698343c1-764e-4a65-9eb8-f2ec4e40da1b](https://chat.openai.com/share/698343c1-764e-4a65-9eb8-f2ec4e40da1b)  
![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34m86e5f/images/a633f88549161d312a90ab7a4288321a6627d036fc519349.png)