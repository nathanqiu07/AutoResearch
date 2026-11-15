Comment by Marius Hobbhahn, 2022-12-15, on "Predicting GPU performance"
https://www.lesswrong.com/posts/vnvGhfikBbrjZHMuD/predicting-gpu-performance?commentId=MP996Puh2uyKsbcwg

PARENT (not his words):
What about the Landauer limit? We are 3 orders of magnitude from the Landauer limit ($10^{-21}$ J/op), see my [article](https://www.lesswrong.com/posts/N7KYWJPmyzB6bJSYT/the-next-ai-winter-will-be-due-to-energy-costs-1) here on Lesswrong. The authors list several physical limitations, but this one seems to be missing. It may pose the most relevant limit.

HIS COMMENT:
We did consider modeling it explicitly. However, most estimates on the Landauer limit give very similar predictions as size limits. So we decided against making an explicit addition to the model and it is "implicitly" modeled in the physical size. We intend to look into Landauer's limit at some point but it's not a high priority right now.