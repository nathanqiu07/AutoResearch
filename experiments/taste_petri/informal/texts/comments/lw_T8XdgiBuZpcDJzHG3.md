Comment by Owain_Evans, 2021-08-02, on "Delta Strain: Fact Dump and Some Policy Takeaways"
https://www.lesswrong.com/posts/9xd5ArGud8897q5on/delta-strain-fact-dump-and-some-policy-takeaways?commentId=T8XdgiBuZpcDJzHG3

PARENT (not his words):
**Errata**: My original calculation underestimated the risk by a factor of about 2x. I neglected two key considerations, which fortunately somewhat canceled each other out. My new estimate from the calculation is 3.0 to 11.7 quality-adjusted days lost to long-term sequelae, with my all-things-considered mean at 45. 

The two key things I missed:

  \- I estimated the risk of a non-hospitalized case is about 10x less than a hospitalized case, and so divided the estimates of disease burden by 10x. The first part is correct, but the second part would only make sense if all disease burden was due to hospitalized cases. In fact, there's a 15:85%  split between hospitalized and non-hospitalized patients in the study (13,654:73,435). So if the disease burden for non-hospitalized is x, the total burden is 0.15\*10x + 0.85\*x = 2.35x. So we should divide by 2.35, not 10.

  \- However, as Owain pointed out below, the [demographics\](https://www.nature.com/articles/s41586-021-03553-9/tables/1) are non-representative and probably skew high-risk given the median age is 60. the demographics are relatively high-risk. Indeed, this is suggested by the 15% hospitalized figure (which also, I suspect, means they just never included asymptomatic and most mildly symptomatic cases). An [ONS survey (Figure 4)](https://www.ons.gov.uk/peoplepopulationandcommunity/healthandsocialcare/conditionsanddiseases/bulletins/prevalenceofongoingsymptomsfollowingcoronaviruscovid19infectionintheuk/1april2021) put 

HIS COMMENT:
I quickly skimmed the El-Aly et al paper. It does look much better than some of the other studies. One concern is the demographics of the patients. Only 25% of people with Covid are younger than 48. Only 12% are female. I'd guess the veterans under 35 are significantly less affluent than LW readers. (Would more affluent veterans use private health care?). At a glance, I can't see results of any regressions on age but it might be worth contacting the authors about this.   
  
How to adjust for this? One thing is just look at hospitalization risk (see AdamGleave's adjustment point (1)). However, it seems plausible that younger and healthier people would also recover better from less acute cases (and be less likely to have lingering symptoms). OTOH, there's anecdata and data (of less high quality IMO) suggesting that Long Covid doesn't fit the general patter of exponential increases in badness of Covid (and other similar diseases) with age. Overall, I'd still be inclined to make an adjustment of risk down if you are under 35 and healthy. 

![](https://39669.cdn.cke-cs.com/rQvD3VnunXZu34m86e5f/images/f273d91b959bae8be0cdf933bbdbeafbcbfcee41f0d7c4a2.png)

Demographic info about patients in [El-Aly et al.](https://www.nature.com/articles/s41586-021-03553-9/tables/1)