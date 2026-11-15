Comment by Marius Hobbhahn, 2023-01-26, on "Gradient hacking is extremely difficult"
https://www.lesswrong.com/posts/w2TAEvME2yAG9MHeq/gradient-hacking-is-extremely-difficult?commentId=7kPNywGtyCycvtjHh

HIS COMMENT:
I agree with everything you're saying. I just want to note that as soon as someone starts training networks in a way where not all weights are updated simultaneously, e.g. because the weights are updated only for specific parts of the network, or when the network has an external memory that is not changed every training step, gradient hacking seems immediately much more likely and much scarier.   
  
And there are probably hundreds of researchers out there working on modular networks with memory, so it probably won't take that long until we have models that plausibly have the capabilities to do gradient hacking. Whether they actually do it is a totally different question but it would be much easier to create a story of how the networks would gradient hack.