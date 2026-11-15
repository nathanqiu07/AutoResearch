Comment by Owain_Evans, 2020-09-23, on "Forecasting Thread: Existential Risk"
https://www.lesswrong.com/posts/6x9rJbx9bmGsxXWEj/forecasting-thread-existential-risk-1?commentId=S6WNhzqWDYZJurvor

PARENT (not his words):
I'm having some technical difficulties I think. When I run the last thing that's supposed to generate my combined distribution, I get the error "NameError: name 'labels' is not defined"

HIS COMMENT:
You need to first run all the cells in "Setup Code" (e.g. by selecting "Runtime > Run before"). Then run the cell with the form input ("\(\)risk1label", "risk1url", etc), and then run the cell that plots your pdf/cdf. It sounds like you're running the last cell without having run the middle one.