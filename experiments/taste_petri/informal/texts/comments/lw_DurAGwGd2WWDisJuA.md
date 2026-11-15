Comment by Owain_Evans, 2025-03-02, on "Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs"
https://www.lesswrong.com/posts/ifechgnJRtJdduFGC/emergent-misalignment-narrow-finetuning-can-produce-broadly?commentId=DurAGwGd2WWDisJuA

PARENT (not his words):
Have we already seen emergent misalignment out in the wild?

"Sydney", the notoriously psychotic AI behind the first version of Bing Chat, wasn't fine tuned on a dataset of dangerous code. But it was pretrained on all of internet scraped. Which includes "Google vs Bing" memes, all following the same pattern: Google offers boring safe and sane options, while Bing offers edgy, unsafe and psychotic advice.

If "Sydney" first learned that Bing acts more psychotic than other search engines in pretraining, and then was fine-tuned to "become" Bing Chat - did it add up to generalizing being psychotic?

HIS COMMENT:
We briefly discuss Syndey in the Related Work section of the paper. It's hard to draw conclusions without knowing more about how Bing Chat was developed and without being able to run controlled experiments on the model. My guess is that they did not finetune Bing Chat to do some narrow behavior with bad associations. So the particular phenomenon is probably different. 