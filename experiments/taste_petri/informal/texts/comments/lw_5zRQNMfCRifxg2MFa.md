Comment by Owain_Evans, 2019-11-12, on "Neural nets as a model for how humans make and understand visual art"
https://www.lesswrong.com/posts/sg8YjyDBKAF5s2Bgh/neural-nets-as-a-model-for-how-humans-make-and-understand?commentId=5zRQNMfCRifxg2MFa

PARENT (not his words):
There's a long history of development of artistic concepts; for example, the [discovery of perspective](http://www.op-art.co.uk/history/perspective/). There's also lots of artistic concepts where the dependence on the medium is highly significant, of which the first examples that come to mind are cave paintings (which were [likely designed around being viewed by moving firelight](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/50BB05A3FDED8AC8CB5F5126249090F9/S0003598X00062785a.pdf/animation_in_palaeolithic_art_a_preecho_of_cinema.pdf)) and 'highly distorted' ancient statuettes that are [probably self-portraits.](https://s3.amazonaws.com/academia.edu.documents/36257626/Leroy_Scan_1.pdf?response-content-disposition=inline%3B%20filename%3DSelf-Representation_in_Upper_Paleolithic.pdf&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIWOWYYGZ2Y53UL3A%2F20191112%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20191112T031324Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=ec7af8b7791d32ce380cec956c2ad8be10bc70d1a937bb3161134b25a910a08a)

So it seems to me like we should expect there to be a similar medium-relevance for NN-generated artwork, and a similar question of which artistic concepts it possesses and lacks. Perspective, for example, seems pretty well captured by GANs targeting the LSUN bedroom dataset or related tasks. It seems like it's not a surprise that NNs would be good at perspective compared to humans, since there's a cleaner invers

HIS COMMENT:
> There's also lots of artistic concepts where the dependence on the medium is highly significant

Great examples. I agree the physical medium is really important in human art: see my [Section 1.3.1](https://owainevans.github.io/visual_aesthetics/sensory-optimization.html#style-transfer-and-medium-transfer).

> It seems like it's not a surprise that NNs would be good at perspective compared to humans, since there's a cleaner inverse between the perceptive and the creation of perspective from the GAN's point of view than the human's (who has to use their hands to make it, rather than their inverted eyes).

I like the point about hands vs. "inverted eyes". At the same time, the GANs are trained on a huge number of photos, and these photos exhibit a perfect projection of a 3D scene onto a finite-size 2D array. The GAN's goal is to match these photos, not to match 3D scenes (which it doesn't know anything about). Humans invented perspective before having photos to work with. (They did have mirrors and primitive projection techniques.)

> I think most humans have pretty good facility with creating and understanding 'stick figures' that comes from training on a history of communicating with other humans using stick figures, rather than simply generalizing from visual image recognition,

I agree that our facility with stick figures probably depends partly on the history of using stick figures. However, I think our general visual recognition abilities make us very flexible. For example, people can quickly master new styles of abstract depiction that differ from the XKCD style (say in a comic or a set of artworks). DeepMind has a cool recent [paper](https://learning-to-paint.github.io/) where they learn abstract styles of depiction with no human imitation or labeling.

> We might want to look for find concepts that are easier for humans than NNs; when I talk to people about ML-produced music, they often suggest that it's hard to capture the sort of dependencies that make for good music using current models (in the same way that current models have trouble making 'good art' that's more than style transfer or realistic faces or so on; it's unlikely that we could hook a NN up to a DeviantArt account and accept commissions and make money).

Currently humans play a major role in the interesting examples of neural art. Getting more artist-like autonomy is probably AI-complete, but I can imagine neural nets being more and more widely used in both visual art and music. I agree there’s great potential in neural music! (I suggest some experiments in my [conclusion](https://owainevans.github.io/visual_aesthetics/sensory-optimization.html#conclusion) but there's tons more that could be tried).