Comment by Owain_Evans, 2023-10-20, on "AI #34: Chipping Away at Chip Exports"
https://www.lesswrong.com/posts/ApPKqx9b8LogfKxAr/ai-34-chipping-away-at-chip-exports?commentId=ZyxfwzZhubZuHetJT

PARENT (not his words):
> A year from now these drones will be running open source multimodal models that can navigate complex environments, recognize faces, and think step-by-step about how to cause the most damage.

  
I am skeptical. How small can language models be and still see large benefits from chain of thought? Anyone have a good sense of this? I should know this...  
  
Anyhow if the answer is "they gotta be, like, 70B at least" then I doubt that'll be running at speed on a drone for several more years. Though I haven't done any actual calculations with actual numbers so I'd love to be corrected.

HIS COMMENT:
My guess is that a model with 1-10B params could benefit from CoT if trained using these techniques (https://arxiv.org/abs/2306.11644, [https://arxiv.org/abs/2306.02707).](https://arxiv.org/abs/2306.02707\).) Then there's reduced precision and other tricks to further shrink the model.   
That said, I think there's a mismatch between state-of-the-art multi-modal models (huge MoE doing lots of inference time compute using scaffolding/CoT) that make sense for many applications and the constraints of a drone if it needs to run locally and produce fast outputs.