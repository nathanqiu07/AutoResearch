Comment by Owain_Evans, 2019-11-11, on "Neural nets as a model for how humans make and understand visual art"
https://www.lesswrong.com/posts/sg8YjyDBKAF5s2Bgh/neural-nets-as-a-model-for-how-humans-make-and-understand?commentId=jeqq5yEP74W9Pkky6

PARENT (not his words):
Thanks for the reply :)

Sure, you can get the AI to draw polka-dots by targeting a feature that likes polka dots, or a [Mondrian](https://www.piet-mondrian.org/images/paintings/broadway-boogie-woogie.jpg) by targeting some features that like certain geometries and colors, but now you're not using style transfer at all - the image *is* the style. Moreover, it would be pretty hard to use this to get a [Kandinsky](https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/c5b87c93-2aef-4942-b846-70001439c229/d1xjhp9-09e07639-3547-4a2f-8d8d-960c5820c3d8.jpg/v1/fill/w_900,h_923,q_75,strp/kandinsky_inspired_3_by_artwyrd.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwic3ViIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsImF1ZCI6WyJ1cm46c2VydmljZTppbWFnZS5vcGVyYXRpb25zIl0sIm9iaiI6W1t7InBhdGgiOiIvZi9jNWI4N2M5My0yYWVmLTQ5NDItYjg0Ni03MDAwMTQzOWMyMjkvZDF4amhwOS0wOWUwNzYzOS0zNTQ3LTRhMmYtOGQ4ZC05NjBjNTgyMGMzZDguanBnIiwid2lkdGgiOiI8PTkwMCIsImhlaWdodCI6Ijw9OTIzIn1dXX0.daw4q-SS4tzsHuMnZPN1P4tBsKseVIORSyzqP6V-Suo), because the AI that makes style-paintings has no standard by which it would choose things to draw that could be objects but aren't. You'd need a third and separate scheme to make Kandinskys, and then I'd just bring up another artist not covered yet.

If you're not trying to capture all human visual art in one model, then this is no biggie. So now you're probably going "this is fine, why is he going on abou

HIS COMMENT:
> You'd need a third and separate scheme to make Kandinskys, and then I'd just bring up another artist not covered yet.

Again, replicating all human art is probably AGI-complete. However, there are some promising strategies for generating non-representational art and I’d guess artists were (implicitly) using some of them. Here are some possible Sensory Optimization objectives:

1\. Optimize the image to be a superstimulus for random sets of features in earlier layers (this was already discussed).

2\. Use Style Transfer to constrain the low-level features in some way. This could aim at grid-like images (Mondrian, [Kelly](https://www.google.com/imgres?imgurl=https%3A%2F%2Fmethodtwomadness.files.wordpress.com%2F2016%2F01%2Fkelly-squares-comp.jpg&imgrefurl=https%3A%2F%2Fmethodtwomadness.wordpress.com%2F2016%2F01%2F09%2Fnine-squares-for-ellsworth-kelly%2F&docid=UX13QtP4jbx5eM&tbnid=I_y-JuTySxczPM%3A&vet=10ahUKEwjW-4jh5-LlAhV0qnEKHaa2CmsQMwhdKAIwAg..i&w=1879&h=1864&client=firefox-b-d&bih=963&biw=1448&q=ellsworth%20kelly%20squares&ved=0ahUKEwjW-4jh5-LlAhV0qnEKHaa2CmsQMwhdKAIwAg&iact=mrc&uact=8), [Albers](https://www.lempertz.com/en/catalogues/lot/1122-1/508-josef-albers.html)) or a limited set of textures ([Richter](https://www.tate.org.uk/art/artworks/richter-abstract-painting-726-t06600)). This is mentioned in Section 1.3.1.

3\. If you want the image to evoke objects (without explicitly depicting them), then you could combine (1) and (2) with optimizing for some object labels (e.g. river, stairs, pole). This is simpler than your Kandinsky example but could still be effective.

4\. In addition to (1) and (2), optimize the image for human emotion labels (having trained on a dataset with emotion labels for photos). To take a simplistic example: people will label photos with lots of green or blue (e.g. forest or sea or blue skies) as peaceful/calming, and so abstract art based on those colors would be labeled similarly. Red or muddy-gray colors would produce a different response. This extends beyond colors to visual textures, shapes, symmetry vs. disorder and so on. (Compare this [Rothko](https://publicdelivery.org/mark-rothko-chapel/) to this [one](https://www.britannica.com/biography/Mark-Rothko)).

> Maybe you could train an AI on patriotic paintings and then it could produce patriotic paintings, but I think only by working on theory of mind would an AI think to produce a patriotic painting without having seen one before.

I agree with your general point about the relevance of theory of mind. However, I think Sensory Optimization could generate patriotic paintings without training on them. Suppose you have a dataset that's richer than ImageNet and includes human emotion and sentiment labels/captions. Some photos will cause patriotic sentiments: e.g. photos of parades or parties on national celebrations, photos of a national sports team winning, photos of iconic buildings or natural wonders. So to create patriotic paintings, you would optimize for labels relating to patriotism. If there are emotional intensity ratings for photos, and patriotic scenes cause high intensity, then maybe you could get patriotic paintings by just optimizing for intensity. (Facebook has trained models on a huge image dataset with Instagram hashtags -- some of which relate to patriotic sentiment. Someone could run a version of this experiment today. However, I think it's a more interesting experiment if the photos are more like everyday human visual perception than carefully crafted/edited photos you'll find on Instagram.)

> I was thinking of how some things aren't art if they're normal sized, but if you make them really big, then they're art.

Again, I expect a richer training set would convey lots of this information. Humans would use different emotional/aesthetic labels on seeing unusually large natural objects (e.g. an abnormally large dog or man, a huge tree or waterfall).

> For "limited," I imagined something like Dennett's example of the people on the bridge. The artist only has to paint little blobs, because they know how humans will interpret them.

Some artworks depend on idiosyncratic quirks of human visual cognition (e.g. optical illusions). It's probably hard for a neural net to predict how humans will respond to all such works (without training on other images that exploit the same quirk). This will limit the kind of art the Sensory Optimization model can generate. Still, this doesn't undermine my claim that artists are doing something like Sensory Optimization. For example, humans have a bias towards seeing faces in random objects -- pareidolia. By exploiting this, [artists](https://en.wikipedia.org/wiki/Giuseppe_Arcimboldo) exploit an image that looks like two things at once. (The artist knows the illusion will work, because it works on his or her own visual system).

> My impression is that DeepDream et al. have been trained to make visual art - by hyperparameter tuning (grad student descent).

I think this first blogpost on Deep Dream and the original [paper](https://arxiv.org/abs/1508.06576) on Style Transfer already were already very impressive. The regularization tweak for Deep Dream is very simple and quite different from what I mean by "training on visual art". (It's less surprising that a GAN trained on visual art can generate something that looks like visual art -- although it is surprising how [well](https://www.gwern.net/Faces) they can deal with stylized images.)