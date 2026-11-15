Comment by Marius Hobbhahn, 2022-01-28, on "Causality, Transformative AI and alignment - part I"
https://www.lesswrong.com/posts/oqzasmQ9Lye45QDMZ/causality-transformative-ai-and-alignment-part-i?commentId=HMbgwBK9THjpYDTmK

PARENT (not his words):
Sure!

I wrote "etc.", but really the main ones I can think of are probably the ones I listed there. Let's start with correlations since this is the really old-school one.

The basic causal principle behind a correlation/covariance-based method is that if you see a correlation where the same thing appears in different places, then that correlation is due to there being a shared cause. This is in particular useful for representation learning, because the shared cause is likely not just an artifact of your perception ("this pixel is darker or lighter") but instead a feature of the world itself ("the scene depicted in this image has properties XYZ"). This then leads to the insight of Factor Analysis[^brgb3qc7o2k]: it's easy to set up a linear generative model with a fixed number of independent latent variables to model your data.

Factor Analysis still gets used a lot in various fields like psychology, but for machine perception it's too bad because perception requires nonlinearity. (Eigenfaces are a relic of the past.) However, the core concept that correlations imply latent variables, and that these latent variables are likely more meaningful features of reality contains to be relevant in many models:

*   Variational autoencoders, generative adversarial networks, etc., learn to encode the distribution of images, and tend to contain a meaningful "latent space" that you can use to generate counterfactual images at a high level of abstraction. They rely on covariances because th

HIS COMMENT:
You state in the first comment that they can be given causal justification.  As far as I understand you argue with covariances above. Can you elaborate on what this causal justification is?