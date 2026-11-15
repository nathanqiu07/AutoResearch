Comment by Marius Hobbhahn, 2023-06-15, on "Announcing Apollo Research"
https://www.lesswrong.com/posts/FG6icLPKizEaWHex5/announcing-apollo-research?commentId=YkAifYXAnzjnmgAiv

PARENT (not his words):
Are you mainly interested in evaluating deceptive *capabilities*? I.e., no-holds-barred, can you elicit competent deception (or sub-components of deception) from the model? (Including by eg fine-tuning on data that demonstrates deception or sub-capabilities.)

Or evaluating *inductive biases* towards deception? I.e. testing whether the model is inclined towards deception in cases when the training data didn't necessarily require deceptive behavior.

(The latter might need to leverage some amount of capability evaluation, to distinguish not being inclined towards deception from not being capable of deception. But I don't think the reverse is true.)

Or if you disagree with that way of cutting up the space.

HIS COMMENT:
All of the above but in a specific order.   
1\. Test if the model has components of deceptive capabilities with lots of handholding with behavioral evals and fine-tuning.   
2\. Test if the model has more general deceptive capabilities (i.e. not just components) with lots of handholding with behavioral evals and fine-tuning.   
3\. Do less and less handholding for 1 and 2. See if the model still shows deception.   
4\. Try to understand the inductive biases for deception, i.e. which training methods lead to more strategic deception. Try to answer questions such as: can we change training data, technique, order of fine-tuning approaches, etc. such that the models are less deceptive?   
5\. Use 1-4 to reduce the chance of labs deploying deceptive models in the wild.