Comment by Owain_Evans, 2023-09-05, on "Paper: On measuring situational awareness in LLMs"
https://www.lesswrong.com/posts/mLfPHv4QjmeQrsSva/paper-on-measuring-situational-awareness-in-llms?commentId=mhfkdMNohXDp3svFm

PARENT (not his words):
This paper seems pretty cool! 

I've for a while thought that alignment-related content should maybe be excluded from pretraining corpora, and held out as a separate optional dataset. This paper seems like more support for that, since describing general eval strategies and specific evals might allow models to 0-shot hack them. 

Other reasons for excluding alignment-related content:

*   "Anchoring" AI assistants on our preconceptions about alignment, reducing our ability to have the AI generate diverse new ideas and possibly conditioning it on our philosophical confusions and mistakes
*   Self-fulfilling prophecies around basilisks and other game-theoretic threats

HIS COMMENT:
Good points. As we note in the paper, this may conflict with the idea of automating alignment research in order to solve alignment. Aaron_Scher makes a related point. 

More generally, it's uncertain what the impact is of excluding a certain topic from pretraining. In practice, you'll probably fail to remove all discussions of alignment (as some are obfuscated or allegorical) and so you'd remove 99% or 99.9% rather than 100%. The experiments in our paper, along with the influence functions [work](https://arxiv.org/abs/2308.03296) by Grosse et al. could help us understand what the impact of this is likely to be.