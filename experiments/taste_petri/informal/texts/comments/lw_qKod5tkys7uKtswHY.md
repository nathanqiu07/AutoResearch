Comment by Owain_Evans, 2025-03-15, on "Emergent Misalignment: Narrow finetuning can produce broadly misaligned LLMs"
https://www.lesswrong.com/posts/ifechgnJRtJdduFGC/emergent-misalignment-narrow-finetuning-can-produce-broadly?commentId=qKod5tkys7uKtswHY

PARENT (not his words):
I'm attempting to duplicate this with my own dataset, based on CVEfixes with the diffs reversed and converted to FIM-style code assistant prompts. It's only 48k examples, limited to patches with < 100 lines. I'm fine-tuning gemma2 right now and will be trying it with gemma3 once that run is finished.

HIS COMMENT:
Cool. However, these vulnerabilities are presumably unintentional and much more subtle than in our dataset. So I think this is interesting but less likely to work. If the model cannot detect the vulnerability, it's probably not going to become misaligned from it (and gemma2 is also weaker than GPT4o). 