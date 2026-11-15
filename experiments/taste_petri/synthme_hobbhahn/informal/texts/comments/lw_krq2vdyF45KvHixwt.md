Comment by Marius Hobbhahn, 2022-05-12, on "The limits of AI safety via debate"
https://www.lesswrong.com/posts/kguLeJTt6LnGuYX4E/the-limits-of-ai-safety-via-debate?commentId=krq2vdyF45KvHixwt

PARENT (not his words):
Going through the problems in order:

> Assumption 1: concept must break down into parts that are verifiable in a reasonable timeframe
> 
> [...]
> 
> In the “1800 Fortnite” example, the debater would have to convince the verifier of the existence of electricity, TVs or computers, video games, the internet, etc. 

No. There would have to be an implicit exponentially-large debate tree that when put together justifies all of those claims using only knowledge that the person from 1800 already has or can easily verify, but that tree could have, idk, 2^1000 nodes. Note this is well over the number of atoms in the observable universe. I don't have an immediate link for debate (besides the original paper), but [this post](https://www.lesswrong.com/posts/DFkGStzvj3jgXibFG/factored-cognition) has an explanation for iterated amplification.

A given debate (as described in the original paper) is a single path through this tree, that ends up narrowing down on a single particular very specific subclaim that the person from 1800 has to judge, e.g. "two balloons that were rubbed on hair will tend to repel each other slightly" (you might get there via a debate that focuses on electricity). It is *not* the case that at the end of the debate the judge is supposed to have an understanding of all of the details going into the final argument.

> Assumption 2: human verifiers are capable of understanding the concept in principle
> 
> I’m not very sure about this but I could imagine that there are 

HIS COMMENT:
Thanks for your detailed comment. Let me ask some clarifications. I will update the post afterward.  
  
**Assumption 1:**   
  
I understand where you are going but the underlying path in the tree might still be very long, right? The not-Fortnite-debater might argue that you couldn't have played Fortnite because electricity doesn't exist.  Then the Fortnite-debater has to argue that it does exist, right?   
  
Furthermore, I don't see why it should just be one path in the tree. Some arguments have multiple necessary conditions/burdens. Why do I not have to prove all of them? Otherwise, the opponent in the debate can always answer with "OK assume everything you said is true, what about the other burden?".   
  
I'll update this section once I understand your criticism better.  
  
**Assumption II:**   
  
Ok, let's say that we are able to understand it after a billion years of looking at it. Or maybe we understand it after the heat death of the universe. Does that really change anything? Perhaps I should reframe it as "understanding the concept in principle (in a relevant sense)" or something like that.   
  
I think the more compelling analogy to me is "could you teach your dog quantum physics" given lots of time and resources. I'm not sure the dog is able to understand. What do you think?  
  
Assumptions III and IV:  
  
These are practical problems of debate. I mostly wanted to point out that they could happen to the people running experiments with debate. I think they could also happen in a company, e.g. when the AI says things that are in the interest of the specific verifier but not their manager. I think this point can be summarized as "as long as humans are the verifiers, human flaws can be breaking points of AI safety via debate"  
I'll rephrase them to emphasize this more.

**Framing: what is AI safety used for**

I think your framing of AI safety as a tool for AI safety researchers reduces some of the problems I described and I will rewrite the relevant passages. However, while the interests of the AI company might be less complex, they are not necessarily straightforward, e.g. when leadership has different ideals than the safety team and would thus verify different players in the final node.    
  
**Assumption V:**

I agree with you that in a perfect setting this could not happen. However, in real life with debates on TV or even with well-intentioned scientists who have held wrong beliefs for a long time even though they were sometimes confronted with the truth and an explanation for it, we see this often. I think it's more of a question of how much we trust the verifier to make the right call given a good explanation than a fundamental disagreement of the method.   
  
**Assumption VI:**

The example is not optimal. I see that now and will change it. However, the underlying argument still seems true to me. The incentive of the AI is to get the human to declare it as the winner, right? Therefore, it will use all its tools to make it win. If it has superhuman intelligence and a very accurate model of the verifier(s) it will say things that make the humans give it the win. If part of that strategy is to be deceptive, why wouldn't it use that? I *think this is very important and I currently don't understand your reasoning. Let me know if you think I'm missing something.*