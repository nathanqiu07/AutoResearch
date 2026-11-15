Comment by Owain_Evans, 2023-09-23, on "Paper: LLMs trained on “A is B” fail to learn “B is A”"
https://www.lesswrong.com/posts/SCqDipWAhZ49JNdmL/paper-llms-trained-on-a-is-b-fail-to-learn-b-is-a?commentId=iLBe4rkqPm7ciL5r9

HIS COMMENT:
How to do your own test of the Reversal Curse (e.g. on ChatGPT or Claude) with different prompting strategies:

1.  Try this list of hard examples: C-list celebrities who have a different last name from their parents. The list below has the form <celeb\_name>, <parent\_name>.
2.  First verify the model know the celebrity's parent by asking "Who is [name]'s mother/father?"
3.  Then, in a separate dialog, ask the model for the child of the parent. You must not include the child's name anywhere in the dialog!

![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34m86e5f/images/8ecafcf3f4f1851dacb2f859eb05ecf63909b6d3cdc9254e.png)